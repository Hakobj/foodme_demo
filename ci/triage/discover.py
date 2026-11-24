"""Step 1 of the daily triage: find the GlitchTip issues that are new since the last run.

New = unresolved, in one of the projects backend / web / admin, first seen within the look-back
window (default 26 h, so a late daily run doesn't miss anything), not deliberate noise, and not yet
in Jira (an issue labelled `glitchtip-<id>`). Jira is the memory between runs: no state file.

For each new issue it writes a run dir `agentic-workflows/triage/runs/GT-<SHORT-ID>/` with
`problem.yaml` (the problem as GlitchTip reports it), `gates.yaml` (the problem gate, auto-approved
in CI) and `artifacts/00-glitchtip-issue.json`, plus a GitHub Actions matrix.

    python -m ci.triage.discover --matrix-file matrix.json [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ci.triage.clients import GlitchTip, Jira, project_slug
from ci.triage.config import IGNORE_CULPRITS, IGNORE_TITLES, PROJECTS, RUNS_DIR, SUT, Settings, jira_label, run_key
from ci.triage.yamlish import dump_yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_noise(issue: dict[str, Any]) -> bool:
    title, culprit = str(issue.get("title", "")), str(issue.get("culprit", ""))
    meta = issue.get("metadata") or {}
    text = f"{title} {meta.get('filename', '')} {meta.get('function', '')}"
    return any(p.search(text) for p in IGNORE_TITLES) or any(p.search(culprit) for p in IGNORE_CULPRITS)


def new_issues(issues: list[dict[str, Any]], since: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(candidates, skipped-as-noise) among the issues of our projects first seen after `since`."""
    fresh: list[dict[str, Any]] = []
    noise: list[dict[str, Any]] = []
    for issue in issues:
        if project_slug(issue) not in PROJECTS:
            continue
        first_seen = issue.get("firstSeen")
        if not first_seen or parse_time(first_seen) < since:
            continue
        (noise if is_noise(issue) else fresh).append(issue)
    return fresh, noise


def event_digest(event: dict[str, Any]) -> dict[str, Any]:
    """The parts of the latest event a triage needs. Headers, cookies, user and body are left out."""
    entries = {e.get("type"): e.get("data", {}) for e in event.get("entries", []) if isinstance(e, dict)}
    request = entries.get("request") or event.get("request") or {}
    frames: list[dict[str, Any]] = []
    for value in (entries.get("exception") or {}).get("values", []) or []:
        for frame in reversed((value.get("stacktrace") or {}).get("frames", []) or []):
            if frame.get("inApp") or frame.get("in_app"):
                frames.append(
                    {k: frame.get(k) for k in ("filename", "function", "lineNo", "lineno", "module") if frame.get(k)}
                )
    tags = {t.get("key"): t.get("value") for t in event.get("tags", []) if isinstance(t, dict)}
    return {
        "event_id": event.get("eventID") or event.get("id"),
        "date": event.get("dateCreated") or event.get("dateReceived"),
        "message": event.get("message") or event.get("title"),
        "request": {"method": request.get("method"), "url": request.get("url")},
        "in_app_frames": frames[:8],
        "tags": {k: v for k, v in tags.items() if k in ("release", "environment", "browser", "os", "url", "level")},
    }


def problem_for(issue: dict[str, Any], event: dict[str, Any], key: str) -> dict[str, Any]:
    slug = project_slug(issue)
    request = event.get("request") or {}
    where = " ".join(x for x in (request.get("method"), request.get("url")) if x) or issue.get("culprit") or ""
    return {
        "ticket": key,
        "mode": "ci",
        "sut": SUT,
        "summary": f"{PROJECTS[slug]} error in GlitchTip {issue.get('shortId')}: {issue.get('title')}",
        "expected": "The flow completes without an unhandled error being reported to GlitchTip.",
        "observed": f"{issue.get('title')} (culprit: {issue.get('culprit') or 'n/a'}, "
        f"{issue.get('count')} event(s), first seen {issue.get('firstSeen')}, last seen {issue.get('lastSeen')})",
        "steps": [f"Trigger: {where}"] if where else [],
        "environment": {
            "user": "unknown (GlitchTip)",
            "browser": (event.get("tags") or {}).get("browser", ""),
            "data": "",
            "release": (event.get("tags") or {}).get("release", ""),
        },
        "first_seen": issue.get("firstSeen"),
        "source_run": "none",
        "glitchtip": {
            "id": str(issue.get("id")),
            "short_id": issue.get("shortId"),
            "project": slug,
            "area": PROJECTS[slug],
            "level": issue.get("level"),
            "count": issue.get("count"),
            "first_seen": issue.get("firstSeen"),
            "last_seen": issue.get("lastSeen"),
            "culprit": issue.get("culprit"),
            "permalink": issue.get("permalink", ""),
            "latest_event": "artifacts/00-glitchtip-issue.json",
        },
        "open_points": [
            "Which user flow triggers it (GlitchTip only shows the failing request / frame)?",
            "Does it reproduce for a guest on the live SUT, or only with specific data or a signed-in user?",
        ],
    }


