"""CLI: python -m selection {select,evaluate,audit,history,explain}."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from selection.selector import DEFAULT_MAP, Selector, changed_files, summary_markdown


def github_output(**values: object) -> None:
    """Step outputs for GitHub Actions (no-op elsewhere)."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.writelines(f"{key}={value}\n" for key, value in values.items())


def count_selected(selector: Selector, data: dict) -> int:
    from selection.selector import Selection

    if data["mode"] == "all":
        return len(selector.tests)
    # prefixes of test files that are new since the map was built count as one test at least
    run = selector.expand(Selection("subset", set(data["selected"]), {}, [], [], data.get("total", 0)))
    return len(run) or len(data["selected"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m selection", description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="impact map (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select", help="select e2e tests for a diff")
    p_select.add_argument("--base", default="origin/main", help="base ref (merge-base with head)")
    p_select.add_argument("--head", default=None, help="head ref (default: the working tree)")
    p_select.add_argument("--files", nargs="*", help="use these changed files instead of git diff")
    p_select.add_argument("--out", type=Path, default=Path("selection.json"))
    p_select.add_argument("--summary", type=Path, help="also write a markdown summary here")

    p_eval = sub.add_parser("evaluate", help="mutation benchmark (one full e2e run per mutation)")
    p_eval.add_argument("--only", nargs="*", help="mutation ids")
    p_eval.add_argument("--baseline", type=Path, help="junit of an unmutated full run (skips that run)")
    p_eval.add_argument("--label", default="", help="write mutation-results-<label>.json (partial re-runs)")

    p_audit = sub.add_parser("audit", help="shadow mode: compare a selection with a full run")
    p_audit.add_argument("--selection", type=Path, required=True)
    p_audit.add_argument("--junit", type=Path, required=True, help="junit xml of the full e2e run")
    p_audit.add_argument("--rerun-junit", type=Path, help="junit of a rerun of the failures (flaky filter)")
    p_audit.add_argument("--summary", type=Path)
    p_audit.add_argument("--fail-on-escape", action="store_true")

    p_hist = sub.add_parser("history", help="replay the selection over past commits")
    p_hist.add_argument("--commits", type=int, default=30)
    p_hist.add_argument("--ref", default="HEAD")

    p_explain = sub.add_parser("explain", help="show a test's recorded footprint")
    p_explain.add_argument("nodeid")

    p_merge = sub.add_parser("merge-additions", help="add reviewer-suggested tests to a selection (never removes)")
    p_merge.add_argument("--selection", type=Path, required=True)
    p_merge.add_argument("--additions", type=Path, required=True, help='[{"test": "<nodeid or file>", "reason": ""}]')
    p_merge.add_argument("--summary", type=Path, help="markdown summary to rewrite")

    args = parser.parse_args(argv)
    selector = Selector.from_file(args.map)

    if args.command == "select":
        if args.files is not None:
            from selection.selector import Change

            changes = [Change(f, "M") for f in args.files]
        else:
            changes = changed_files(args.base, args.head)
        selection = selector.select(changes, args.base, args.head or "WORKTREE")
        args.out.write_text(json.dumps(selection.to_json(), indent=1) + "\n", encoding="utf-8")
        summary = summary_markdown(selector, selection)
        if args.summary:
            args.summary.write_text(summary, encoding="utf-8")
        run = selector.expand(selection)
        print(f"{selection.mode}: {len(run)} of {selection.total} e2e tests -> {args.out}")
        github_output(mode=selection.mode, count=count_selected(selector, selection.to_json()))
        return 0

    if args.command == "evaluate":
        from selection.evaluate import run_mutations

        result = run_mutations(selector, args.only, args.baseline, args.label)
        print(json.dumps(result["totals"], indent=1))
        return 0

    if args.command == "audit":
        from selection.evaluate import audit, audit_markdown

        result = audit(selector, json.loads(args.selection.read_text(encoding="utf-8")), args.junit, args.rerun_junit)
        print(json.dumps(result, indent=1))
        if args.summary:
            args.summary.write_text(audit_markdown(result), encoding="utf-8")
        return 1 if args.fail_on_escape and result["escapes"] else 0

    if args.command == "history":
        from selection.evaluate import history

        print(json.dumps(history(selector, args.commits, args.ref), indent=1))
        return 0

    if args.command == "explain":
        record = selector.tests.get(args.nodeid) or next(
            (r for n, r in selector.tests.items() if n.startswith(args.nodeid)), None
        )
        print(json.dumps(record, indent=1) if record else f"{args.nodeid}: not in the map")
        return 0 if record else 1

    if args.command == "merge-additions":
        from selection.selector import merge_additions

        data = json.loads(args.selection.read_text(encoding="utf-8"))
        additions = json.loads(args.additions.read_text(encoding="utf-8")) if args.additions.exists() else []
        merged, accepted = merge_additions(selector, data, additions)
        args.selection.write_text(json.dumps(merged, indent=1) + "\n", encoding="utf-8")
        print(f"added {len(accepted)} test(s) suggested by the reviewer")
        github_output(count=count_selected(selector, merged))
        if args.summary and accepted:
            with args.summary.open("a", encoding="utf-8") as fh:
                fh.write("\n**Added by the AI reviewer:**\n\n")
                fh.writelines(f"- `{a['test']}`: {a['reason']}\n" for a in accepted)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
