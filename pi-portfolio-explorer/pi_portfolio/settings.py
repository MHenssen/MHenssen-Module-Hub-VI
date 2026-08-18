"""Application settings persistence (pi_portfolio_settings.json)."""
import os
import sys
import json
import datetime as dt

from .config import DEFAULT_SETTINGS_JSON, app_path, _settings_bool


def settings_path():
    return app_path(DEFAULT_SETTINGS_JSON)


def default_ui_settings():
    defaults = {
        "jiraUrl": os.getenv("JIRA_URL", "https://devtrack.vanderlande.com"),
        "jiraEmail": os.getenv("JIRA_EMAIL", ""),
        "jiraToken": os.getenv("JIRA_TOKEN", os.getenv("JIRA_API_TOKEN", "")),
        "kanbanBoardId": os.getenv("JIRA_KANBAN_BOARD_ID", "17289"),
        "piName": "26.3",
        "numSprints": 6,
        "commitmentDate": "",
        "forceCommitmentRefresh": False,
        "includeProgress": True,
    }
    existing = load_app_settings()
    defaults.update(existing)
    return normalize_app_settings(defaults)


def load_app_settings():
    p = settings_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"[settings] could not read {p}: {e}", file=sys.stderr)
        return {}


def save_app_settings(settings):
    p = settings_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(normalize_app_settings(settings), f, indent=2, ensure_ascii=False)
    return p


def normalize_app_settings(settings):
    s = dict(settings or {})
    s["jiraUrl"] = str(s.get("jiraUrl", "") or "").strip().rstrip("/")
    s["jiraEmail"] = str(s.get("jiraEmail", "") or "").strip()
    s["jiraToken"] = str(s.get("jiraToken", "") or "").strip()
    s["kanbanBoardId"] = str(s.get("kanbanBoardId", "") or "").strip()
    s["piName"] = str(s.get("piName", "") or "").strip().replace("PI ", "").replace("PI", "")
    try:
        s["numSprints"] = max(1, int(str(s.get("numSprints", 6)).strip() or "6"))
    except Exception:
        s["numSprints"] = 6
    for obsolete in ("ppiField", "teamField", "parentLinkField", "priorityField", "verifySsl"):
        s.pop(obsolete, None)
    s["commitmentDate"] = str(s.get("commitmentDate", "") or "").strip()
    if s["commitmentDate"]:
        try:
            dt.date.fromisoformat(s["commitmentDate"])
        except ValueError:
            s["commitmentDate"] = ""
    s["forceCommitmentRefresh"] = _settings_bool(s.get("forceCommitmentRefresh", False), False)
    s["includeProgress"] = _settings_bool(s.get("includeProgress", True), True)
    return s


def apply_app_settings_to_env(settings):
    env = dict(os.environ)
    env["JIRA_URL"] = settings.get("jiraUrl", "")
    env["JIRA_EMAIL"] = settings.get("jiraEmail", "")
    env["JIRA_TOKEN"] = settings.get("jiraToken", "")
    env["JIRA_KANBAN_BOARD_ID"] = settings.get("kanbanBoardId", "")
    env["JIRA_VERIFY_SSL"] = "1"
    return env
