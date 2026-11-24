"""Step 3 of the daily triage: open the Jira issue and report to Telegram.

    python -m ci.triage.report issue  --run-dir agentic-workflows/triage/runs/GT-BACKEND-7 [--dry-run]
    python -m ci.triage.report digest --discover discover.json --reports-dir reports/ [--dry-run]

`issue` reads the run dir: `ci-result.json` (written by the agent in CI mode, see
.claude/skills/triage-pipeline/SKILL.md "CI mode") and `artifacts/00-glitchtip-issue.json`. Without a
usable ci-result.json (agent failed, timed out or the issue was over the daily limit) it still opens
the Jira issue from the GlitchTip data, marked `triage-incomplete`. It writes `ci-report.json`.

`digest` sends ONE Telegram message for the whole run: every new issue, its Jira link and the top
root-cause candidate, plus what was skipped.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ci.triage.clients import Jira, Telegram
from ci.triage.config import PROJECTS, Settings, jira_label

RATINGS = {"confirmed": "✅", "likely": "🟢", "possible": "🟡", "unlikely": "🟠", "ruled_out": "❌"}
LAYERS = {"backend", "web", "admin", "data", "infra", "test"}


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if text.startswith("//"):  # artifacts carry a one-line header comment
        text = text.split("\n", 1)[1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def validate_result(result: dict[str, Any] | None) -> list[str]:
    """Problems that make the agent's ci-result.json unusable (empty list = usable)."""
    if result is None:
        return ["ci-result.json is missing or not valid JSON"]
    problems = []
    jira = result.get("jira")
    if not isinstance(jira, dict) or not jira.get("summary") or not jira.get("description_md"):
        problems.append("jira.summary / jira.description_md missing")
    top = result.get("top")
    if top is not None and (not isinstance(top, dict) or top.get("rating") not in RATINGS):
        problems.append("top.rating must be one of " + ", ".join(RATINGS))
    return problems


def build_issue(run_dir: Path, settings: Settings) -> dict[str, Any]:
    """The Jira fields for one run (no network)."""
    gt = load_json(run_dir / "artifacts" / "00-glitchtip-issue.json") or {}
    issue, event = gt.get("issue") or {}, gt.get("latest_event") or {}
    area = PROJECTS.get(str(issue.get("project")), "?")
    result = load_json(run_dir / "ci-result.json")
    problems = validate_result(result)
    labels = ["bug", "foodme", "auto-triage", "needs-review", jira_label(str(issue.get("id"))), f"area-{area.lower()}"]
    footer = [
        "",
        "## Source",
        f"- **GlitchTip:** {issue.get('shortId')} ({issue.get('project')}) {issue.get('permalink') or ''}".rstrip(),
        f"- **Events:** {issue.get('count')} · first seen {issue.get('firstSeen')} · last seen {issue.get('lastSeen')}",
        f"- **Triage run:** `agentic-workflows/triage/runs/{run_dir.name}/`"
        + (f" (CI artifact `triage-{run_dir.name}` of {settings.run_url})" if settings.run_url else ""),
        "",
        "_Opened automatically by the daily triage workflow. Review the analysis before acting on it._",
    ]
    if not problems:
        assert result is not None
        jira = result["jira"]
        top = result.get("top") or {}
        summary = str(jira["summary"]).strip()
        if not summary.startswith("[Bug]"):
            summary = f"[Bug] {summary}"
        layer = str(top.get("layer", ""))
        if top.get("rating") in ("confirmed", "likely") and layer in LAYERS:
            labels.append(f"rc-{layer}")
        labels.append("triaged")
        labels += [str(x) for x in jira.get("labels", []) if isinstance(x, str) and x.replace("-", "").isalnum()]
        priority = jira.get("priority") if jira.get("priority") in ("High", "Medium", "Low") else "Medium"
        description = str(jira["description_md"]).rstrip() + "\n" + "\n".join(footer)
        triaged = True
    else:
        title = issue.get("title") or "GlitchTip issue"
        summary = f"[Bug] {area}: {title}"
        labels.append("triage-incomplete")
        priority = "Medium"
        request = event.get("request") or {}
        frames = event.get("in_app_frames") or []
        description = "\n".join(
            [
                "## Automated triage did not complete",
                *[f"- {p}" for p in problems],
                *(f"- {o}" for o in (result or {}).get("obstacles", []) if isinstance(o, str)),
                "",
                "## What GlitchTip reports",
                f"- **Error:** {title}",
                f"- **Culprit:** {issue.get('culprit') or 'n/a'}",
                f"- **Request:** {request.get('method') or ''} {request.get('url') or 'n/a'}".rstrip(),
                *[
                    f"- **Frame:** `{f.get('filename')}` {f.get('function')} line {f.get('lineNo') or f.get('lineno')}"
                    for f in frames[:5]
                ],  # fmt: skip
                *footer,
            ]
        )
        triaged = False
    return {
        "summary": summary[:250],
        "description_md": description,
        "labels": sorted(set(labels)),
        "priority": priority,
        "triaged": triaged,
        "problems": problems,
        "label_key": jira_label(str(issue.get("id"))),
        "glitchtip": {k: issue.get(k) for k in ("id", "shortId", "project", "title", "count")},
        "top": (result or {}).get("top") if not problems else None,
        "reproduced": (result or {}).get("reproduced") if not problems else None,
        "telegram": (result or {}).get("telegram") if not problems else None,
    }


