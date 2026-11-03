"""Wrapper around hytek-parser for .hyv meet events files."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from hytek_parser.hyv import parse_event_hyv
from hytek_parser.hyv.schemas import ParsedEventHyvFile

from hytek_ae.core.models import Meet, MeetEvent


def load_hyv_file(path: Path | str) -> Tuple[Meet, List[MeetEvent]]:
    """Parse a .hyv file and return a Meet dataclass and a list of MeetEvent objects."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"HYV file not found: {p}")

    parsed: ParsedEventHyvFile = parse_event_hyv(str(p))

    course_code = "YO"
    if parsed.meet_course:
        name = parsed.meet_course.name.upper()
        if "SCY" in name:
            course_code = "YO"
        elif "LCM" in name:
            course_code = "LO"
        elif "SCM" in name:
            course_code = "SO"

    meet = Meet(
        name=parsed.meet_name or p.stem,
        start_date=parsed.meet_start_date,
        end_date=parsed.meet_end_date,
        course=course_code,
        location=parsed.meet_pool or "",
    )

    events: List[MeetEvent] = []
    for ev in parsed.events:
        gender_letter = "X"
        if ev.gender:
            g_name = ev.gender.name.upper()
            if "FEMALE" in g_name:
                gender_letter = "F"
            elif "MALE" in g_name:
                gender_letter = "M"

        stroke_str = ev.stroke.name.upper() if ev.stroke else "FREESTYLE"
        is_relay = False
        if ev.swimmer_type and "RELAY" in ev.swimmer_type.name.upper():
            is_relay = True

        events.append(
            MeetEvent(
                number=int(ev.number),
                gender=gender_letter,
                distance=int(ev.distance),
                stroke=stroke_str,
                is_relay=is_relay,
            )
        )

    return meet, events
