"""OpenAI integration and deterministic parsers for meet entries and messy times.

Interprets free-text and form inputs like:
  "50 back: 3, 28.63 50 fly: 13, 28.68 50 free: 19, 24.33"
  "19-20: 50 Breast, 23-24: 50 Free"
  "100 Free: 48.83\n100 Fly: 54.63\n50 Free: 22.20"
  "6, 26.56"
and maps them to valid meet events and centisecond times.
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


def parse_events_field(
    events_text: str,
    athlete_gender: str,
    valid_events: List[MeetEvent],
) -> List[int]:
    """Parse comma/newline separated chosen events text (e.g. '19-20: 50 Breast, 23-24: 50 Free')
    into a list of event_numbers matching the meet events and athlete gender.
    """
    if not events_text or not events_text.strip():
        return []

    gender_code = athlete_gender.upper()[:1] if athlete_gender else "X"
    matched_event_nums: List[int] = []

    # Split by comma or newline
    parts = re.split(r"[,;\n\r]+", events_text)
    for part in parts:
        p = part.strip()
        if not p:
            continue

        # Pattern 1: e.g. "19-20: 50 Breast" or "23-24: 50 Free" or "6: 100 IM"
        range_match = re.search(r"\b(\d+)(?:\s*-\s*(\d+))?\s*:\s*(.*)", p)
        if range_match:
            ev_start = int(range_match.group(1))
            ev_end = int(range_match.group(2)) if range_match.group(2) else ev_start
            # Find the event in range that matches gender
            matching = [
                e.number for e in valid_events
                if ev_start <= e.number <= ev_end and e.gender in ("X", gender_code)
            ]
            if matching:
                matched_event_nums.extend(matching)
                continue

        # Pattern 2: e.g. "#6" or "Event 6" or just an integer number
        num_match = re.match(r"^(?:event\s*#?|#)?(\d+)\b", p, re.IGNORECASE)
        if num_match:
            ev_no = int(num_match.group(1))
            if any(e.number == ev_no for e in valid_events):
                matched_event_nums.append(ev_no)
                continue

        # Pattern 3: distance + stroke (e.g. "50 Free", "100 Breast")
        for ev in valid_events:
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
            pattern = rf"\b{dist_str}\b\s*(?:{'|'.join(stroke_terms)})\b"
            if re.search(pattern, p, re.IGNORECASE):
                if ev.number not in matched_event_nums:
                    matched_event_nums.append(ev.number)
                break

    # De-duplicate while preserving order
    seen = set()
    return [x for x in matched_event_nums if not (x in seen or seen.add(x))]


def _find_event_by_stroke(
    desc: str,
    athlete_gender: str,
    valid_events: List[MeetEvent],
) -> Optional[int]:
    """Helper to match a stroke phrase like '50 back' or '100 Free' to an event number."""
    gender_code = athlete_gender.upper()[:1] if athlete_gender else "X"
    for ev in valid_events:
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
        pattern = rf"\b{dist_str}\b\s*(?:{'|'.join(stroke_terms)})\b"
        if re.search(pattern, desc, re.IGNORECASE):
            return ev.number
    return None


def parse_times_field(
    times_text: str,
    athlete_gender: str,
    valid_events: List[MeetEvent],
) -> Dict[int, int]:
    """Parse custom times text like:
        "50 back: 3, 28.63 50 fly: 13, 28.68 50 free: 19, 24.33"
        "100 Free: 48.83\n100 Fly: 54.63\n50 Free: 22.20"
        "6, 26.56"
        "Event 24: 23.69"
    into a mapping: {event_number: centiseconds}.
    """
    if not times_text or not times_text.strip():
        return {}

    # Pre-clean string: strip all quotes (" and ') and parentheses (( and ))
    clean_text = re.sub(r"[\'\"()]", "", str(times_text)).strip()
    if not clean_text:
        return {}

    gender_code = athlete_gender.upper()[:1] if athlete_gender else "X"
    times_map: Dict[int, int] = {}

    # Comprehensive multi-pattern regex matching:
    # 1) Optional event stroke description: e.g. "50 back:" or "100 Free:" or "50 Free 23.69"
    # 2) Optional event number: e.g. "3," or "Event 6:"
    # 3) Time token: e.g. "28.63", "1:01.01", "24", "NT"
    pattern = re.compile(
        r"(?:(?P<desc>\d{1,4}\s*(?:free(?:style)?|back(?:stroke)?|breast(?:stroke)?|fly|butterfly|im|medley))\s*[:=-]?\s*)?"
        r"(?:(?:event\s*#?|#)?(?P<ev>\d{1,3})\s*[,:\s-]+\s*)?"
        r"(?P<time>(?:\d{1,2}:)?\d{1,2}[.:]\d{1,3}|\d{1,2}(?:\.\d{1,2})?|NT|nt)(?:[YSLysl])?",
        re.IGNORECASE,
    )

    for m in pattern.finditer(clean_text):
        desc = m.group("desc")
        raw_ev = m.group("ev")
        time_str = m.group("time")

        if not time_str:
            continue

        target_ev: Optional[int] = None

        if raw_ev:
            ev_candidate = int(raw_ev)
            if any(e.number == ev_candidate for e in valid_events):
                target_ev = ev_candidate

        if target_ev is None and desc:
            target_ev = _find_event_by_stroke(desc, athlete_gender, valid_events)

        if target_ev is not None:
            try:
                times_map[target_ev] = parse_time_to_centiseconds(time_str)
            except ValueError:
                times_map[target_ev] = 0

    return times_map


class NLPExtractor:
    """Wraps an OpenAI client with a targeted prompt to resolve meet entries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        force_nlp: bool = False,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        self.force_nlp = force_nlp
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
        """Parse raw user-typed text into a list of (event_number, centiseconds)."""
        if not raw_text or not raw_text.strip():
            return []

        # If force_nlp is False, try deterministic parsing first
        if not self.force_nlp:
            deterministic = self._try_deterministic_parse(raw_text, athlete_gender, valid_events)
            if deterministic is not None:
                return deterministic

        # If deterministic fails or force_nlp is True:
        if not self.is_available:
            if self.force_nlp:
                logger.warning(
                    "Force NLP was requested but OpenAI API key is not configured; falling back to deterministic parser."
                )
                det = self._try_deterministic_parse(raw_text, athlete_gender, valid_events)
                return det if det is not None else []
            logger.warning(
                "Could not deterministically parse entry '%s' and OpenAI API key is not configured.",
                raw_text,
            )
            return []

        return self._call_openai_parse(raw_text, athlete_gender, valid_events)

    def parse_custom_times(
        self,
        times_text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> Dict[int, int]:
        """Parse custom times text into {event_number: centiseconds}.
        If force_nlp is True and OpenAI client is available, calls LLM completion.
        Otherwise uses deterministic parse_times_field().
        """
        if not times_text or not times_text.strip():
            return {}

        if self.force_nlp and self.is_available:
            entries = self._call_openai_parse(times_text, athlete_gender, valid_events)
            return dict(entries)

        # Deterministic
        res = parse_times_field(times_text, athlete_gender, valid_events)
        if not res and self.is_available:
            # Fallback to NLP if deterministic returned empty
            entries = self._call_openai_parse(times_text, athlete_gender, valid_events)
            return dict(entries)
        return res

    def _try_deterministic_parse(
        self,
        text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> Optional[List[Tuple[int, int]]]:
        """Try simple, fast matching before calling the API."""
        times_map = parse_times_field(text, athlete_gender, valid_events)
        if times_map:
            return list(times_map.items())

        return None

    def _call_openai_parse(
        self,
        text: str,
        athlete_gender: str,
        valid_events: List[MeetEvent],
    ) -> List[Tuple[int, int]]:
        client = self._get_client()

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
            items = data.get("entries", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
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
