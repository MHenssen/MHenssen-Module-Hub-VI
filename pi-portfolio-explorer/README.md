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

## Epic progress tab

Beyond the shared team/product/parent-link filters, this tab has four controls
aimed at running a PI review:

- **Epic team** — filters on the Epic's *own* assigned Team field. This is
  deliberately different from the team pills at the top of the page, which also
  match an Epic through any of its child tickets; use those to see everything a
  team touches, and this one to see the Epics a team actually owns.
- **Commitment** — Committed / Uncommitted, read from the Jira field of that
  name on the Epic (see below).
- **Drag to reorder** — grab the ⠿ handle to arrange Epics in your own review
  order. The first drag freezes the order currently on screen and then applies
  the move, so it works from any sort. A "My order" sort option and a **Reset
  order** button appear once an order exists. Dragging near the top or bottom of
  the window scrolls the page.
- **× to remove from view** — takes an Epic out of the tab, including out of its
  KPIs. Removed Epics collect in a bar above the table and come back with one
  click, or all at once.

Manual order and removed Epics are stored per browser and per PI in
`localStorage`. They are a personal reading aid: Sync never writes them back to
Jira, and other people opening the same workbook see the default order.

### The Committed field

Teams mark an Epic Uncommitted when dependencies mean they cannot guarantee it
for the Planned PI. The tool finds the field automatically by name (`Committed`,
`Commitment`, `PI Commitment`, …) on each Full Sync. If your Jira names it
something else, pin it explicitly:

```
JIRA_COMMITTED_FIELD=customfield_XXXXX
```

The value is stored in the `Committed` column of the Epics sheet. Workbooks
synced before this column existed still open fine — the tab then says the field
is not in the workbook and the filter stays inactive until the next Full Sync.

## Changing the dashboard

Visual and layout changes are almost always edits to
`pi_portfolio/templates/dashboard.html` alone — it is a single self-contained
file holding the styles, the tab markup and the rendering JavaScript. Changes to
*which* data is available need `jira_client.py` (fetch) plus `excel_io.py`
(persist) so new fields survive the workbook round trip.
