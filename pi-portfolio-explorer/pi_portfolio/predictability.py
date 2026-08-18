"""Sprint predictability: final commitment vs completed work per team and sprint.

Reads the Greenhopper sprint report for every configured dashboard board and
every closed sprint of the target PI.
"""
import re
import sys

from .fields import _norm_pi

# Scrum boards used for the Predictability tab, in display order.
PREDICTABILITY_BOARDS = {
    14807: "Team Barcelona",
    16657: "Team DaVinci",
    16652: "Team ELMO's",
    16654: "Team The GOATs",
    29711: "Team Resolvers",
}

# (boardId, sprintId) -> final commitment, for sprints where the Jira report
# does not reflect the commitment the team actually agreed on.
PREDICTABILITY_FINAL_OVERRIDES = {
    (29711, 55061): 36.0,
}


def _predictability_estimate(contents, key):
    value = (contents or {}).get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _predictability_closed_sprints(jc, board_id):
    """Load all closed sprints, even when Jira omits total/isLast."""
    values, start_at, page_size = [], 0, 50
    seen_ids = set()
    while True:
        page = jc._get(f"/rest/agile/1.0/board/{board_id}/sprint",
                       state="closed", startAt=start_at, maxResults=page_size) or {}
        batch = list(page.get("values") or [])
        new_rows = []
        for sprint in batch:
            sprint_id = sprint.get("id")
            if sprint_id in seen_ids:
                continue
            seen_ids.add(sprint_id)
            new_rows.append(sprint)
        values.extend(new_rows)
        # Some Jira versions omit isLast/total on this endpoint, so stop as soon
        # as a short page or a page without new sprints comes back.
        if page.get("isLast") is True or not batch or len(batch) < page_size:
            break
        start_at += len(batch)
        if not new_rows:
            break
    return values


def fetch_sprint_predictability(jc, pi_name, num_sprints):
    """Read every configured dashboard team and every closed sprint in the PI."""
    pi_code = _norm_pi(pi_name)
    if not pi_code:
        return {"piName": str(pi_name or ""), "rows": [], "failures": [
            {"team": "All teams", "error": "No PI configured"},
        ]}

    sprint_re = re.compile(rf"(?<!\d){re.escape(pi_code)}[.](\d+)(?!\d)", re.I)
    failures, rows = [], []

    for board_id, team in PREDICTABILITY_BOARDS.items():
        try:
            closed_sprints = _predictability_closed_sprints(jc, board_id)
            print(f"[predictability] {team}: {len(closed_sprints)} closed sprint(s)")
            # Jira can hold several closed sprints with the same PI number
            # (re-opened, split). Keep the one that closed last.
            by_number = {}
            for sprint in closed_sprints:
                name = str(sprint.get("name") or "")
                match = sprint_re.search(name)
                if not match:
                    continue
                number = int(match.group(1))
                if not (1 <= number <= int(num_sprints)):
                    continue
                previous = by_number.get(number)
                current_date = str(sprint.get("completeDate") or sprint.get("endDate") or "")
                previous_date = str((previous or {}).get("completeDate") or (previous or {}).get("endDate") or "")
                if previous is None or current_date > previous_date:
                    by_number[number] = sprint

            if not by_number:
                failures.append({
                    "team": team, "boardId": board_id,
                    "error": f"No closed sprint matching {pi_code}.1-{num_sprints}",
                })
                print(f"[predictability] {team}: no matching PI sprint", file=sys.stderr)
                continue

            for number in sorted(by_number):
                sprint = by_number[number]
                sprint_id = int(sprint["id"])
                report = jc._get(
                    "/rest/greenhopper/1.0/rapid/charts/sprintreport",
                    rapidViewId=board_id,
                    sprintId=sprint_id,
                ) or {}
                contents = report.get("contents") or report
                completed = _predictability_estimate(contents, "completedIssuesEstimateSum")
                unfinished = _predictability_estimate(contents, "issuesNotCompletedEstimateSum")
                final = PREDICTABILITY_FINAL_OVERRIDES.get(
                    (board_id, sprint_id), completed + unfinished,
                )
                row = {
                    "team": team,
                    "boardId": board_id,
                    "sprint": f"{pi_code}.{number}",
                    "sprintNumber": number,
                    "sprintId": sprint_id,
                    "finalCommitment": round(final, 2),
                    "completedWork": round(completed, 2),
                    "predictability": (completed / final) if final else None,
                    "closedDate": sprint.get("completeDate") or sprint.get("endDate") or "",
                }
                rows.append(row)
                print(f"[predictability] {team} {row['sprint']}: final={final:.2f}"
                      f" completed={completed:.2f}")
        except Exception as exc:
            failures.append({"team": team, "boardId": board_id, "error": str(exc)})
            print(f"[predictability] {team} failed ({exc})", file=sys.stderr)

    team_order = {team: index for index, team in enumerate(PREDICTABILITY_BOARDS.values())}
    rows.sort(key=lambda row: (row["sprintNumber"], team_order.get(row["team"], 999)))
    print(f"[predictability] loaded {len({row['team'] for row in rows})}/5 teams and {len(rows)} row(s)")
    return {
        "piName": pi_code,
        "rows": rows,
        "failures": failures,
        "calculation": "Completed work / Final commitment",
    }
