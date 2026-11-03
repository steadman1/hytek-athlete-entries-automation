# Hytek Athlete and Entries Automation

A CLI tool for programmatically generating `.mdb` database files for **Hy-Tek Team Manager 8.0 Lite**.

## Overview

Entering single-team athletes and meet entries manually inside Team Manager is tedious. This tool takes:
1. A **`.hyv` meet events file** (exported from Meet Manager)
2. An **`athlete_ids.csv` / `memberTable.csv`** roster file containing athlete names and IDs (such as the College Club Swimming roster download)
3. An **`entries.csv`** spreadsheet (e.g. Google Forms / Google Sheets responses) with names, gender/division, chosen events, and custom/seed times

It automatically maps athletes to their IDs, populates the meet events table (`MTEVENTE`), resolves swim events and centisecond times (via high-speed deterministic matching or an optional OpenAI completion endpoint for unstructured text), and writes a fully populated, ready-to-use `.mdb` database file by cloning the clean Team Manager template.

> **Environment Note:** Writing directly to a `.mdb` database requires the **Microsoft Access Database Engine** and `pyodbc` on a Windows (or virtualized Windows) machine. The parsing, NLP, column mapping, and model verification logic can run on any platform (macOS/Linux/Windows). Team Manager databases use the internal Jet master password `5hY-tek`, which is automatically supplied by the driver.

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
1. Prompt for file paths (supports terminal drag-and-drop with quotes and spaces automatically).
2. Ask if you have an athlete roster / IDs CSV (e.g. `memberTable.csv`).
3. Interactively prompt for team information (Code, Name, City, State, etc.).
4. Load meet events from the `.hyv` file and insert them into `MTEVENTE`.
5. Display detected columns for both CSVs and let you confirm or choose custom columns via a numbered menu.
6. Populate the `.mdb` database with `TEAM`, `MEET`, `MTEVENTE`, `Athlete`, and `ENTRY` records.

### Scripted / CLI Flags (Headless or Custom)
Provide command-line flags to skip individual steps or run non-interactively:

```bash
uv run hytek-automated-athletes-entries \
  -hyv "meet.hyv" \
  -ids "memberTable.csv" \
  -e "entries.csv" \
  -o "meet_entries.mdb" \
  --team-code "VTECH" \
  --team-name "Swim Club at Virginia Tech" \
  --non-interactive
```

All path options and interactive prompts accept paths wrapped in whitespace, `'`, `"`, or terminal drag-and-drop escaping (`\ `).

---

## Time Pattern Matching

The tool parses swim times directly into integer centiseconds (e.g. `58.69` -> `5869`, `0` for `NT` / No Time).

Supported formats include:
* Standard times: `28.63`, `00:48.00`, `1:01.01`, `23.5`, `NT`
* Event number + time: `"6, 26.56"`, `Event 24: 23.69`
* Inline multi-event strings: `"50 back: 3, 28.63 50 fly: 13, 28.68 50 free: 19, 24.33"`
* Form response strings with quotes and parentheses: `"50 back: (3, 28.63)" '50 fly: (13, 28.68)'`
* Multiline times:
  ```text
  100 Free: 48.83
  100 Fly: 54.63
  50 Free: 22.20
  ```

---

## NLP Extraction & `--force-nlp`

By default, deterministic regex parsing runs first for maximum speed and accuracy. If an entry cannot be parsed deterministically, it falls back to an OpenAI completion endpoint if configured.

To bypass deterministic matching and force all times/entries to go directly to the LLM:

```bash
uv run hytek-automated-athletes-entries \
  -hyv "meet.hyv" \
  -ids "memberTable.csv" \
  -e "entries.csv" \
  -o "meet_entries.mdb" \
  --openai-api-key "sk-..." \
  --openai-base-url "https://api.openai.com/v1" \
  --force-nlp
```

Or configure environment variables:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

---

## Database Architecture (`.mdb`)

The generated `.mdb` clones the Team Manager 8.0 Lite template and populates:

| Table | Contents |
|---|---|
| `TEAM` | Team code, full name, short name, location, and contact information |
| `MEET` | Meet name, start/end dates, course code (`YO`), entry limits |
| `MTEVENTE` | Complete list of meet events parsed from `.hyv` (event number, distance, stroke 1–5, gender `M`/`F`, `I`/`R`, `lo_hi=99`) |
| `Athlete` | 1-based `Athlete` PK, `First`, `Last`, `Sex`, and coach-assigned `ID_NO` (from roster or entries CSV) |
| `ENTRY` | Sequential 1-based `Entry` PK, `Athlete` FK, `MtEvent` number, `Course` (`Y`), `Score` (centiseconds) |

---

## Running Tests

All unit and integration tests run cross-platform without requiring Access on macOS or Linux:

```bash
uv run pytest -v
```