def write_run(runs_dir: Path, issue: dict[str, Any], event: dict[str, Any]) -> str:
    key = run_key(str(issue.get("shortId") or issue.get("id")))
    run = runs_dir / key
    (run / "artifacts").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    issue_view = {k: issue.get(k) for k in ("id", "shortId", "title", "culprit", "level", "count", "userCount")}
    issue_view |= {
        "project": project_slug(issue),
        "firstSeen": issue.get("firstSeen"),
        "lastSeen": issue.get("lastSeen"),
        "metadata": issue.get("metadata"),
        "permalink": issue.get("permalink"),
    }
    artifact = {"fetched_at": now, "issue": issue_view, "latest_event": event}
    (run / "artifacts" / "00-glitchtip-issue.json").write_text(
        f"// GlitchTip issue {issue.get('id')} + latest event (headers, cookies, user data left out), {now}\n"
        + json.dumps(artifact, indent=1),
        encoding="utf-8",
    )
    (run / "problem.yaml").write_text(dump_yaml(problem_for(issue, event, key)), encoding="utf-8")
    gates = {
        "problem": {
            "approved": True,
            "by": "ci-daily-triage",
            "at": now,
            "note": "CI mode: the problem is the GlitchTip issue as reported; no human confirmation.",
        }
    }
    (run / "gates.yaml").write_text(dump_yaml(gates), encoding="utf-8")
    status = f"Triage {key} │ ✅01 ⏳02 ⏳03 ⏳04 ⏳05 ⏳06 │ queued by daily CI\n"
    (run / "status").write_text(status, encoding="utf-8")
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs-dir", type=Path, default=REPO_ROOT / RUNS_DIR)
    parser.add_argument("--matrix-file", type=Path, default=Path("matrix.json"))
    parser.add_argument("--summary-file", type=Path, default=Path("discover.json"))
    parser.add_argument("--dry-run", action="store_true", help="list what would be triaged, write nothing")
    args = parser.parse_args(argv)
    settings = Settings()
    required = {
        "GLITCHTIP_TOKEN": settings.glitchtip_token,
        "JIRA_API_TOKEN": settings.jira_token,
        "JIRA_EMAIL": settings.jira_email,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print(f"::error::missing secrets: {', '.join(missing)}")
        return 1

    jira = Jira(settings)
    print(f"Jira login OK as {jira.check_login()}")  # fail early: without Jira there is no de-duplication
    since = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    glitchtip = GlitchTip(settings)
    issues = glitchtip.unresolved_issues()
    fresh, noise = new_issues(issues, since)
    known = jira.existing_labels([jira_label(str(i["id"])) for i in fresh])
    todo = [i for i in fresh if jira_label(str(i["id"])) not in known]
    todo.sort(key=lambda i: int(i.get("count") or 0), reverse=True)  # most frequent first

    matrix: list[dict[str, Any]] = []
    for index, issue in enumerate(todo):
        triage = index < settings.max_issues  # the rest still gets a Jira issue, without triage
        key = run_key(str(issue.get("shortId") or issue.get("id")))
        if not args.dry_run:
            event = event_digest(glitchtip.latest_event(str(issue["id"])))
            key = write_run(args.runs_dir, issue, event)
        matrix.append(
            {
                "key": key,
                "issue_id": str(issue["id"]),
                "project": project_slug(issue),
                "title": str(issue.get("title", ""))[:120],
                "triage": triage,
            }
        )

    summary = {
        "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unresolved_seen": len(issues),
        "new": len(fresh),
        "noise_skipped": [f"{i.get('shortId')}: {i.get('title')}" for i in noise],
        "already_in_jira": known,
        "queued": matrix,
        "max_issues": settings.max_issues,
    }
    args.summary_file.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    args.matrix_file.write_text(json.dumps(matrix), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"matrix={json.dumps(matrix)}\ncount={len(matrix)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
