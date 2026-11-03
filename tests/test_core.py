"""Unit tests for time parsing, csv reading, and SQL generators."""
import pytest
from datetime import date

from hytek_ae.core.models import Athlete, Entry, Meet, MeetEvent, Team
from hytek_ae.core.time_parser import format_centiseconds, parse_time_to_centiseconds
from hytek_ae.core.csv_reader import auto_detect_athlete_columns, auto_detect_entry_columns
from hytek_ae.core.nlp import NLPExtractor, parse_events_field, parse_times_field
from hytek_ae.db.operations import (
    pack_athlete_params,
    pack_entry_params,
    pack_meet_params,
    pack_team_params,
)


def test_time_parsing_centiseconds():
    # Centiseconds: 58.69 -> 5869
    assert parse_time_to_centiseconds("58.69") == 5869
    assert parse_time_to_centiseconds("58.69Y") == 5869
    assert parse_time_to_centiseconds("23.5") == 2350
    assert parse_time_to_centiseconds("23") == 2300

    # Minutes: 1:01.01 -> (60 + 1)*100 + 1 = 6101
    assert parse_time_to_centiseconds("1:01.01") == 6101
    assert parse_time_to_centiseconds("01:01.01") == 6101
    assert parse_time_to_centiseconds("4:32.10") == 27210

    # Float inputs
    assert parse_time_to_centiseconds(58.69) == 5869
    assert parse_time_to_centiseconds(0.0) == 0

    # No-times (NT)
    assert parse_time_to_centiseconds("NT") == 0
    assert parse_time_to_centiseconds("nt") == 0
    assert parse_time_to_centiseconds("None") == 0
    assert parse_time_to_centiseconds("") == 0
    assert parse_time_to_centiseconds(None) == 0


def test_format_centiseconds():
    assert format_centiseconds(5869) == "58.69"
    assert format_centiseconds(6101) == "1:01.01"
    assert format_centiseconds(0) == "NT"


def test_auto_detect_columns():
    # College club swimming roster export style
    ccs_headers = ["", "First Name", "Last Name", "Status", "Member ID", "Registration Date"]
    cols = auto_detect_athlete_columns(ccs_headers)
    assert cols["first_name"] == "First Name"
    assert cols["last_name"] == "Last Name"
    assert cols["id"] == "Member ID"

    # Form entries style
    form_headers = [
        "First Name", "Last Name", "Who do you plan to compete against",
        "Individual Events Select up to 3",
        "Please indicate if you would like to include a seed time in the following format",
    ]
    entry_cols = auto_detect_entry_columns(form_headers)
    assert entry_cols["first_name"] == "First Name"
    assert entry_cols["last_name"] == "Last Name"
    assert entry_cols["gender"] == "Who do you plan to compete against"
    assert entry_cols["events_col"] == "Individual Events Select up to 3"
    assert "seed time" in entry_cols["times_col"].lower()


def test_form_fields_parsing():
    valid_events = [
        MeetEvent(number=6, gender="M", distance=100, stroke="MEDLEY"),
        MeetEvent(number=19, gender="F", distance=50, stroke="BREASTSTROKE"),
        MeetEvent(number=20, gender="M", distance=50, stroke="BREASTSTROKE"),
        MeetEvent(number=23, gender="F", distance=50, stroke="FREESTYLE"),
        MeetEvent(number=24, gender="M", distance=50, stroke="FREESTYLE"),
    ]

    # Test event range e.g. "19-20: 50 Breast, 23-24: 50 Free" for Male
    chosen_m = parse_events_field("19-20: 50 Breast, 23-24: 50 Free", "M", valid_events)
    assert chosen_m == [20, 24]

    # Test event range for Female
    chosen_f = parse_events_field("19-20: 50 Breast, 23-24: 50 Free", "F", valid_events)
    assert chosen_f == [19, 23]

    # Test times parsing: multiline or comma separated
    times_text = "50 Free: 22.20\n20: 28.71"
    times = parse_times_field(times_text, "M", valid_events)
    assert times.get(24) == 2220
    assert times.get(20) == 2871


def test_deterministic_nlp_fallback():
    extractor = NLPExtractor(api_key=None)
    events = [
        MeetEvent(number=6, gender="M", distance=100, stroke="MEDLEY"),
        MeetEvent(number=24, gender="M", distance=50, stroke="FREESTYLE"),
    ]

    res = extractor.parse_entry_text("Event 6: 58.69", "M", events)
    assert res == [(6, 5869)]

    res2 = extractor.parse_entry_text("50 Free 23.69", "M", events)
    assert res2 == [(24, 2369)]


def test_param_packing_matches_schema():
    team = Team(code="VTECH", name="Swim Club at Virginia Tech", city="Blacksburg", state="VA")
    team_params = pack_team_params(team)
    assert team_params[0] == 1
    assert team_params[1] == "VTECH"

    meet = Meet(name="Pajama Meet", start_date=date(2026, 9, 27), end_date=date(2026, 9, 27))
    meet_params = pack_meet_params(meet)
    assert meet_params[0] == 1
    assert meet_params[1] == "Pajama Meet"

    ath = Athlete(athlete_id=1, first_name="Spencer", last_name="Steadman", gender="M", id_no="27523")
    ath_params = pack_athlete_params(ath)
    assert ath_params[0] == 1
    assert ath_params[6] == "Steadman"
    assert ath_params[7] == "Spencer"
    assert ath_params[11] == "27523"

    entry = Entry(entry_id=1, athlete_id=1, meet_id=1, team_id=1, event_number=6, score=5869)
    ent_params = pack_entry_params(entry)
    assert ent_params[0] == 1
    assert ent_params[1] == 1
    assert ent_params[5] == 5869
    assert ent_params[6] == 6
    assert ent_params[7] == 1
