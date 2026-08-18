"""Configuration constants and application path helpers."""
import os
import sys

DEFAULT_DATA_XLSX = "pi_portfolio_data.xlsx"
DEFAULT_SETTINGS_JSON = "pi_portfolio_settings.json"

# Jira custom field ids. These are instance specific: if this tool is pointed
# at a different Jira, these are the ids that need to change. An empty value
# means "detect automatically at runtime" (see JiraClient._detect_sp_field).
CONFIG_DISCIPLINE_FIELD = "customfield_12329"
CONFIG_STORY_POINTS_FIELD = ""
CONFIG_PLANNED_PI_FIELD = "customfield_16925"
CONFIG_EPIC_PRIORITY_FIELD = "customfield_11120"
CONFIG_EPIC_PARENT_LINK_FIELD = "customfield_14121"
CONFIG_EPIC_TEAM_FIELD = "customfield_14120"
CONFIG_TICKET_SPRINT_FIELD = "customfield_11325"
CONFIG_BULK_EPIC_BATCH = int(os.getenv("JIRA_DEMAND_BULK_EPIC_BATCH", "40") or "40")


def app_base_dir():
    """Folder where the app lives. Generated files are saved here by default.

    - Frozen (.exe): the folder containing the executable.
    - Normal Python: the folder containing the entry script (run.py).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    candidates = []
    try:
        candidates.append(os.path.abspath(sys.argv[0]))
    except Exception:
        pass
    for candidate in candidates:
        if candidate and candidate.lower().endswith(".py") and os.path.exists(candidate):
            return os.path.dirname(candidate)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _settings_bool(value, default=False):
    """Parse UI/settings booleans consistently."""
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def app_path(path):
    """Resolve a relative filename next to this script."""
    p = str(path or "").strip()
    if not p:
        return p
    if os.path.isabs(p) or p.lower().startswith("http"):
        return p
    return os.path.join(app_base_dir(), p)
