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
                headers = [h.strip() for h in raw_headers]
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
    """
    mapping: Dict[str, Optional[str]] = {
        "first_name": None,
        "last_name": None,
        "id": None,
        "gender": None,
    }

    norm_to_orig = {_normalize_header(h): h for h in headers}

    # First name
    for pat in ("firstname", "first", "fname", "givenname"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or (pat in norm and "last" not in norm):
                mapping["first_name"] = orig
                break
        if mapping["first_name"]:
            break

    # Last name
    for pat in ("lastname", "last", "lname", "surname", "familyname"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or (pat in norm and "first" not in norm):
                mapping["last_name"] = orig
                break
        if mapping["last_name"]:
            break

    # Athlete ID
    for pat in ("athleteid", "idno", "idnumber", "clubid", "usaswid", "id", "memberid"):
        for norm, orig in norm_to_orig.items():
            if norm == pat:
                mapping["id"] = orig
                break
            if pat in norm and norm not in ("firstname", "lastname", "eventid"):
                mapping["id"] = orig
                break
        if mapping["id"]:
            break

    # Gender
    for pat in ("gender", "sex"):
        for norm, orig in norm_to_orig.items():
            if norm == pat or pat in norm:
                mapping["gender"] = orig
                break
        if mapping["gender"]:
            break

    return mapping
