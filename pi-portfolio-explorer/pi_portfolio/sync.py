"""Jira -> Excel synchronization (cmd: sync)."""
import os
import sys
import datetime as dt

from .config import (
    CONFIG_PLANNED_PI_FIELD,
    CONFIG_EPIC_PRIORITY_FIELD,
    CONFIG_EPIC_PARENT_LINK_FIELD,
    CONFIG_EPIC_TEAM_FIELD,
    _settings_bool,
)
from .jira_client import JiraClient
from .predictability import fetch_sprint_predictability
from .settings import default_ui_settings, save_app_settings
from .excel_io import data_excel_path, write_portfolio_excel, read_portfolio_excel


def cmd_sync(args):
    settings = default_ui_settings()
    url = os.getenv("JIRA_URL") or settings.get("jiraUrl")
    email = os.getenv("JIRA_EMAIL") or settings.get("jiraEmail")
    token = os.getenv("JIRA_TOKEN") or os.getenv("JIRA_API_TOKEN") or settings.get("jiraToken")
    board = os.getenv("JIRA_KANBAN_BOARD_ID") or settings.get("kanbanBoardId")
    verify = True
    pi = getattr(args, "pi", None) or settings.get("piName")
    num_sprints = int(getattr(args, "num_sprints", None) or settings.get("numSprints", 6))
    include_progress = _settings_bool(settings.get("includeProgress", True), True)
    commitment_date = str(settings.get("commitmentDate") or "").strip()
    force_commitment = _settings_bool(settings.get("forceCommitmentRefresh", False), False)

    if not url or not token or not board:
        raise SystemExit("Missing Jira URL, token or Kanban board id. Save settings in the UI first.")

    print(f"[settings] Jira URL: {url}")
    print(f"[settings] Kanban board: {board}")
    print(f"[settings] target PI: {pi}  ({num_sprints} sprints)")
    print(f"[settings] fields: ppi={CONFIG_PLANNED_PI_FIELD} team={CONFIG_EPIC_TEAM_FIELD}"
          f" parentLink={CONFIG_EPIC_PARENT_LINK_FIELD} priority={CONFIG_EPIC_PRIORITY_FIELD}")
    print(f"[settings] sync mode: {'FULL Jira refresh' if include_progress else 'INSTANT Excel cache reuse'}")

    if not include_progress:
        # Instant mode: zero Jira requests. Re-read the workbook that is already
        # on disk and write it back out with the current settings applied.
        out = data_excel_path()
        if not os.path.exists(out):
            raise SystemExit("Instant cached Sync needs an existing pi_portfolio_data.xlsx. Check Full Sync once to create it.")
        try:
            data = read_portfolio_excel(out)
        except Exception as exc:
            raise SystemExit(f"Instant cached Sync could not read the existing workbook: {exc}")

        epics = list(data.get("epics") or [])
        child_count = sum(len(e.get("tickets") or []) for e in epics)
        if not epics or not child_count:
            raise SystemExit("The Excel cache has no Epic/ticket data. Check Full Sync once to rebuild it from Jira.")
        meta = dict(data.get("meta") or {})
        meta.update({
            "piName": pi,
            "numSprints": num_sprints,
            "jiraUrl": url,
            "kanbanBoardId": str(board),
            "syncedAt": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "commitmentDate": commitment_date,
            "syncMode": "Excel cache reuse",
        })
        data["meta"] = meta
        commitment_count = len((data.get("commitment") or {}).get("tickets") or [])
        if force_commitment:
            print("[fast-sync] Force commitment refresh selected; refreshing Predictability only")
            jc = JiraClient(url, email, token, board, os.getenv("JIRA_SP_FIELD") or None, verify=verify)
            print(f"[jira] auth={jc.auth_mode}; user={jc.whoami}")
            data["predictability"] = fetch_sprint_predictability(jc, pi, num_sprints)
            settings["forceCommitmentRefresh"] = False
            save_app_settings(settings)
            print("[fast-sync] Predictability refreshed; option reset")
        else:
            print(f"[fast-sync] zero Jira requests; reusing {len(epics)} Epic(s), {child_count} child ticket(s), "
                  f"{len(data.get('boardTickets') or [])} board ticket(s), and {commitment_count} commitment ticket(s) from Excel")
        write_portfolio_excel(data, out)
        teams = sorted({e.get("team") or "No team" for e in epics})
        parents = sorted({e.get("parentLink") or "No parent link" for e in epics})
        total_sp = sum(float(e.get("totalSp") or 0) for e in epics)
        done_sp = sum(float(e.get("doneSp") or 0) for e in epics)
        print(f"[done] refreshed cached workbook {out}")
        print(f"[done] {len(epics)} epic(s), {len(teams)} team(s), {len(parents)} parent link(s); {done_sp:.1f}/{total_sp:.1f} SP done")
        return

    jc = JiraClient(url, email, token, board, os.getenv("JIRA_SP_FIELD") or None, verify=verify)
    print(f"[jira] auth={jc.auth_mode}; user={jc.whoami}")
    board_columns = jc._board_columns()
    board_tickets = jc.fetch_board_tickets(include_progress=True, team_field=CONFIG_EPIC_TEAM_FIELD)
    epics = jc.fetch_portfolio(CONFIG_PLANNED_PI_FIELD, pi,
                               team_field=CONFIG_EPIC_TEAM_FIELD,
                               priority_field=CONFIG_EPIC_PRIORITY_FIELD,
                               include_progress=True)
    commitment = {"date": "", "tickets": []}
    if commitment_date:
        cached = {}
        if not force_commitment and os.path.exists(data_excel_path()):
            try:
                cached = read_portfolio_excel(data_excel_path()).get("commitment") or {}
            except Exception as exc:
                print(f"[commitment] cache could not be read ({exc}); rebuilding", file=sys.stderr)
        if not force_commitment and str(cached.get("date") or "") == commitment_date and bool(cached.get("tickets")):
            commitment = cached
            print(f"[commitment] reused cached snapshot for {commitment_date}: {len(commitment.get('tickets') or [])} ticket(s)")
        else:
            reason = "forced refresh" if force_commitment else "no matching cached snapshot"
            print(f"[commitment] rebuilding snapshot for {commitment_date} ({reason})")
            commitment = jc.commitment_snapshot(epics, commitment_date, team_field=CONFIG_EPIC_TEAM_FIELD)
            if force_commitment:
                settings["forceCommitmentRefresh"] = False
                save_app_settings(settings)
                print("[commitment] force refresh completed; option reset")

    predictability = fetch_sprint_predictability(jc, pi, num_sprints)
    teams = sorted({e.get("team") or "No team" for e in epics})
    parents = sorted({e.get("parentLink") or "No parent link" for e in epics})
    data = {
        "meta": {
            "piName": pi,
            "numSprints": num_sprints,
            "jiraUrl": url,
            "kanbanBoardId": str(board),
            "syncedAt": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "teams": teams,
            "boardColumns": board_columns,
            "commitmentDate": commitment_date,
        },
        "epics": epics,
        "boardTickets": board_tickets,
        "commitment": commitment,
        "predictability": predictability,
    }
    out = data_excel_path()
    write_portfolio_excel(data, out)
    total_sp = sum(float(e.get("totalSp") or 0) for e in epics)
    done_sp = sum(float(e.get("doneSp") or 0) for e in epics)
    print(f"[done] wrote {out}")
    print(f"[done] {len(epics)} epic(s), {len(teams)} team(s), {len(parents)} parent link(s); {done_sp:.1f}/{total_sp:.1f} SP done")
