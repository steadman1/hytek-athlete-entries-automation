"""Core orchestration pipeline that links CSV reading, matching, and DB insertion."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from hytek_ae.core.csv_reader import auto_detect_athlete_columns, read_csv_rows
from hytek_ae.core.hyv_parser import load_hyv_file
from hytek_ae.core.models import Athlete, Entry, Meet, MeetEvent, Team
from hytek_ae.core.nlp import NLPExtractor
from hytek_ae.core.time_parser import parse_time_to_centiseconds

logger = logging.getLogger(__name__)


def build_athlete_id_map(
    ids_csv_path: Optional[Path | str],
    first_name_col: Optional[str] = None,
    last_name_col: Optional[str] = None,
    id_col: Optional[str] = None,
) -> Dict[str, str]:
    """Parse the athlete IDs CSV into a map: 'first|last' -> id_no."""
    if not ids_csv_path:
        return {}

    p = Path(ids_csv_path)
    if not p.is_file():
        return {}

    headers, rows = read_csv_rows(p)
    detected = auto_detect_athlete_columns(headers)
    fn_col = first_name_col or detected.get("first_name")
    ln_col = last_name_col or detected.get("last_name")
    id_c = id_col or detected.get("id")

    if not fn_col or not ln_col or not id_c:
        logger.warning("Could not identify all required columns in IDs CSV: %s", headers)
        return {}

    mapping: Dict[str, str] = {}
    for r in rows:
        fn = r.get(fn_col, "").strip().lower()
        ln = r.get(ln_col, "").strip().lower()
        id_val = r.get(id_c, "").strip()
        if fn and ln and id_val:
            key = f"{fn}|{ln}"
            mapping[key] = id_val

    return mapping


def process_entries_csv(
    entries_csv_path: Path | str,
    valid_events: List[MeetEvent],
    athlete_id_map: Dict[str, str],
    nlp_extractor: NLPExtractor,
    meet_id: int = 1,
    team_id: int = 1,
    first_name_col: Optional[str] = None,
    last_name_col: Optional[str] = None,
    gender_col: Optional[str] = None,
    event_cols: Optional[List[str]] = None,
) -> Tuple[List[Athlete], List[Entry]]:
    """Parse the entries CSV, match athletes, assign 1-based IDs, and build Entry records."""
    headers, rows = read_csv_rows(entries_csv_path)
    detected = auto_detect_athlete_columns(headers)

    fn_col = first_name_col or detected.get("first_name")
    ln_col = last_name_col or detected.get("last_name")
    gen_col = gender_col or detected.get("gender")

    if not fn_col or not ln_col:
        raise ValueError(
            f"Entries CSV is missing First Name or Last Name column. Available: {headers}"
        )

    # If specific event columns are not provided, treat all other columns as potential entry columns
    if not event_cols:
        reserved = {fn_col, ln_col}
        if gen_col:
            reserved.add(gen_col)
        # Filter out obvious non-entry metadata columns (Timestamp, Email, Notes, etc.)
        ignored = {"timestamp", "emailaddress", "email", "notes", "comments", "grade", "class"}
        event_cols = [
            h for h in headers
            if h not in reserved and h.lower().replace(" ", "").replace("_", "") not in ignored
        ]

    athletes: List[Athlete] = []
    entries: List[Entry] = []
    athlete_lookup: Dict[str, Athlete] = {}

    entry_pk = 1
    athlete_pk = 1

    for row in rows:
        fn = row.get(fn_col, "").strip()
        ln = row.get(ln_col, "").strip()
        if not fn or not ln:
            continue

        raw_gender = row.get(gen_col, "") if gen_col else ""
        gender = "M" if raw_gender.strip().upper().startswith("M") else (
            "F" if raw_gender.strip().upper().startswith("F") else "X"
        )

        lookup_key = f"{fn.lower()}|{ln.lower()}"
        if lookup_key not in athlete_lookup:
            id_no = athlete_id_map.get(lookup_key, "")
            ath = Athlete(
                athlete_id=athlete_pk,
                first_name=fn,
                last_name=ln,
                gender=gender,
                id_no=id_no,
                team_id=team_id,
            )
            athlete_lookup[lookup_key] = ath
            athletes.append(ath)
            athlete_pk += 1
        else:
            ath = athlete_lookup[lookup_key]
            # Update gender if previously unknown
            if ath.gender == "X" and gender != "X":
                ath.gender = gender

        # Parse each event column for this row
        for col in event_cols:
            val = row.get(col, "").strip()
            if not val:
                continue

            # First, check if the column header ITSELF is a meet event name
            # e.g. Column is "50 Freestyle" and the cell is "23.69" or "X"
            header_match = next(
                (
                    e for e in valid_events
                    if e.gender in ("X", ath.gender)
                    and (
                        col.lower() in e.name.lower()
                        or f"{e.distance}" in col and e.stroke.lower()[:3] in col.lower()
                    )
                ),
                None,
            )

            if header_match:
                try:
                    cs = parse_time_to_centiseconds(val)
                except ValueError:
                    cs = 0
                entries.append(
                    Entry(
                        entry_id=entry_pk,
                        athlete_id=ath.athlete_id,
                        meet_id=meet_id,
                        team_id=team_id,
                        event_number=header_match.number,
                        score=cs,
                    )
                )
                entry_pk += 1
            else:
                # The cell text contains the event description (or multiple events)
                # Pass through the NLP / deterministic parser
                parsed_list = nlp_extractor.parse_entry_text(val, ath.gender, valid_events)
                for ev_num, cs in parsed_list:
                    entries.append(
                        Entry(
                            entry_id=entry_pk,
                            athlete_id=ath.athlete_id,
                            meet_id=meet_id,
                            team_id=team_id,
                            event_number=ev_num,
                            score=cs,
                        )
                    )
                    entry_pk += 1

    return athletes, entries
