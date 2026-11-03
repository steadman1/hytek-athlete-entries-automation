"""Data models for teams, meets, athletes, and entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Team:
    code: str
    name: str
    short_name: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "USA"
    email: str = ""
    reg_type: str = "OTH"
    team_type: str = "OTH"
    team_id: int = 1

    def __post_init__(self) -> None:
        self.code = (self.code or "").strip().upper()[:5]
        self.name = (self.name or "").strip()[:30]
        if not self.short_name:
            self.short_name = self.name[:16]
        else:
            self.short_name = self.short_name.strip()[:16]
        self.city = (self.city or "").strip()[:30]
        self.state = (self.state or "").strip()[:3]
        self.zip_code = (self.zip_code or "").strip()[:10]
        self.country = (self.country or "USA").strip()[:3]
        self.email = (self.email or "").strip()[:36]
        self.reg_type = (self.reg_type or "OTH").strip()[:4]
        self.team_type = (self.team_type or "OTH").strip()[:3]


@dataclass
class Meet:
    name: str
    start_date: date
    end_date: date
    age_up_date: Optional[date] = None
    course: str = "YO"  # YO = Yards (standard TM entry course code)
    location: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "USA"
    meet_id: int = 1
    deadline: Optional[date] = None
    max_ind_entries: int = 3
    max_rel_entries: int = 2
    max_total_entries: int = 5

    def __post_init__(self) -> None:
        self.name = (self.name or "").strip()[:45]
        if self.age_up_date is None:
            self.age_up_date = self.start_date
        if self.deadline is None:
            self.deadline = self.start_date
        self.course = (self.course or "YO").strip()[:2]
        self.location = (self.location or "").strip()[:45]
        self.address = (self.address or "").strip()[:30]
        self.city = (self.city or "").strip()[:30]
        self.state = (self.state or "").strip()[:3]
        self.zip_code = (self.zip_code or "").strip()[:10]
        self.country = (self.country or "USA").strip()[:20]


# Stroke integer codes for Team Manager MTEVENTE table:
# 1 = Freestyle, 2 = Backstroke, 3 = Breaststroke, 4 = Butterfly, 5 = Medley
STROKE_NAME_TO_CODE = {
    "FREESTYLE": 1,
    "BACKSTROKE": 2,
    "BREASTSTROKE": 3,
    "BUTTERFLY": 4,
    "MEDLEY": 5,
}


@dataclass
class MeetEvent:
    number: int
    gender: str  # "M", "F", or "X"
    distance: int
    stroke: str  # "FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY", "MEDLEY"
    is_relay: bool = False
    name: str = ""
    session: int = 1
    lo_hi: int = 99  # Open age group (0 to 109) in TM MTEVENTE is 99
    fee: float = 0.0

    def __post_init__(self) -> None:
        g = self.gender.upper() if self.gender else "X"
        self.gender = "M" if g.startswith("M") else ("F" if g.startswith("F") else "X")
        if not self.name:
            self.name = f"{self.distance} {self.stroke.title()} ({self.gender})"

    @property
    def stroke_code(self) -> int:
        return STROKE_NAME_TO_CODE.get(self.stroke.upper(), 1)

    @property
    def individual_or_relay(self) -> str:
        return "R" if self.is_relay else "I"


@dataclass
class Athlete:
    athlete_id: int  # 1-based sequential PK in the Access DB
    first_name: str
    last_name: str
    gender: str  # "M" or "F"
    id_no: str = ""  # Coach-provided ID (e.g. "27523")
    team_id: int = 1
    birth_date: Optional[date] = None
    age: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.first_name = (self.first_name or "").strip().title()[:20]
        self.last_name = (self.last_name or "").strip().title()[:20]
        g = (self.gender or "").strip().upper()
        self.gender = "M" if g.startswith("M") else ("F" if g.startswith("F") else "X")
        self.id_no = (self.id_no or "").strip()[:17]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def lookup_key(self) -> str:
        """Normalized key for athlete matching across CSVs."""
        return f"{self.first_name.strip().lower()}|{self.last_name.strip().lower()}"


@dataclass
class Entry:
    entry_id: int  # 1-based sequential PK
    athlete_id: int  # FK to Athlete.Athlete
    meet_id: int  # FK to MEET.Meet
    team_id: int  # FK to TEAM.Team
    event_number: int  # MtEvent (event number from HYV, e.g. 6)
    score: int = 0  # Time in CENTISECONDS (58.69 -> 5869). 0 = NT (No Time)
    course: str = "Y"  # Course: "Y", "S", "L"
    individual_or_relay: str = "I"  # "I" or "R"