def cmd_issue(args: argparse.Namespace, settings: Settings) -> int:
    fields = build_issue(args.run_dir, settings)
    report: dict[str, Any] = {"run": args.run_dir.name, **fields, "jira_key": None, "jira_url": None}
    if args.dry_run:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        jira = Jira(settings)
        existing = jira.existing_labels([fields["label_key"]])  # a re-run must not file a duplicate
        if existing:
            key = existing[fields["label_key"]]
            report["note"] = "already in Jira, not created again"
        else:
            key = jira.create_issue(fields["summary"], fields["description_md"], fields["labels"], fields["priority"])
        report.update({"jira_key": key, "jira_url": jira.browse_url(key)})
        print(f"Jira: {key} {jira.browse_url(key)} ({'triaged' if fields['triaged'] else 'triage incomplete'})")
    report["at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (args.run_dir / "ci-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


def digest_text(discover: dict[str, Any], reports: list[dict[str, Any]], run_url: str) -> str:
    esc = html.escape
    by_key = {r["run"]: r for r in reports}
    queued = discover.get("queued", [])
    lines = [f"<b>🩺 FoodMe daily triage</b> · new GlitchTip issues since {esc(discover.get('since', '?'))}"]
    if not queued:
        lines.append("No new issues in BE / FE / ADM. 🎉")
    for item in queued:
        report = by_key.get(item["key"], {})
        area = PROJECTS.get(item["project"], "?")
        jira = (
            f'<a href="{esc(report["jira_url"])}">{esc(report["jira_key"])}</a>'
            if report.get("jira_url")
            else "Jira: not created"
        )
        lines.append(f"\n<b>{esc(area)}</b> {esc(item['key'])} — {esc(item['title'])}\n{jira}")
        top = report.get("top")
        if top:
            mark = RATINGS.get(top.get("rating", ""), "")
            lines.append(
                f"{mark} {esc(str(top.get('title', '')))} ({esc(str(top.get('rating')))}, "
                f"{esc(str(top.get('confidence', '?')))}%, layer {esc(str(top.get('layer', '?')))})"
            )
            if report.get("telegram"):
                lines.append(esc(str(report["telegram"]))[:500])
        elif not item.get("triage"):
            lines.append("⏭️ over the daily triage limit: filed without analysis")
        else:
            lines.append("⚠️ triage incomplete: filed with the GlitchTip data only")
    skipped = discover.get("noise_skipped") or []
    known = discover.get("already_in_jira") or {}
    if skipped or known:
        lines.append(f"\nSkipped: {len(skipped)} known-noise, {len(known)} already in Jira.")
    if run_url:
        lines.append(f'<a href="{esc(run_url)}">Workflow run and triage artifacts</a>')
    return "\n".join(lines)


def cmd_digest(args: argparse.Namespace, settings: Settings) -> int:
    discover = load_json(args.discover) or {}
    reports = [r for p in sorted(args.reports_dir.rglob("ci-report.json")) if (r := load_json(p))]
    text = digest_text(discover, reports, settings.run_url)
    if args.summary:
        args.summary.write_text(text.replace("<b>", "**").replace("</b>", "**") + "\n", encoding="utf-8")
    telegram = Telegram(settings)
    if args.dry_run or not telegram.configured:
        print(("(not sent: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set)\n" if not args.dry_run else "") + text)
        return 0
    if not discover.get("queued") and not args.notify_empty:
        print("no new issues; nothing sent")
        return 0
    telegram.send(text)
    print("Telegram digest sent")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_issue = sub.add_parser("issue")
    p_issue.add_argument("--run-dir", type=Path, required=True)
    p_issue.add_argument("--dry-run", action="store_true")
    p_digest = sub.add_parser("digest")
    p_digest.add_argument("--discover", type=Path, required=True)
    p_digest.add_argument("--reports-dir", type=Path, required=True)
    p_digest.add_argument("--summary", type=Path, help="also write the digest as markdown (job summary)")
    p_digest.add_argument("--notify-empty", action="store_true", help="send a message when nothing is new")
    p_digest.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    settings = Settings()
    return cmd_issue(args, settings) if args.command == "issue" else cmd_digest(args, settings)


if __name__ == "__main__":
    sys.exit(main())
