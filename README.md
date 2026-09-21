# Hytek Athlete and Entries Automation

A CLI-tool for populating .mdb files for use in Hytek's Team Manager software

## Usage

This tool is built for coaches that are entering single-team athletes and entries for meets inside **Team Manager 8.0 Lite** and find the process tedious. It is also built to take in all required info from one or more *.csv files and programmatically populate athlete info including IDs and populate entry info using NLP (optional).

**This too must be run on a Windows (or virtualized windows) machine with a Microsoft Access Database Engine installation** (gross)

## Input
- **.hyv** which contains valid events for entry
- **althletes.csv** which contains columns with first name, last name, and athlete ID (optional)
- **entries.csv** which contains columns with (UPDATE) first name, last name, gender, events, custom times
  - [Form template we use](https://docs.google.com/forms/d/1_5v9OgbT_4q61MsBgtTZwK1yvOSkMpWTPARDmZM_7Fo/edit)
  - [Sheet template we get from the form](https://docs.google.com/spreadsheets/d/1ER1hUFQehKXsMGF54FkG0XjhNp1Oud5mWl59T8nKghk/edit?usp=sharing)
