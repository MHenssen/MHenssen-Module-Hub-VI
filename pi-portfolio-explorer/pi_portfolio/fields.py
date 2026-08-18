"""Jira field flattening and normalization helpers (pure functions)."""


def _ppi_value(v):
    """Flatten a field value (PPI, Team, option...) to a display string."""
    if v is None:
        return ""
    if isinstance(v, dict):
        return str(v.get("value") or v.get("name") or v.get("title")
                   or v.get("displayName") or "")
    if isinstance(v, list):
        return ", ".join(_ppi_value(x) for x in v if x)
    return str(v)


def _parent_link_info(v):
    """Return (key_or_value, display_name) for Jira Parent Link custom field."""
    if v is None:
        return "", ""
    if isinstance(v, str):
        txt = v.strip()
        return txt, txt
    if isinstance(v, dict):
        fields = v.get("fields") if isinstance(v.get("fields"), dict) else {}
        key = str(v.get("key") or v.get("value") or v.get("name") or v.get("title") or v.get("displayName") or "").strip()
        name = str(fields.get("summary") or fields.get("name") or v.get("summary") or v.get("name") or v.get("value") or key or "").strip()
        return key, name
    if isinstance(v, (list, tuple, set)):
        pairs = [_parent_link_info(x) for x in v]
        keys = [k for k, _n in pairs if k]
        names = [n for _k, n in pairs if n]
        return ", ".join(keys), ", ".join(names or keys)
    txt = str(v).strip()
    return txt, txt


def _norm_status(v):
    return " ".join(str(v or "").strip().lower().replace("-", " ").replace("_", " ").split())


def _norm_pi(v):
    """Normalize a PI label for tolerant matching: 'PI 26.3' / '26.3' -> '26.3'."""
    s = str(v or "").strip().lower()
    if s.startswith("pi"):
        s = s[2:]
    return "".join(ch for ch in s if ch.isalnum() or ch == ".").strip(".")


def _norm_team_label(v):
    """Human-stable team label. Empty -> 'No team'."""
    s = str(v or "").strip()
    return s if s else "No team"


def _portfolio_product(epic):
    vals = [epic.get("key"), epic.get("parentLink"), epic.get("parentLinkName")]
    if any(str(v or "").strip().upper().startswith("SPO4-") for v in vals):
        return "SPO4"
    return "Maintain"


def _excel_exact_closed(value):
    return str(value or "").strip().lower() == "closed"
