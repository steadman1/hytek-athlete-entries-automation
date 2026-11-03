"""OpenAI integration for parsing non-standard event entries and messy times.

When configured with an api_key and optional completions base_url, this module
can interpret messy free-text form inputs (e.g. from Google Forms / Sheets) like:
  "50 Free (23.50), 100 Breast (1:05.2)"
  "500 Free - 5 min 30 sec"
and map them to valid meet events and centisecond times.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from hytek_ae.core.models import MeetEvent
from hytek_ae.core.time_parser import parse_time_to_centiseconds

logger = logging.getLogger(__name__)


class NLPExtractor:
    """Wraps an OpenAI client with a targeted prompt to resolve meet entries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        self._client: Any = None

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key is required for NLP parsing.")
            try:
                from openai import OpenAI

                kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError as err:
                raise ImportError(
                    "openai package is required for NLP parsing. Run: uv add openai"
                ) from err
        return self._client

    def parse_entry_text(
        self,
        raw_text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> List[Tuple[int, int]]:
        """Parse raw user-typed text into a list of (event_number, centiseconds).

        Args:
            raw_text: user-supplied text from a CSV entry cell
            athlete_gender: "M" or "F"
            valid_events: available MeetEvent objects from the .hyv file

        Returns:
            List of (event_number, centiseconds)
        """
        if not raw_text or not raw_text.strip():
            return []

        # First, try pure deterministic matching
        deterministic = self._try_deterministic_parse(raw_text, athlete_gender, valid_events)
        if deterministic is not None:
            return deterministic

        # If deterministic fails and no OpenAI key is set, log warning and return empty
        if not self.is_available:
            logger.warning(
                "Could not deterministically parse entry '%s' and OpenAI API key is not configured.",
                raw_text,
            )
            return []

        # Otherwise, call OpenAI structured output
        return self._call_openai_parse(raw_text, athlete_gender, valid_events)

    def _try_deterministic_parse(
        self,
        text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> Optional[List[Tuple[int, int]]]:
        """Try simple, fast matching before calling the API."""
        # Normalize text
        t = text.strip()
        gender_code = athlete_gender.upper()[:1] if athlete_gender else "X"

        # Check for event number prefix e.g. "Event 6: 58.69" or "#6 58.69"
        num_match = re.match(r"^(?:event\s*#?|#)?(\d+)\b[:\s-]*(.*)$", t, re.IGNORECASE)
        if num_match:
            ev_no = int(num_match.group(1))
            time_part = num_match.group(2).strip()
            # Verify ev_no exists
            matching_ev = next((e for e in valid_events if e.number == ev_no), None)
            if matching_ev:
                try:
                    cs = parse_time_to_centiseconds(time_part)
                    return [(ev_no, cs)]
                except ValueError:
                    pass

        # Check for standard distance + stroke matching e.g. "50 Free 23.69", "100 Back"
        # Only attempt if it looks simple (single line)
        for ev in valid_events:
            # Check gender compatibility
            if ev.gender not in ("X", gender_code):
                continue

            dist_str = str(ev.distance)
            stroke_terms = {
                "FREESTYLE": ["free", "freestyle", "fr"],
                "BACKSTROKE": ["back", "backstroke", "bk"],
                "BREASTSTROKE": ["breast", "breaststroke", "br"],
                "BUTTERFLY": ["fly", "butterfly", "fl"],
                "MEDLEY": ["im", "medley", "individual medley"],
            }.get(ev.stroke, [])

            pattern = rf"\b{dist_str}\b\s*(?:{'|'.join(stroke_terms)})\b(?:\s*[:=-]?\s*([0-9:.]+))?"
            m = re.search(pattern, t, re.IGNORECASE)
            if m:
                time_str = m.group(1)
                try:
                    cs = parse_time_to_centiseconds(time_str) if time_str else 0
                    return [(ev.number, cs)]
                except ValueError:
                    return [(ev.number, 0)]

        return None

    def _call_openai_parse(
        self,
        text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> List[Tuple[int, int]]:
        client = self._get_client()

        # Build candidate event descriptions for the prompt
        events_desc = [
            f"#{e.number}: {e.distance} {e.stroke.title()} ({e.gender})"
            for e in valid_events
            if e.gender in ("X", athlete_gender.upper()[:1])
        ]

        system_prompt = (
            "You are a swimming meet entries parser. Given a swimmer's raw entries text "
            "and their gender, extract the matching meet events and seed times.\n"
            "Respond ONLY with a JSON array of objects with keys:\n"
            "  'event_number': integer\n"
            "  'centiseconds': integer (swim time in hundredths of a second, e.g. 58.69 -> 5869, 1:01.01 -> 6101, NT or missing -> 0)\n"
            "If an event cannot be matched, omit it."
        )

        user_content = (
            f"Athlete gender: {athlete_gender}\n"
            f"Available meet events:\n" + "\n".join(events_desc) + "\n\n"
            f"Raw text to parse:\n\"{text}\""
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw_json = response.choices[0].message.content or "{}"
            data = json.loads(raw_json)
            # data could be {"entries": [...]} or directly a list
            items = data.get("entries", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                # Search for any list inside data
                for val in data.values():
                    if isinstance(val, list):
                        items = val
                        break

            results: List[Tuple[int, int]] = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        ev_no = item.get("event_number")
                        cs = item.get("centiseconds", 0)
                        if ev_no is not None:
                            results.append((int(ev_no), int(cs)))

            return results
        except Exception as e:
            logger.error("Error calling OpenAI completion: %s", e)
            return []
