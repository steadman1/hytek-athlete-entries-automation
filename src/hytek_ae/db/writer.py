"""High-level database writer using pyodbc (runs on Windows)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from hytek_ae.core.models import Athlete, Entry, Meet, MeetEvent, Team
from hytek_ae.db.get_db import get_db
from hytek_ae.db.operations import (
    SQL_INSERT_ATHLETE,
    SQL_INSERT_ENTRY,
    SQL_INSERT_MEET,
    SQL_INSERT_MTEVENTE,
    SQL_INSERT_TEAM,
    initialize_output_mdb,
    pack_athlete_params,
    pack_entry_params,
    pack_meet_params,
    pack_mtevente_params,
    pack_team_params,
)

logger = logging.getLogger(__name__)


def write_meet_database(
    output_path: Path | str,
    team: Team,
    meet: Meet,
    athletes: List[Athlete],
    entries: List[Entry],
    events: Optional[List[MeetEvent]] = None,
    overwrite: bool = True,
) -> Path:
    """Copy template and execute all INSERT statements to produce the populated .mdb file."""
    dest = initialize_output_mdb(output_path, overwrite=overwrite)

    conn = get_db(dest)
    cursor = conn.cursor()

    try:
        # Insert TEAM
        cursor.execute(SQL_INSERT_TEAM, pack_team_params(team))

        # Insert MEET
        cursor.execute(SQL_INSERT_MEET, pack_meet_params(meet))

        # Insert MTEVENTE (Meet events from the HYV)
        if events:
            for ev in events:
                cursor.execute(SQL_INSERT_MTEVENTE, pack_mtevente_params(meet.meet_id, ev))

        # Insert Athletes in batches
        for ath in athletes:
            cursor.execute(SQL_INSERT_ATHLETE, pack_athlete_params(ath))

        # Insert Entries in batches
        for ent in entries:
            cursor.execute(SQL_INSERT_ENTRY, pack_entry_params(ent))

        conn.commit()
        logger.info(
            "Successfully wrote %d events, %d athletes and %d entries to %s",
            len(events or []),
            len(athletes),
            len(entries),
            dest,
        )
    finally:
        cursor.close()
        conn.close()

    return dest
