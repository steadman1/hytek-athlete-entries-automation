"""Database operations: template initialization and SQL statement builders.

These operations build parameterized INSERT queries matching the exact schema
verified from Hy-Tek Team Manager 8.0 Lite (VTSC_NC_State.mdb).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

from hytek_ae.core.models import Athlete, Entry, Meet, Team

logger = logging.getLogger(__name__)

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_MDB = ASSET_DIR / "empty.mdb"


def initialize_output_mdb(dest_path: Path | str, overwrite: bool = True) -> Path:
    """Copy the clean template empty.mdb to the target output path."""
    dest = Path(dest_path)
    if not TEMPLATE_MDB.is_file():
        raise FileNotFoundError(f"Template database not found at {TEMPLATE_MDB}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {dest}")

    shutil.copyfile(TEMPLATE_MDB, dest)
    logger.info("Initialized new .mdb database at %s", dest)
    return dest


# SQL insert query generators & parameter packers:

SQL_INSERT_TEAM = """
INSERT INTO [TEAM] (
    [Team], [TCode], [TName], [Short], [TCity], [TState], [TZip], [TCntry],
    [TType], [Reg], [MinAge], [EMail], [TM50]
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def pack_team_params(team: Team) -> Tuple[Any, ...]:
    return (
        int(team.team_id),
        team.code,
        team.name,
        team.short_name,
        team.city,
        team.state,
        team.zip_code,
        team.country,
        team.team_type,
        team.reg_type,
        0,  # MinAge
        team.email,
        False,  # TM50
    )


SQL_INSERT_MEET = """
INSERT INTO [MEET] (
    [Meet], [MName], [Start], [End], [AgeUp], [Course], [Location],
    [IndCharge], [RelCharge], [SurCharge], [MaxIndEnt], [MaxRelEnt], [MaxEnt],
    [RestrictBest], [NonConform], [EnterAtQTime], [FacilityFee], [TeamFee],
    [MinAge], [EnforceQualifying], [Altitude], [EnforceSlowQtime], [BanNoTimes],
    [Lanes], [EvenOrOdd], [FastToSlow], [Masters], [ActiveFeeXMLSent],
    [MinAge10AndUnder], [DeadLine], [CustIndCharge], [CustRelCharge], [CustSurCharge],
    [CustIndAction], [CustRelAction], [CustSurAction], [Addr], [City], [State],
    [ZIP], [Cntry], [UseCustomFees], [OMEEntryStyle], [AllowCustomTimes],
    [UseSwimmersTeam], [HonorInviteList], [EntryTeam], [OnlyPreEntered],
    [CollectFeesOnline], [OMEValidated], [OMECustomTeam], [OMEFilterTeam],
    [OMENeedSync], [FileExportType], [EV3Version], [OMENeedsSync]
) VALUES (
    ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?, ?
)
"""


def pack_meet_params(meet: Meet) -> Tuple[Any, ...]:
    # Format dates as MM/DD/YYYY
    start_dt = meet.start_date.strftime("%m/%d/%Y 00:00:00")
    end_dt = meet.end_date.strftime("%m/%d/%Y 00:00:00")
    ageup_dt = (meet.age_up_date or meet.start_date).strftime("%m/%d/%Y 00:00:00")
    deadline_dt = (meet.deadline or meet.start_date).strftime("%m/%d/%Y 00:00:00")

    return (
        int(meet.meet_id),
        meet.name,
        start_dt,
        end_dt,
        ageup_dt,
        meet.course,
        meet.location,
        0.0,  # IndCharge
        0.0,  # RelCharge
        0.0,  # SurCharge
        meet.max_ind_entries,
        meet.max_rel_entries,
        meet.max_total_entries,
        False,  # RestrictBest
        0.0,  # NonConform
        False,  # EnterAtQTime
        0.0,  # FacilityFee
        0.0,  # TeamFee
        0,  # MinAge
        False,  # EnforceQualifying
        0,  # Altitude
        False,  # EnforceSlowQtime
        False,  # BanNoTimes
        0,  # Lanes
        0,  # EvenOrOdd
        False,  # FastToSlow
        False,  # Masters
        False,  # ActiveFeeXMLSent
        0,  # MinAge10AndUnder
        deadline_dt,
        0.0,  # CustIndCharge
        0.0,  # CustRelCharge
        0.0,  # CustSurCharge
        0,  # CustIndAction
        0,  # CustRelAction
        0,  # CustSurAction
        meet.address,
        meet.city,
        meet.state,
        meet.zip_code,
        meet.country,
        False,  # UseCustomFees
        3,  # OMEEntryStyle
        False,  # AllowCustomTimes
        True,  # UseSwimmersTeam
        False,  # HonorInviteList
        0,  # EntryTeam
        False,  # OnlyPreEntered
        False,  # CollectFeesOnline
        False,  # OMEValidated
        False,  # OMECustomTeam
        0,  # OMEFilterTeam
        False,  # OMENeedSync
        1,  # FileExportType
        0,  # EV3Version
        False,  # OMENeedsSync
    )


SQL_INSERT_ATHLETE = """
INSERT INTO [Athlete] (
    [Athlete], [Team1], [Team2], [Team3], [Group], [SubGr], [Last], [First],
    [Sex], [Age], [Class], [ID_NO], [Inactive], [Batch], [WMGroup], [WMSubGr],
    [DiveCertified], [AWRegType], [RegYear], [Foreign], [LastUpdated], [PC_Hide]
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?
)
"""


def pack_athlete_params(ath: Athlete) -> Tuple[Any, ...]:
    updated_dt = ath.last_updated.strftime("%m/%d/%Y %H:%M:%S")
    return (
        int(ath.athlete_id),
        int(ath.team_id),
        0,  # Team2
        0,  # Team3
        " ",  # Group
        " ",  # SubGr
        ath.last_name,
        ath.first_name,
        ath.gender,
        ath.age,
        " ",  # Class
        ath.id_no,
        False,  # Inactive
        0,  # Batch
        " ",  # WMGroup
        " ",  # WMSubGr
        False,  # DiveCertified
        "K",  # AWRegType
        0,  # RegYear
        False,  # Foreign
        updated_dt,
        False,  # PC_Hide
    )


SQL_INSERT_ENTRY = """
INSERT INTO [ENTRY] (
    [Meet], [Athlete], [I_R], [Team], [Course], [Score], [MtEvent], [Entry],
    [HEAT], [LANE], [FromOME]
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?
)
"""


def pack_entry_params(ent: Entry) -> Tuple[Any, ...]:
    return (
        int(ent.meet_id),
        int(ent.athlete_id),
        ent.individual_or_relay,
        int(ent.team_id),
        ent.course,
        int(ent.score),
        int(ent.event_number),
        int(ent.entry_id),
        0,  # HEAT
        0,  # LANE
        False,  # FromOME
    )
