# Hytek Athlete and Entries Automation

A CLI-tool for populating .mdb files for use in Hytek's Team Manager software

## Usage

This tool is built for coaches that are entering athletes and entries for meets inside **Team Manager 8.0 Lite** and find the process tedious. It is also built to take in all required info from one or more *.csv files and programmatically populate athlete info including IDs and populate entry info using NLP (optional).

## Input
- ***.hyv meet file** which contains valid events for entry
- **althlete_ids.csv** (optional) which contains columns with first name, last name, and athlete ID
- **althlete_entries.csv** which contains columns with first name, last name, and athlete ID
  - [Form template we use](https://docs.google.com/forms/d/1_5v9OgbT_4q61MsBgtTZwK1yvOSkMpWTPARDmZM_7Fo/edit)
  - [Sheet template we get from the form](https://docs.google.com/spreadsheets/d/1ER1hUFQehKXsMGF54FkG0XjhNp1Oud5mWl59T8nKghk/edit?usp=sharing)