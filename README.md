# Hytek Athlete and Entries Automation

A CLI tool for programmatically generating `.mdb` database files for **Hy-Tek Team Manager 8.0 Lite**.

## Overview

Entering single-team athletes and meet entries manually inside Team Manager is tedious. This tool takes:
1. A **`.hyv` meet events file** (exported from Meet Manager)
2. An **`athlete_ids.csv`** file containing athlete names and coach-assigned IDs
3. An **`entries.csv`** spreadsheet (e.g., Google Forms/Sheets export) with names, gender, events, and seed times

It automatically maps athletes to their IDs, resolves swim events and times (via fast deterministic matching or an optional OpenAI completions endpoint for messy text), and generates a ready-to-use `.mdb` database file by cloning and populating the Team Manager template.

> **Environment Note:** Writing directly to a `.mdb` database requires the **Microsoft Access Database Engine** and pyodbc on a Windows (or virtualized Windows) machine. The parsing, NLP, and model verification logic can run anywhere.

---

## Installation

Using [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

---

## Usage

### Interactive Wizard (Default)
Simply run the CLI and follow the guided prompts:

```bash
uv run hytek-automated-athletes-entries
```

The wizard will:
1. Ask for paths if not provided.
2. Prompt for team information (Code, Name, City, State, etc.).
3. Load the meet events from the `.hyv` file.
4. Auto-detect columns in your CSVs and let you confirm or adjust them.
5. Populate the `.mdb` database.

### Scripted / CLI Flags (Skip Steps)
Provide command-line flags to skip individual steps or run non-interactively:

```bash
uv run hytek-automated-athletes-entries \
  -hyv "meet.hyv" \
  -ids "athletes.csv" \
  -e "entries.csv" \
  -o "meet_entries.mdb" \
  --team-code "VTECH" \
  --team-name "Swim Club at Virginia Tech" \
  --non-interactive
```

### NLP Event & Time Extraction (Optional)
If your entries CSV contains unstructured free-text (e.g. `"50 Free 23.5, 100 Fly 54.63"` or `"5 min 30 sec"`), you can pass an OpenAI API key or endpoint:

```bash
uv run hytek-automated-athletes-entries \
  -hyv "meet.hyv" \
  -e "entries.csv" \
  -o "meet_entries.mdb" \
  --openai-api-key "sk-..." \
  --openai-base-url "https://api.openai.com/v1"
```

Or set the environment variables:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

---

## Running Tests

All unit tests and end-to-end pipeline tests can be run locally on macOS/Linux:

```bash
uv run pytest -v
```
