from pathlib import Path

import click

# TODO:
#
# parse .hyv events file and build list of valid events
# parse .csv files
# return path to .mdb file

# available flags
# --events-path OR -hyv ".hyv file"
# --athlete-ids-path OR -ids ".csv file"
# --entries-path OR -e ".csv file"
# --output-path OR -o "populated .mdb file"


@click.command()
@click.option(
    "-hyv",
    "--events-path",
    help=".hyv (hytek events) file path containing events for a specific swim meet",
)
@click.option(
    "-ids",
    "--athlete-ids-path",
    help=".csv file path containing athletes' first name, last name, and IDs",
)
@click.option(
    "-e",
    "--entries-path",
    help=".csv file path containing athletes' chosen events, custom times, gender, etc. (see README.md for more info)",
)  # TODO: add all fields
@click.option(
    "-o",
    "--output-path",
    help="file path to place the resulting .mdb file",
)
def main() -> Path:
    # first, create Team object by taking direct cli input:
    #   5-char abbreviation
    #   full team name
    #   team registration (default: OTH)
    #   team type (default: OTH)
    #   address
    #   city
    #   postal code
    #   email address
    #   state
    #   country

    # second, parse the athletes .csv and ask user to select which columns should act as which fields
    #   first name
    #   last name
    #   ID

    # third, parse the entrie .csv and ask user to select which columns should act as which fields

    # fourth, build Athlete objects:
    #   first name
    #   last name
    #   gender
    #   team
    #   ID

    # fifth,

    return Path()


if __name__ in "__main__":
    pass
