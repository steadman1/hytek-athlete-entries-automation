"""CSV loading and flexible column mapping for athletes and entries."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def read_csv_rows(path: Path | str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a CSV file returning the headers and a list of string-valued dict rows.
    Handles UTF-8, UTF-8-BOM, and Latin-1 automatically.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CSV file not found: {p}")

    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                raw_headers = next(reader, None)
                if raw_headers is None:
                    return [], []
                # Keep original non-empty trimmed headers or assign index fallback for blank cols
                headers = [h.strip() if h.strip() else f"_col_{i}" for i, h in enumerate(raw_headers)]
                dict_reader = csv.DictReader(f, fieldnames=headers)
                rows = [
                    {k: (v or "").strip() for k, v in r.items() if k is not None}
                    for r in dict_reader
                ]
                return headers, rows
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not decode CSV file {p}")


def _normalize_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", h.lower())


def auto_detect_athlete_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Heuristically find columns for: 'first_name', 'last_name', 'id', 'gender'.
    Returns a dict mapping role -> column name (or None if not found).
    Works with standard CSVs and College Club Swimming roster exports (memberTable.csv).
    """
    mapping: Dict[str, Optional[str]] = {
        "first_name": None,
        "last_name": None,
        "id": None,
        "gender": None,
    }

    norm_to_orig = {_normalize_header(h): h for h in headers}

    # 1. Athlete ID: check for Member ID / CCS ID / Club ID first, before generic 'id'
    for pat in ("memberid", "athleteid", "ccsid", "clubid", "usaswid", "idno", "idnumber"):
        for norm, orig in norm_to_orig.items():
            if norm == pat:
                mapping["id"] = orig
                break
        if mapping["id"]:
            break

    # Fallback to general 'id' if not already found
    if not mapping["id"]:
        for norm, orig in norm_to_orig.items():
            if norm == "id" or (norm.endswith("id") and "first" not in norm and "last" not in norm and "event" not in norm):
                mapping["id"] = orig
                break

    # 2. First name
    for pat in ("firstname", "first", "fname", "givenname"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or (pat in norm and "last" not in norm):
                mapping["first_name"] = orig
                break
        if mapping["first_name"]:
            break

    # 3. Last name
    for pat in ("lastname", "last", "lname", "surname", "familyname"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or (pat in norm and "first" not in norm):
                mapping["last_name"] = orig
                break
        if mapping["last_name"]:
            break

    # 4. Gender / Sex / "Who do you plan to compete against"
    for pat in ("gender", "sex", "whodoyouplanto", "competeagainst"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or pat in norm:
                mapping["gender"] = orig
                break
        if mapping["gender"]:
            break

    return mapping


def auto_detect_entry_columns(headers: List[str]) -> Dict[str, Any]:
    """Auto-detect columns in the entries CSV:
    - first_name
    - last_name
    - gender
    - events_col: column listing chosen events (e.g. 'Individual Events Select up to 3')
    - times_col: column listing custom seed times (e.g. 'Please indicate if you would like to include a seed time')
    """
    ath_map = auto_detect_athlete_columns(headers)
    mapping: Dict[str, Any] = {
        "first_name": ath_map.get("first_name"),
        "last_name": ath_map.get("last_name"),
        "gender": ath_map.get("gender"),
        "events_col": None,
        "times_col": None,
    }

    norm_to_orig = {_normalize_header(h): h for h in headers}

    # Detect times column
    for norm, orig in norm_to_orig.items():
        if ("seedtime" in norm or "customtime" in norm or ("time" in norm and "format" in norm) or "seed" in norm) and "timestamp" not in norm:
            mapping["times_col"] = orig
            break

    # Detect events column
    for norm, orig in norm_to_orig.items():
        if ("individualevents" in norm or "eventsselect" in norm or "chosenevents" in norm or "events" in norm) and orig != mapping.get("times_col") and "relay" not in norm:
            mapping["events_col"] = orig
            break

    return mapping
