"""Main entry point for Hy-Tek Athlete and Entries Automation."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

import click

from hytek_ae.cli.clean_path import CleanPath
from hytek_ae.cli.pipeline import build_athlete_id_map, process_entries_csv
from hytek_ae.cli.prompts import (
    prompt_team_info,
    resolve_athlete_columns,
    resolve_entry_columns,
)
from hytek_ae.core.csv_reader import read_csv_rows
from hytek_ae.core.hyv_parser import load_hyv_file
from hytek_ae.core.models import Team
from hytek_ae.core.nlp import NLPExtractor
from hytek_ae.db.writer import write_meet_database


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-hyv",
    "--events-path",
    type=CleanPath(exists=True, dir_okay=False),
    help=".hyv (hytek events) file path containing events for a specific swim meet",
)
@click.option(
    "-ids",
    "--athlete-ids-path",
    type=CleanPath(exists=True, dir_okay=False),
    help=".csv file path containing athletes' first name, last name, and IDs (e.g. memberTable.csv from College Club Swimming)",
)
@click.option(
    "-e",
    "--entries-path",
    type=CleanPath(exists=True, dir_okay=False),
    help=".csv file path containing athletes' chosen events, custom times, gender, etc.",
)
@click.option(
    "-o",
    "--output-path",
    type=CleanPath(dir_okay=False),
    help="File path to place the resulting populated .mdb file",
)
@click.option(
    "--team-code",
    help="Team 5-character abbreviation code (skips prompt if provided, e.g. VTECH)",
)
@click.option(
    "--team-name",
    help="Full team name (e.g. 'Swim Club at Virginia Tech')",
)
@click.option(
    "--openai-api-key",
    envvar="OPENAI_API_KEY",
    help="OpenAI API Key for NLP extraction (falls back to OPENAI_API_KEY env var)",
)
@click.option(
    "--openai-base-url",
    envvar="OPENAI_BASE_URL",
    help="Custom OpenAI completions endpoint / base URL",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Run without interactive wizard prompts, auto-detecting all columns",
)
def main(
    events_path: Optional[Path],
    athlete_ids_path: Optional[Path],
    entries_path: Optional[Path],
    output_path: Optional[Path],
    team_code: Optional[str],
    team_name: Optional[str],
    openai_api_key: Optional[str],
    openai_base_url: Optional[str],
    non_interactive: bool,
) -> None:
    """Hy-Tek Athlete and Entries Automation CLI."""
    click.echo("=" * 60)
    click.echo("  Hy-Tek Athlete & Entries Automation (Team Manager 8.0 Lite)")
    click.echo("=" * 60)

    # 1. Resolve required file paths if not passed as flags (using CleanPath for prompts too)
    clean_existing_file = CleanPath(exists=True, dir_okay=False)
    clean_dest_file = CleanPath(dir_okay=False)

    if not events_path:
        events_path = click.prompt(
            "\nEnter path to .hyv events file",
            type=clean_existing_file,
        )

    if not entries_path:
        entries_path = click.prompt(
            "Enter path to entries .csv file",
            type=clean_existing_file,
        )

    if not output_path:
        output_path = click.prompt(
            "Enter output .mdb file path",
            default="meet_entries.mdb",
            type=clean_dest_file,
        )

    # 2. Team information step
    if team_code and team_name:
        team = Team(code=team_code, name=team_name)
    elif non_interactive:
        team = Team(code=team_code or "TEAM1", name=team_name or "My Swim Team")
    else:
        team = prompt_team_info()

    # 3. Parse HYV meet events
    click.echo(f"\nParsing meet events from: {events_path}")
    meet, valid_events = load_hyv_file(events_path)
    click.echo(f"  Meet: {meet.name} ({len(valid_events)} events found)")

    # 4. Parse athlete IDs if provided (with interactive column selection)
    athlete_id_map = {}
    if athlete_ids_path:
        click.echo(f"\nProcessing athlete IDs from: {athlete_ids_path}")
        headers, _ = read_csv_rows(athlete_ids_path)
        col_map = resolve_athlete_columns(headers, skip_interactive=non_interactive)
        athlete_id_map = build_athlete_id_map(
            athlete_ids_path,
            first_name_col=col_map["first_name"],
            last_name_col=col_map["last_name"],
            id_col=col_map["id"],
        )
        click.echo(f"  Loaded {len(athlete_id_map)} athlete ID mappings.")

    # 5. Map entries columns (interactive or auto-detected)
    entries_headers, _ = read_csv_rows(entries_path)
    entry_cols = resolve_entry_columns(entries_headers, skip_interactive=non_interactive)

    # 6. Initialize NLP Extractor
    nlp = NLPExtractor(api_key=openai_api_key, base_url=openai_base_url)
    if nlp.is_available:
        click.echo("  NLP Extractor: enabled with OpenAI completions.")
    else:
        click.echo("  NLP Extractor: deterministic matching enabled.")

    # 7. Process Entries CSV
    click.echo(f"\nProcessing entries from: {entries_path}...")
    athletes, entries = process_entries_csv(
        entries_csv_path=entries_path,
        valid_events=valid_events,
        athlete_id_map=athlete_id_map,
        nlp_extractor=nlp,
        meet_id=meet.meet_id,
        team_id=team.team_id,
        first_name_col=entry_cols["first_name"],
        last_name_col=entry_cols["last_name"],
        gender_col=entry_cols["gender"],
        events_col=entry_cols["events_col"],
        times_col=entry_cols["times_col"],
    )
    click.echo(f"  Created {len(athletes)} athletes and {len(entries)} meet entries.")

    # 8. Write to output Access database
    click.echo(f"\nWriting to Microsoft Access database: {output_path}")
    try:
        write_meet_database(
            output_path=output_path,
            team=team,
            meet=meet,
            athletes=athletes,
            entries=entries,
            overwrite=True,
        )
        click.secho(f"\nSUCCESS! Meet entries database created at: {output_path.resolve()}", fg="green", bold=True)
    except Exception as exc:
        click.secho(f"\nDatabase write error: {exc}", fg="red")
        click.echo(
            "\nNote: Writing directly to an .mdb file requires Microsoft Access Database Engine (Windows). "
            "If running on macOS or Linux, transfer the output files or test on Windows."
        )


if __name__ == "__main__":
    main()
