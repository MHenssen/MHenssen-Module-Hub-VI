"""Minimal Jira REST client used by the portfolio sync."""
import sys
import datetime as dt

from .config import (
    CONFIG_DISCIPLINE_FIELD,
    CONFIG_EPIC_PRIORITY_FIELD,
    CONFIG_EPIC_PARENT_LINK_FIELD,
    CONFIG_EPIC_TEAM_FIELD,
    CONFIG_TICKET_SPRINT_FIELD,
    CONFIG_EPIC_COMMITTED_FIELD,
    CONFIG_BULK_EPIC_BATCH,
)
from .fields import (
    _ppi_value,
    _parent_link_info,
    _norm_status,
    _norm_pi,
    _norm_team_label,
    _portfolio_product,
)


class JiraClient:
    """Minimal Jira client: only what the all-teams portfolio read needs."""

    def __init__(self, base, email, token, kanban_board_id, sp_field=None,
                 disc_field=CONFIG_DISCIPLINE_FIELD, verify=True):
        import requests
        from requests.auth import HTTPBasicAuth
        self.s = requests.Session()
        self.s.headers.update({"Accept": "application/json"})
        self.base = base.rstrip("/")
        self.board_id = kanban_board_id
        self.disc_field = disc_field
        self.verify = verify
        if not verify:
            import urllib3
            urllib3.disable_warnings()

        self._auth = None
        self._headers = {}
        self.auth_mode = None
        attempts = [("bearer", None, {"Authorization": f"Bearer {token}"})]
        if email:
            attempts.append(("basic-email", HTTPBasicAuth(email, token), {}))
            attempts.append(("basic-user", HTTPBasicAuth(email.split("@")[0], token), {}))
        for label, auth, hdr in attempts:
            try:
                r = self.s.get(self.base + "/rest/api/2/myself", auth=auth, headers=hdr,
                               timeout=30, verify=verify)
            except Exception:
                continue
            if r.status_code != 200:
                continue
            self._auth, self._headers, self.auth_mode = auth, hdr, label
            self.whoami = (r.json() or {}).get("displayName", "?")
            break
        if self.auth_mode is None:
            raise SystemExit("Jira auth failed (no method returned 200). Check your PAT.")
        self.sp_field = sp_field or self._detect_sp_field()

    def _get(self, path, **params):
        r = self.s.get(self.base + path, auth=self._auth, headers=self._headers,
                       params=params, timeout=40, verify=self.verify)
        r.raise_for_status()
        return r.json()

    def _board_columns(self):
        """Read Jira board columns and exact status mappings in display order."""
        try:
            cfg = self._get(f"/rest/agile/1.0/board/{self.board_id}/configuration") or {}
            cols = (cfg.get("columnConfig") or {}).get("columns") or []
            out = []
            for idx, col in enumerate(cols):
                out.append({
                    "id": f"column_{idx}",
                    "name": str(col.get("name") or f"Column {idx + 1}"),
                    "statusIds": [str(st.get("id")) for st in (col.get("statuses") or []) if st.get("id") not in (None, "")],
                    "doneColumn": idx == len(cols) - 1,
                })
            print(f"[kanban] loaded {len(out)} Jira board column(s): " + ", ".join(c["name"] for c in out), flush=True)
            return out
        except Exception as e:
            print(f"[kanban] could not load Jira board columns ({e})", file=sys.stderr, flush=True)
            return []

    def _detect_sp_field(self):
        try:
            bc = self._get(f"/rest/agile/1.0/board/{self.board_id}/configuration")
            fid = ((bc.get("estimation") or {}).get("field") or {}).get("fieldId")
            if fid:
                print(f"[sp] board estimation field = {fid}", file=sys.stderr)
                return fid
        except Exception as e:
            print(f"[sp] board configuration unavailable ({e})", file=sys.stderr)
        try:
            for f in self._get("/rest/api/2/field"):
                if f.get("name", "").lower() in ("story points", "story point estimate"):
                    print(f"[sp] matched by name -> {f['id']}", file=sys.stderr)
                    return f["id"]
        except Exception:
            pass
        print("[sp] WARNING falling back to customfield_10016 (set JIRA_SP_FIELD if empty)", file=sys.stderr)
        return "customfield_10016"

    def _discipline(self, fields):
        src = self.disc_field
        raw = None
        if src == "component":
            comps = fields.get("components") or []
            raw = comps[0]["name"] if comps else None
        elif src == "label":
            labs = fields.get("labels") or []
            raw = labs[0] if labs else None
        else:
            v = fields.get(src)
            if isinstance(v, list) and len(v) > 0:
                v = v[0]
            raw = v.get("value") if isinstance(v, dict) else v
        return str(raw) if raw else "Unassigned"

    def _demand_sp_value(self, fields):
        """Remaining/total SP: customfield_15220 (done/total -> total-done), then customfield_17121, then board SP."""
        import re

        def flatten(raw):
            if raw is None:
                return ""
            if isinstance(raw, (int, float)):
                return str(raw)
            if isinstance(raw, dict):
                parts = []
                for k in ("value", "name", "title", "displayName"):
                    if raw.get(k) not in (None, ""):
                        parts.append(str(raw.get(k)))
                if not parts:
                    parts = [flatten(v) for v in raw.values() if v not in (None, "")]
                return " ".join(p for p in parts if p).strip()
            if isinstance(raw, list):
                return " ".join(flatten(x) for x in raw if x not in (None, "")).strip()
            return str(raw).strip()

        def nums_from(raw):
            txt = flatten(raw)
            return txt, re.findall(r"-?\d+(?:[\.,]\d+)?", txt)

        def to_float(s):
            return float(str(s).replace(",", "."))

        def parse_general(raw):
            txt, nums = nums_from(raw)
            if not txt or not nums:
                return None
            try:
                return to_float(txt)
            except Exception:
                try:
                    return to_float(nums[0])
                except Exception:
                    return None

        raw15220 = (fields or {}).get("customfield_15220")
        txt15220, nums15220 = nums_from(raw15220)
        if txt15220 and nums15220:
            if "/" in txt15220 and len(nums15220) >= 2:
                try:
                    done = to_float(nums15220[0])
                    total = to_float(nums15220[1])
                    if total > 0:
                        return max(0.0, total - done), "customfield_15220"
                except Exception:
                    pass
            else:
                try:
                    return to_float(nums15220[0]), "customfield_15220"
                except Exception:
                    pass

        v17121 = parse_general((fields or {}).get("customfield_17121"))
        if v17121 is not None:
            return v17121, "customfield_17121"
        fallback = parse_general((fields or {}).get(self.sp_field))
        if fallback is not None:
            return fallback, self.sp_field
        return 0.0, ""

    def _demand_done_sp_value(self, fields):
        """Best-effort SP already done (customfield_15220 done part, else 17121/board SP)."""
        import re

        def to_float(x):
            return float(str(x).strip().replace(",", "."))

        raw = (fields or {}).get("customfield_15220")
        txt = _ppi_value(raw).strip() if raw not in (None, "") else ""
        nums = re.findall(r"-?\d+(?:[\.,]\d+)?", txt)
        if txt and nums:
            try:
                if "/" in txt and len(nums) >= 2:
                    done, total = to_float(nums[0]), to_float(nums[1])
                    if total > 0:
                        return max(0.0, done), "customfield_15220_done"
                else:
                    v = to_float(nums[0])
                    if v > 0:
                        return v, "customfield_15220_done"
            except Exception:
                pass

        v17121 = self._demand_sp_value({**(fields or {}), "customfield_15220": None})[0]
        if v17121 and v17121 > 0:
            return v17121, "customfield_17121"
        return 0.0, ""

    def _sp_total_value(self, fields):
        """Total SP for progress math: done + remaining when 15220 is done/total, else remaining value."""
        import re
        raw = (fields or {}).get("customfield_15220")
        txt = _ppi_value(raw).strip() if raw not in (None, "") else ""
        nums = re.findall(r"-?\d+(?:[\.,]\d+)?", txt)
        if txt and "/" in txt and len(nums) >= 2:
            try:
                total = float(str(nums[1]).replace(",", "."))
                if total > 0:
                    return total
            except Exception:
                pass
        return self._demand_sp_value(fields)[0]

    def _epic_priority_value(self, fields, priority_field=None):
        if not priority_field:
            return None
        raw = (fields or {}).get(priority_field)
        if raw in (None, ""):
            return None
        import re
        txt = _ppi_value(raw).strip()
        if not txt:
            return None
        m = re.search(r"-?\d+(?:[\.,]\d+)?", txt)
        if not m:
            return None
        try:
            n = int(float(m.group(0).replace(",", ".")))
            return n if n >= 0 else None
        except Exception:
            return None

    def _issue_sprint_raw_text(self, fields):
        def flat(v):
            if v in (None, ""):
                return ""
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, dict):
                preferred = []
                for k in ("value", "name", "title", "displayName"):
                    if v.get(k) not in (None, ""):
                        preferred.append(str(v.get(k)))
                rest = [flat(x) for x in v.values() if x not in (None, "")]
                return " ".join(p for p in preferred + rest if p).strip()
            if isinstance(v, (list, tuple, set)):
                return " | ".join(flat(x) for x in v if x not in (None, "")).strip()
            return str(v).strip()

        texts = []
        for key in (CONFIG_TICKET_SPRINT_FIELD, "sprint", "closedSprints"):
            if not key:
                continue
            raw = (fields or {}).get(key)
            txt = flat(raw)
            if not txt:
                continue
            texts.append(txt)
        return " | ".join(texts).strip()

    def _issue_sprint_codes(self, fields):
        """Extract PI sprint codes like 26.3.1 from Jira sprint fields."""
        import re
        txt = self._issue_sprint_raw_text(fields)
        out = []
        for m in re.finditer(r"(?:\bPI\s*)?(\d{2}\.\d+\.\d+)\b", txt, flags=re.I):
            code = m.group(1)
            if code not in out:
                out.append(code)

        def key(code):
            try:
                return tuple(int(x) for x in code.split("."))
            except Exception:
                return (999, 999, 999)

        return sorted(out, key=key)

    def _demand_fields(self, extra=None, include_sprint=False):
        base = ["summary", "status", "issuetype", "assignee", "components", "labels", self.sp_field,
                "customfield_15220", "customfield_17121"]
        if self.disc_field not in ("component", "label"):
            base.append(self.disc_field)
        if include_sprint and CONFIG_TICKET_SPRINT_FIELD:
            base.append(CONFIG_TICKET_SPRINT_FIELD)
        base += list(extra or [])
        return ",".join(f for f in dict.fromkeys(base) if f)

    def _issue_is_closed(self, fields):
        st = (fields or {}).get("status") or {}
        name = _norm_status(st.get("name") if isinstance(st, dict) else st)
        cat = _norm_status(((st.get("statusCategory") or {}).get("key")
                            or (st.get("statusCategory") or {}).get("name") or "")
                           if isinstance(st, dict) else "")
        return name in ("closed", "done", "resolved", "cancelled", "canceled", "rejected") or cat == "done"

    def _search_issues(self, jql, fields, max_results=100):
        out, start = [], 0
        while True:
            d = self._get("/rest/api/2/search", jql=jql, fields=fields, startAt=start, maxResults=max_results)
            got = d.get("issues", [])
            out += got
            if not got or start + d.get("maxResults", max_results) >= d.get("total", 0):
                break
            start += max_results
        return out

    def _detect_epic_link_field(self):
        if hasattr(self, "_epic_link_field_cache"):
            return self._epic_link_field_cache
        self._epic_link_field_cache = ""
        try:
            for f in self._get("/rest/api/2/field"):
                if str(f.get("name") or "").strip().lower() == "epic link":
                    self._epic_link_field_cache = f.get("id") or ""
                    break
        except Exception:
            self._epic_link_field_cache = ""
        return self._epic_link_field_cache

    def _detect_committed_field(self):
        """Find the Jira field holding Committed / Uncommitted for the Planned PI.

        Teams set this per Epic to flag work they cannot guarantee for the PI.
        CONFIG_EPIC_COMMITTED_FIELD (env JIRA_COMMITTED_FIELD) pins the id;
        otherwise it is matched by field name once per run.
        """
        if hasattr(self, "_committed_field_cache"):
            return self._committed_field_cache
        if CONFIG_EPIC_COMMITTED_FIELD:
            self._committed_field_cache = CONFIG_EPIC_COMMITTED_FIELD
            print(f"[committed] using configured field {CONFIG_EPIC_COMMITTED_FIELD}")
            return self._committed_field_cache
        self._committed_field_cache = ""
        try:
            for f in self._get("/rest/api/2/field"):
                name = str(f.get("name") or "").strip().lower()
                if name in ("committed", "commitment", "pi commitment", "committed?",
                            "commitment status", "pi commitment status"):
                    self._committed_field_cache = f.get("id") or ""
                    print(f"[committed] matched field by name '{name}' -> {self._committed_field_cache}")
                    break
        except Exception as e:
            print(f"[committed] could not read the Jira field list ({e})", file=sys.stderr)
        if not self._committed_field_cache:
            print("[committed] no Committed field found; set JIRA_COMMITTED_FIELD to its "
                  "custom field id to enable the committed/uncommitted filter", file=sys.stderr)
        return self._committed_field_cache

    @staticmethod
    def _committed_value(fields, committed_field):
        """Normalize the Committed field to 'Committed', 'Uncommitted' or ''."""
        if not committed_field:
            return ""
        txt = _ppi_value((fields or {}).get(committed_field)).strip()
        low = txt.lower()
        if low.startswith("uncommit") or low.startswith("un-commit") or low in ("no", "false"):
            return "Uncommitted"
        if low.startswith("commit") or low in ("yes", "true"):
            return "Committed"
        return txt

    def _issue_epic_ref_key(self, fields, epic_link_field=""):
        fields = fields or {}
        parent = fields.get("parent")
        if isinstance(parent, dict) and parent.get("key"):
            return str(parent.get("key")).strip()
        if epic_link_field:
            v = fields.get(epic_link_field)
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, dict):
                return str(v.get("key") or v.get("value") or v.get("name") or "").strip()
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict):
                    return str(first.get("key") or first.get("value") or first.get("name") or "").strip()
                return str(first).strip()
        return ""

    def _fetch_parent_link_names_bulk(self, parent_keys):
        """Return {parent_key: summary} for Parent Link issue keys, in chunks."""
        keys = [str(k).strip() for k in (parent_keys or []) if str(k or "").strip()]
        keys = sorted(set(k for k in keys if k.lower() != "no parent link"))
        if not keys:
            return {}
        out = {}
        batch_size = 50
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            key_list = ",".join(batch)
            try:
                found = self._search_issues(f"key in ({key_list})", fields="summary")
            except Exception as e:
                print(f"[parent-link] could not fetch parent names for {len(batch)} key(s) ({e})", file=sys.stderr)
                found = []
            for issue in found:
                key = str(issue.get("key") or "").strip()
                summary = str((issue.get("fields") or {}).get("summary") or "").strip()
                if not key or not summary:
                    continue
                out[key] = summary
        return out

    def _fetch_epic_children_bulk(self, epic_keys, include_progress=False, team_field=CONFIG_EPIC_TEAM_FIELD):
        """Fetch children for many epics using batched JQL, with per-epic fallback."""
        keys = [str(k).strip() for k in (epic_keys or []) if str(k or "").strip()]
        out = {k: [] for k in keys}
        if not keys:
            return out
        epic_set = set(keys)
        epic_link_field = self._detect_epic_link_field()
        extra = ["parent"]
        if team_field:
            extra.append(team_field)
        if epic_link_field:
            extra.append(epic_link_field)
        fields = self._demand_fields(extra=extra, include_sprint=include_progress)
        fields_no_sprint = self._demand_fields(extra=extra, include_sprint=False)
        batch_size = max(5, int(CONFIG_BULK_EPIC_BATCH or 40))
        total_found = 0
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            key_list = ",".join(batch)
            jqls = [f"parent in ({key_list})"]
            if epic_link_field:
                jqls.append(f'"Epic Link" in ({key_list})')
            seen = set()
            for jql in jqls:
                try:
                    found = self._search_issues(jql, fields)
                except Exception as e1:
                    try:
                        found = self._search_issues(jql, fields_no_sprint)
                        print(f"[children] sprint field unavailable for JQL [{jql}]; continued without movement ({e1})", file=sys.stderr)
                    except Exception as e2:
                        print(f"[children] bulk lookup skipped for JQL [{jql}] ({e2})", file=sys.stderr)
                        found = []
                for issue in found:
                    ikey = issue.get("key")
                    if not ikey or ikey in seen:
                        continue
                    ref = self._issue_epic_ref_key(issue.get("fields", {}) or {}, epic_link_field)
                    if ref not in epic_set:
                        continue
                    out.setdefault(ref, []).append(issue)
                    seen.add(ikey)
                    total_found += 1
            print(f"[children] chunk {i // batch_size + 1}: {total_found} child ticket(s) mapped so far")
        if total_found == 0:
            print(f"[children] bulk lookup found no children; falling back to per-epic lookup for {len(keys)} epic(s)")
            for k in keys:
                try:
                    out[k] = self._search_issues(f'"Epic Link" = {k}', fields) + self._search_issues(f"parent = {k}", fields)
                except Exception as e:
                    print(f"[children] per-epic lookup failed for {k} ({e})", file=sys.stderr)
        return out

    def fetch_board_tickets(self, include_progress=True, team_field=CONFIG_EPIC_TEAM_FIELD):
        """Fetch every non-Epic issue currently returned by the configured Jira board."""
        epic_link_field = self._detect_epic_link_field()
        extra = ["parent", "assignee"]
        if epic_link_field:
            extra.append(epic_link_field)
        if team_field:
            extra.append(team_field)
        fields = self._demand_fields(extra=extra, include_sprint=include_progress)
        out, start = [], 0
        while True:
            print(f"[kanban] reading board tickets startAt={start}", flush=True)
            data = self._get(f"/rest/agile/1.0/board/{self.board_id}/issue",
                             jql="issuetype != Epic", fields=fields,
                             startAt=start, maxResults=100)
            issues = data.get("issues", []) or []
            for issue in issues:
                f = issue.get("fields", {}) or {}
                issue_type = (f.get("issuetype") or {}).get("name", "")
                if str(issue_type).strip().lower() == "epic":
                    continue
                status = f.get("status") or {}
                assignee = f.get("assignee") or {}
                sp = self._sp_total_value(f)
                epic_key = self._issue_epic_ref_key(f, epic_link_field)
                out.append({
                    "key": issue.get("key", ""),
                    "epicKey": epic_key,
                    "team": _norm_team_label(_ppi_value(f.get(team_field)) if team_field else ""),
                    "status": status.get("name", ""),
                    "statusId": str(status.get("id") or ""),
                    "assignee": str(assignee.get("displayName") or assignee.get("name") or ""),
                    "sp": round(float(sp or 0), 2),
                    "discipline": self._discipline(f),
                    "issueType": issue_type,
                    "sprints": self._issue_sprint_codes(f) if include_progress else [],
                    "summary": f.get("summary", ""),
                })
            print(f"[kanban] board tickets page: {len(issues)} issue(s); accumulated {len(out)}/{data.get('total', '?')}", flush=True)
            if not issues or start + data.get("maxResults", 100) >= data.get("total", len(out)):
                break
            start += data.get("maxResults", 100)
        print(f"[kanban] loaded {len(out)} non-Epic board ticket(s)", flush=True)
        return out

    def _issue_changelog(self, issue_key):
        """Read Jira Server/Data Center changelog via issue expand=changelog.

        This Jira instance returns 404 for the Jira Cloud-style
        /issue/{key}/changelog endpoint. The issue endpoint with
        expand=changelog is supported and returns changelog.histories.
        """
        data = self._get(f"/rest/api/2/issue/{issue_key}", expand="changelog", fields="created")
        changelog = data.get("changelog") or {}
        histories = list(changelog.get("histories") or changelog.get("values") or [])
        total = int(changelog.get("total", len(histories)) or len(histories))
        if total > len(histories):
            print(f"[commitment] warning: {issue_key} exposes {len(histories)}/{total} changelog entries via expand=changelog", file=sys.stderr)
        return histories

    @staticmethod
    def _history_number(value):
        import re
        text = str(value or "").strip()
        m = re.search(r"-?\d+(?:[\.,]\d+)?", text)
        return float(m.group(0).replace(",", ".")) if m else 0.0

    @staticmethod
    def _history_sprints(value):
        import re
        text = str(value or "")
        found = []
        for match in re.finditer(r"(?:\bPI\s*)?(\d{2}\.\d+\.\d+)\b", text, flags=re.I):
            code = match.group(1)
            if code not in found:
                found.append(code)
        return found

    def commitment_snapshot(self, epics, cutoff_date, team_field=CONFIG_EPIC_TEAM_FIELD):
        """Reconstruct child-ticket SP, Team, status and sprint values at a cutoff date."""
        if not cutoff_date:
            return {"date": "", "tickets": [], "error": "No commitment date configured"}
        try:
            cutoff = dt.datetime.combine(dt.date.fromisoformat(cutoff_date), dt.time.max)
        except ValueError:
            return {"date": cutoff_date, "tickets": [], "error": "Invalid commitment date; use YYYY-MM-DD"}

        records, failures = [], []
        all_tickets = [(e, t) for e in (epics or []) for t in (e.get("tickets") or [])]
        print(f"[commitment] reconstructing {len(all_tickets)} ticket(s) at {cutoff_date}", flush=True)
        for idx, (epic, ticket) in enumerate(all_tickets, 1):
            key = str(ticket.get("key") or "")
            current = {"sp": float(ticket.get("sp") or 0), "team": ticket.get("team") or "No team",
                       "status": ticket.get("status") or "", "sprints": list(ticket.get("sprints") or [])}
            try:
                issue = self._get(f"/rest/api/2/issue/{key}",
                                  fields=f"created,{self.sp_field},customfield_15220,customfield_17121,{team_field},{CONFIG_TICKET_SPRINT_FIELD},status")
                fields = issue.get("fields") or {}
                created_txt = str(fields.get("created") or "")
                created = dt.datetime.fromisoformat(created_txt.replace("Z", "+00:00")).replace(tzinfo=None) if created_txt else None
                if created and created > cutoff:
                    continue
                histories = self._issue_changelog(key)
                state = dict(current)
                for history in sorted(histories, key=lambda h: str(h.get("created") or ""), reverse=True):
                    changed_txt = str(history.get("created") or "")
                    try:
                        changed = dt.datetime.fromisoformat(changed_txt.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        continue
                    if changed <= cutoff:
                        continue
                    for item in (history.get("items") or []):
                        fid = str(item.get("fieldId") or "")
                        fname = str(item.get("field") or "").strip().lower()
                        old = item.get("fromString")
                        if fid in {self.sp_field, "customfield_15220", "customfield_17121"} or "story point" in fname or "epic sp sum" in fname:
                            if fid == "customfield_15220" and "/" in str(old or ""):
                                nums = __import__("re").findall(r"-?\d+(?:[\.,]\d+)?", str(old))
                                state["sp"] = float(nums[1].replace(",", ".")) if len(nums) > 1 else 0.0
                                continue
                            state["sp"] = self._history_number(old)
                            continue
                        if fid == team_field or fname == "team":
                            state["team"] = str(old or "").strip() or "No team"
                            continue
                        if fid == CONFIG_TICKET_SPRINT_FIELD or fname == "sprint":
                            state["sprints"] = self._history_sprints(old)
                            continue
                        if fname != "status":
                            continue
                        state["status"] = str(old or "")
                records.append({
                    "key": key, "epicKey": epic.get("key") or "", "team": state["team"],
                    "product": _portfolio_product(epic), "parentLink": epic.get("parentLink") or "No parent link",
                    "sp": round(float(state["sp"] or 0), 2), "status": state["status"],
                    "sprints": state["sprints"], "summary": ticket.get("summary") or "",
                })
            except Exception as exc:
                failures.append(key)
                print(f"[commitment] {key} skipped ({exc})", file=sys.stderr)
            if idx % 25 == 0:
                print(f"[commitment] {idx}/{len(all_tickets)} ticket(s)", flush=True)
        print(f"[commitment] captured {len(records)} ticket(s); {len(failures)} failed", flush=True)
        return {"date": cutoff_date, "tickets": records, "failedKeys": failures}

    def fetch_portfolio(self, ppi_field, target_pi, team_field=CONFIG_EPIC_TEAM_FIELD,
                        priority_field=CONFIG_EPIC_PRIORITY_FIELD, include_progress=True):
        """Read ALL Epics on the Kanban board matching the target PI, for every team.

        Returns a list of epic dicts:
          key, summary, status, closed, team, ppi, priority, discipline, committed,
          parentLink, parentLinkName, sp (remaining/display), totalSp, doneSp,
          tickets: [key, summary, status, closed, sp, doneSp, discipline, sprints]
        """
        committed_field = self._detect_committed_field()
        extra_fields = [ppi_field, CONFIG_EPIC_PARENT_LINK_FIELD]
        if team_field:
            extra_fields.append(team_field)
        if committed_field:
            extra_fields.append(committed_field)
        extra_fields_with_priority = list(extra_fields)
        if priority_field:
            extra_fields_with_priority.append(priority_field)
        cols = self._demand_fields(extra_fields_with_priority)
        cols_no_priority = self._demand_fields(extra_fields)
        epics, start = [], 0
        priority_field_enabled = bool(priority_field)
        while True:
            try:
                d = self._get(f"/rest/agile/1.0/board/{self.board_id}/issue",
                              jql="issuetype = Epic", fields=cols, startAt=start, maxResults=100)
            except Exception as e1:
                if priority_field_enabled:
                    priority_field_enabled = False
                    cols = cols_no_priority
                    print(f"[portfolio] priority field '{priority_field}' could not be read from the board; continuing without priority ({e1})", file=sys.stderr)
                    try:
                        d = self._get(f"/rest/agile/1.0/board/{self.board_id}/issue",
                                      jql="issuetype = Epic", fields=cols, startAt=start, maxResults=100)
                    except Exception:
                        d = self._get(f"/rest/agile/1.0/board/{self.board_id}/issue",
                                      fields=cols, startAt=start, maxResults=100)
                        d["issues"] = [i for i in d.get("issues", [])
                                       if ((i.get("fields", {}) or {}).get("issuetype") or {}).get("name", "").lower() == "epic"] or d.get("issues", [])
                else:
                    d = self._get(f"/rest/agile/1.0/board/{self.board_id}/issue",
                                  fields=cols, startAt=start, maxResults=100)
                    d["issues"] = [i for i in d.get("issues", [])
                                   if ((i.get("fields", {}) or {}).get("issuetype") or {}).get("name", "").lower() == "epic"] or d.get("issues", [])
            got = d.get("issues", [])
            epics += got
            if not got or start + d.get("maxResults", 100) >= d.get("total", len(epics)):
                break
            start += 100
        if not priority_field_enabled:
            priority_field = None
        print(f"[portfolio] board returned {len(epics)} epic issue(s) total")

        tgt = _norm_pi(target_pi)
        candidates = []
        for ep in epics:
            fl = ep.get("fields", {}) or {}
            if (fl.get("issuetype") or {}).get("name", "").lower() not in ("", "epic"):
                continue
            ppi = _ppi_value(fl.get(ppi_field))
            npi = _norm_pi(ppi)
            if tgt and not (tgt == npi or tgt in npi):
                continue
            team = _norm_team_label(_ppi_value(fl.get(team_field)) if team_field else "")
            candidates.append((ep, fl, ppi, team))
        teams_found = sorted({t for _e, _f, _p, t in candidates})
        print(f"[portfolio] {len(candidates)} epic(s) match PI {target_pi} across {len(teams_found)} team(s): {', '.join(teams_found) or '-'}")

        # Resolve Parent Link display names in bulk rather than one call per epic.
        parent_name_lookup = {}
        parent_keys = []
        for _ep, fl, _ppi, _team in candidates:
            pk, pn = _parent_link_info(fl.get(CONFIG_EPIC_PARENT_LINK_FIELD))
            if not pk or (pn and pn != pk):
                continue
            parent_keys.append(pk)
        if parent_keys:
            print(f"[portfolio] resolving {len(set(parent_keys))} parent link name(s) in bulk")
            parent_name_lookup = self._fetch_parent_link_names_bulk(parent_keys)

        child_cache = {}
        if candidates:
            epic_keys = [ep.get("key") for ep, _fl, _ppi, _team in candidates if ep.get("key")]
            print(f"[portfolio] bulk fetching child tickets for {len(epic_keys)} epic(s) in chunks of {CONFIG_BULK_EPIC_BATCH}")
            child_cache = self._fetch_epic_children_bulk(epic_keys, include_progress=include_progress, team_field=team_field)

        detail = []
        for ep, fl, ppi, team in candidates:
            epic_sp, epic_sp_src = self._demand_sp_value(fl)
            epic_total_sp = self._sp_total_value(fl)
            epic_done_sp, epic_done_src = self._demand_done_sp_value(fl)
            epic_priority = self._epic_priority_value(fl, priority_field)
            epic_disc = self._discipline(fl)
            epic_committed = self._committed_value(fl, committed_field)
            status = (fl.get("status") or {}).get("name", "")
            epic_closed = self._issue_is_closed(fl)
            # Only trust an explicit done/total field as "done SP" on an open epic.
            if not epic_closed and epic_done_src != "customfield_15220_done":
                epic_done_sp = 0.0
            parent_link, parent_link_name = _parent_link_info(fl.get(CONFIG_EPIC_PARENT_LINK_FIELD))
            if parent_link and (not parent_link_name or parent_link_name == parent_link):
                parent_link_name = parent_name_lookup.get(parent_link, parent_link_name)

            tickets = []
            child_total = 0.0
            child_done = 0.0
            for ch in child_cache.get(ep.get("key"), []):
                cf = ch.get("fields", {}) or {}
                csp = self._sp_total_value(cf)
                cdonesp, cdone_src = self._demand_done_sp_value(cf)
                cclosed = self._issue_is_closed(cf)
                if not cclosed and cdone_src != "customfield_15220_done":
                    cdonesp = 0.0
                sprint_codes = self._issue_sprint_codes(cf) if include_progress else []
                child_total += float(csp or 0)
                if cclosed:
                    child_done += float(cdonesp or csp or 0)
                elif cdonesp and cdonesp > 0:
                    # Partial progress on an open ticket never exceeds its own total.
                    child_done += min(float(cdonesp), float(csp or cdonesp))
                status_obj = cf.get("status") or {}
                assignee_obj = cf.get("assignee") or {}
                ticket_team = _norm_team_label(_ppi_value(cf.get(team_field)) if team_field else "")
                tickets.append({
                    "key": ch.get("key"), "epicKey": ep.get("key"),
                    "plannedForPi": True,
                    "team": ticket_team,
                    "sp": round(float(csp or 0), 2),
                    "doneSp": round(float(cdonesp or 0), 2),
                    "discipline": self._discipline(cf),
                    "status": status_obj.get("name", ""),
                    "statusId": str(status_obj.get("id") or ""),
                    "assignee": str(assignee_obj.get("displayName") or assignee_obj.get("name") or ""),
                    "issueType": (cf.get("issuetype") or {}).get("name", ""),
                    "sprints": sprint_codes, "closed": cclosed,
                    "summary": cf.get("summary", ""),
                })

            # Child totals win over the epic's own rollup when children are known.
            total_sp = float(epic_total_sp or epic_sp or 0)
            done_sp = float(child_done if child_total > 0 else (epic_done_sp or 0))
            if epic_closed:
                done_sp = max(done_sp, total_sp)
            done_sp = min(done_sp, total_sp) if total_sp > 0 else done_sp

            detail.append({
                "key": ep.get("key"),
                "summary": fl.get("summary", ""),
                "status": status,
                "closed": epic_closed,
                "team": team,
                "ppi": ppi,
                "priority": epic_priority,
                "discipline": epic_disc,
                "committed": epic_committed,
                "parentLink": parent_link,
                "parentLinkName": parent_link_name,
                "sp": round(float(epic_sp or 0), 2),
                "totalSp": round(total_sp, 2),
                "doneSp": round(done_sp, 2),
                "spSource": epic_sp_src,
                "ticketCount": len(tickets),
                "tickets": tickets,
            })
        return detail
