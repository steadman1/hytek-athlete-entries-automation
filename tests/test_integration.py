"""End-to-end integration test creating dummy HYV and CSV files and validating pipeline processing."""
import tempfile
from pathlib import Path

from hytek_ae.cli.pipeline import build_athlete_id_map, process_entries_csv
from hytek_ae.core.hyv_parser import load_hyv_file
from hytek_ae.core.nlp import NLPExtractor


def test_full_pipeline_mock_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # 1. Write a minimal valid .hyv file (exactly 11 semicolon-separated values in line 1)
        # Note: In HYV exports, Stroke uses single letters: A=Free, B=Back, C=Breast, D=Fly, E=Medley
        hyv_file = tmppath / "meet.hyv"
        hyv_content = (
            "Test Invitational;09/27/2026;09/27/2026;09/27/2026;Y;Test Pool;;Hy-Tek;8.0;;\n"
            "6;0;M;0;0;109;100;E;;;;;;;;;;\n"
            "24;0;M;0;0;109;50;A;;;;;;;;;;\n"
            "23;0;F;0;0;109;50;A;;;;;;;;;;\n"
        )
        hyv_file.write_text(hyv_content)

        # 2. Write an athletes ID CSV
        ids_file = tmppath / "athlete_ids.csv"
        ids_content = (
            "First Name,Last Name,ID Number\n"
            "Spencer,Steadman,27523\n"
            "Matthew,Alexander,46423\n"
        )
        ids_file.write_text(ids_content)

        # 3. Write an entries CSV
        entries_file = tmppath / "entries.csv"
        entries_content = (
            "First Name,Last Name,Gender,50 Freestyle,Event 2\n"
            "Spencer,Steadman,M,23.69,Event 6: 58.69\n"
            "Matthew,Alexander,M,22.20,NT\n"
        )
        entries_file.write_text(entries_content)

        # 4. Load HYV
        meet, valid_events = load_hyv_file(hyv_file)
        assert meet.name == "Test Invitational"
        assert len(valid_events) == 3

        # 5. Load Athlete IDs
        id_map = build_athlete_id_map(ids_file)
        assert id_map["spencer|steadman"] == "27523"
        assert id_map["matthew|alexander"] == "46423"

        # 6. Process Entries
        nlp = NLPExtractor(api_key=None)
        athletes, entries = process_entries_csv(
            entries_csv_path=entries_file,
            valid_events=valid_events,
            athlete_id_map=id_map,
            nlp_extractor=nlp,
            meet_id=meet.meet_id,
        )

        assert len(athletes) == 2
        assert athletes[0].first_name == "Spencer"
        assert athletes[0].id_no == "27523"
        assert athletes[1].first_name == "Matthew"
        assert athletes[1].id_no == "46423"

        # Spencer: 50 Free (ev 24, 23.69 -> 2369) + Event 6 (ev 6, 58.69 -> 5869)
        # Matthew: 50 Free (ev 24, 22.20 -> 2220)
        assert len(entries) >= 2
        spencer_entries = [e for e in entries if e.athlete_id == athletes[0].athlete_id]
        scores = {e.event_number: e.score for e in spencer_entries}
        assert scores.get(24) == 2369
        assert scores.get(6) == 5869
