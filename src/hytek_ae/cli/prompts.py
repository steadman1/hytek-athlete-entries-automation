"""Interactive wizard prompts and column selection for hytek-ae CLI."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import click

from hytek_ae.core.csv_reader import auto_detect_athlete_columns, auto_detect_entry_columns
from hytek_ae.core.models import Team


def prompt_team_info() -> Team:
    """Prompt the user interactively for team registration info."""
    click.echo("\n--- Step 1: Team Information ---")
    code = click.prompt("5-character team abbreviation (e.g. VTECH)", type=str).strip().upper()[:5]
    name = click.prompt("Full team name (e.g. Swim Club at Virginia Tech)", type=str).strip()
    short = click.prompt("Short name", default=name[:16], show_default=True).strip()
    city = click.prompt("City", default="", show_default=False).strip()
    state = click.prompt("State (e.g. VA)", default="", show_default=False).strip()
    zip_code = click.prompt("Postal Code", default="", show_default=False).strip()
    country = click.prompt("Country", default="USA", show_default=True).strip()
    email = click.prompt("Team Email", default="", show_default=False).strip()

    return Team(
        code=code,
        name=name,
        short_name=short,
        city=city,
        state=state,
        zip_code=zip_code,
        country=country,
        email=email,
    )


def select_column_interactively(
    role_name: str,
    headers: List[str],
    detected_col: Optional[str] = None,
    allow_none: bool = False,
) -> Optional[str]:
    """Ask user to select a column from headers with a numeric menu or accept detected default."""
    if not headers:
        return None

    click.echo(f"\nSelect column for '{role_name}':")
    for idx, h in enumerate(headers, 1):
        mark = " (detected)" if h == detected_col else ""
        # Clean multi-line headers for clean display
        display_h = h.replace("\n", " ")
        if len(display_h) > 75:
            display_h = display_h[:72] + "..."
        click.echo(f"  [{idx}] {display_h}{mark}")
    if allow_none:
        click.echo("  [0] (None / Skip)")

    default_idx = None
    if detected_col and detected_col in headers:
        default_idx = headers.index(detected_col) + 1
    elif allow_none:
        default_idx = 0

    while True:
        try:
            val = click.prompt(
                f"Choice for {role_name}",
                default=default_idx if default_idx is not None else 1,
                type=int,
            )
            if allow_none and val == 0:
                return None
            if 1 <= val <= len(headers):
                return headers[val - 1]
        except (click.Abort, KeyboardInterrupt):
            raise
        except Exception:
            pass
        click.echo("Invalid selection. Try again.")


def resolve_athlete_columns(
    headers: List[str],
    skip_interactive: bool = False,
    first_name_col: Optional[str] = None,
    last_name_col: Optional[str] = None,
    id_col: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Determine column mappings for athlete IDs file, auto-detecting or prompting as needed."""
    detected = auto_detect_athlete_columns(headers)

    fn = first_name_col or detected["first_name"]
    ln = last_name_col or detected["last_name"]
    id_c = id_col or detected["id"]

    if skip_interactive:
        return {"first_name": fn, "last_name": ln, "id": id_c}

    # Prompt interactively
    click.echo("\n--- Map Athlete IDs CSV Columns ---")
    fn = select_column_interactively("First Name", headers, fn, allow_none=False)
    ln = select_column_interactively("Last Name", headers, ln, allow_none=False)
    id_c = select_column_interactively("Athlete / Member ID", headers, id_c, allow_none=False)

    return {"first_name": fn, "last_name": ln, "id": id_c}


def resolve_entry_columns(
    headers: List[str],
    skip_interactive: bool = False,
    first_name_col: Optional[str] = None,
    last_name_col: Optional[str] = None,
    gender_col: Optional[str] = None,
    events_col: Optional[str] = None,
    times_col: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Determine column mappings for meet entries CSV (first name, last name, gender, events, custom times)."""
    detected = auto_detect_entry_columns(headers)

    fn = first_name_col or detected["first_name"]
    ln = last_name_col or detected["last_name"]
    gen = gender_col or detected["gender"]
    ev_c = events_col or detected["events_col"]
    time_c = times_col or detected["times_col"]

    if skip_interactive:
        return {
            "first_name": fn,
            "last_name": ln,
            "gender": gen,
            "events_col": ev_c,
            "times_col": time_c,
        }

    # Prompt interactively
    click.echo("\n--- Map Meet Entries CSV Columns ---")
    fn = select_column_interactively("First Name", headers, fn, allow_none=False)
    ln = select_column_interactively("Last Name", headers, ln, allow_none=False)
    gen = select_column_interactively("Gender / Division", headers, gen, allow_none=True)
    ev_c = select_column_interactively("Chosen Events", headers, ev_c, allow_none=True)
    time_c = select_column_interactively("Custom / Seed Times", headers, time_c, allow_none=True)

    return {
        "first_name": fn,
        "last_name": ln,
        "gender": gen,
        "events_col": ev_c,
        "times_col": time_c,
    }
