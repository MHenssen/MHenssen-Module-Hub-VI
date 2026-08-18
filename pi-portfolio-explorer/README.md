# PI Portfolio Explorer

All-teams Jira portfolio dashboard: reads every Epic on the PI Kanban board,
classifies by Parent Link, Epic progress and Team, loads sprint predictability
from the Jira sprint reports, and serves a local web dashboard.

## Where this source came from

The original source was lost when its author left the company. This tree was
**reconstructed from the shipped `PI_Portfolio_Explorer.exe`** (v1.1.0):

1. The PyInstaller archive was extracted from the `.exe`.
2. The embedded `PYZ` archive yielded the 12 application modules as Python 3.14
   bytecode.
3. No decompiler supports Python 3.14, so each module was rebuilt by hand from
   its disassembly, guided by the line numbers, docstrings and constants the
   bytecode preserves.

**What is exact:** `pi_portfolio/templates/dashboard.html` is the original file,
copied byte-for-byte out of the bundle. All logic, constants, Jira custom-field
ids, JQL, log strings, Excel layout and docstrings are faithful to the compiled
bytecode.

**What may differ:** comments (the compiler discards them — those here were
written during reconstruction), blank-line placement, and a few dense one-line
statements that were expanded onto several lines for readability. Behaviour is
unchanged.

Verified after reconstruction: all 12 modules import; a full Excel write/read
round trip preserves epics, tickets, sprint codes, board tickets and
predictability; the workbook keeps its styling, formulas and Jira hyperlinks;
and the Flask dashboard serves the real template with data injected and renders
all seven tabs in a browser.

## Running from source

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python run.py                      # setup window (settings, Sync, Serve)
python run.py sync                 # Jira -> pi_portfolio_data.xlsx
python run.py serve --port 8010    # dashboard only
```

Needs Python 3.11+ with Tkinter for the setup window; `sync` and `serve` run
headless without it.

## Building the .exe

```bash
pip install pyinstaller
pyinstaller PI_Portfolio_Explorer.spec      # -> dist/PI_Portfolio_Explorer.exe
```

Build on Windows to get a Windows executable.

## Configuration

Settings live in `pi_portfolio_settings.json` next to the executable or entry
script, written by the setup window. Environment variables override them:
`JIRA_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`, `JIRA_KANBAN_BOARD_ID`, `JIRA_SP_FIELD`,
`JIRA_DEMAND_BULK_EPIC_BATCH`.

> The settings file contains a personal Jira access token. It is in
> `.gitignore` — keep it that way, and keep the folder private.

Jira custom-field ids are instance-specific and live at the top of
`pi_portfolio/config.py`; the predictability board ids are in
`pi_portfolio/predictability.py`.

## Module map

| Module | Purpose |
| --- | --- |
| `cli.py` | Argument parsing; entry point (`setup` / `sync` / `serve`) |
| `config.py` | Jira custom-field ids and app path helpers |
| `settings.py` | Load/save/normalize `pi_portfolio_settings.json` |
| `fields.py` | Pure Jira field flattening and normalization helpers |
| `jira_client.py` | Jira REST client: board, epics, children, changelog |
| `predictability.py` | Greenhopper sprint reports per team board |
| `sync.py` | Jira -> Excel sync, including instant (cache-reuse) mode |
| `excel_io.py` | Styled workbook writer and reader (source of truth) |
| `server.py` | Local Flask app serving the dashboard |
| `template.py` | PyInstaller-aware dashboard template loader |
| `setup_ui.py` | Tkinter setup window with live sync log |
| `templates/dashboard.html` | The dashboard itself (HTML/CSS/JS, single file) |

## Data flow

```
Jira REST  ->  jira_client / predictability  ->  sync  ->  pi_portfolio_data.xlsx
                                                               |
                                            server + templates/dashboard.html
                                                               |
                                                   http://127.0.0.1:<port>
```

The workbook is the source of truth: anyone holding it can open the dashboard
with no Jira access at all — skip Sync and press "Serve dashboard".

## Changing the dashboard

Visual and layout changes are almost always edits to
`pi_portfolio/templates/dashboard.html` alone — it is a single self-contained
file holding the styles, the tab markup and the rendering JavaScript. Changes to
*which* data is available need `jira_client.py` (fetch) plus `excel_io.py`
(persist) so new fields survive the workbook round trip.
