"""Evaluates the selection. Three methods (selection/EVALUATION.md explains the strategy):

- `mutations`: inject each change from selection/mutations.py, select, run the FULL e2e suite as
   ground truth, and score: did the selection contain a failing test (detection), how many of the
   failing tests it contained (recall), how many tests / minutes it ran (cost). Slow: one full run
   per mutation. Results go to selection/eval/mutation-results.json and a markdown report.
- `audit`: shadow mode in CI. A PR runs the selection AND the full suite; any test that failed in
   the full run but was not selected is an escape.
- `history`: replays the selection over past commits (cost only, no ground truth).
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from selection.mutations import MUTATIONS, Mutation
from selection.selector import REPO_ROOT, Change, Selector, changed_files, estimated_minutes, git

EVAL_DIR = REPO_ROOT / "selection" / "eval"


# ---- junit ------------------------------------------------------------------------------------


def junit_results(path: Path) -> dict[str, str]:
    """node id -> passed | failed | error | skipped, from a pytest --junitxml report."""
    results: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name", "")
        parts = classname.split(".")
        # tests-python.e2e.web.test_x[.TestClass] -> tests-python/e2e/web/test_x.py[::TestClass]
        module_end = next((i for i, p in enumerate(parts) if p.startswith("test_")), len(parts) - 1)
        nodeid = "/".join(parts[: module_end + 1]) + ".py"
        if parts[module_end + 1 :]:
            nodeid += "::" + "::".join(parts[module_end + 1 :])
        nodeid += f"::{name}"
        status = "passed"
        for child in case:
            if child.tag in ("failure", "error"):
                status = "failed"
            elif child.tag == "skipped":
                status = "skipped"
        results[nodeid] = status
    return results


def failed(results: dict[str, str]) -> set[str]:
    return {n for n, s in results.items() if s == "failed"}


# ---- one mutation ------------------------------------------------------------------------------


def _changed_lines(text: str, find: str) -> set[int]:
    start = text.index(find)
    first = text.count("\n", 0, start) + 1
    return set(range(first, first + find.count("\n") + 1))


def run_e2e(junit: Path, extra: list[str] | None = None) -> float:
    started = time.monotonic()
    subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "e2e", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"]
        + (extra or []),
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return time.monotonic() - started


def evaluate_mutation(selector: Selector, mutation: Mutation, baseline_failed: set[str]) -> dict[str, Any]:
    path = REPO_ROOT / mutation.file
    original = path.read_bytes()
    crlf = b"\r\n" in original
    text = original.decode("utf-8")
    find = mutation.find.replace("\n", "\r\n") if crlf else mutation.find
    replace = mutation.replace.replace("\n", "\r\n") if crlf else mutation.replace
    if text.count(find) != 1:
        return {"id": mutation.id, "error": f"find string occurs {text.count(find)} times in {mutation.file}"}

    lines = _changed_lines(text.replace("\r\n", "\n"), mutation.find)
    selection = selector.select([Change(mutation.file, "M", lines)])
    selected = set(selector.expand(selection))
    row: dict[str, Any] = {
        "id": mutation.id,
        "file": mutation.file,
        "description": mutation.description,
        "ground_truth": mutation.ground_truth,
        "mode": selection.mode,
        "selected": len(selected),
        "total": selection.total,
        "selected_minutes": round(estimated_minutes(selector, sorted(selected)), 2),
        "total_minutes": round(estimated_minutes(selector, sorted(selector.tests)), 2),
        "effects": [f["effect"] for f in selection.files],
    }
    if not mutation.ground_truth:
        return row

    junit = EVAL_DIR / "junit" / f"{mutation.id}.xml"
    junit.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(text.replace(find, replace).encode("utf-8"))
        row["full_run_seconds"] = round(run_e2e(junit))
    finally:
        path.write_bytes(original)

    failing = failed(junit_results(junit)) - baseline_failed  # failures caused by the mutation
    caught = failing & selected
    row.update(
        {
            "killed": bool(failing),
            "failing": sorted(failing),
            "failing_selected": sorted(caught),
            "escaped": sorted(failing - selected),
            "detected": bool(caught) if failing else None,
            "recall": round(len(caught) / len(failing), 3) if failing else None,
        }
    )
    return row


# ---- aggregate ---------------------------------------------------------------------------------


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in rows if r.get("ground_truth") and "error" not in r]
    killed = [r for r in scored if r.get("killed")]
    ratios = [r["selected"] / r["total"] for r in rows if "error" not in r and r.get("total")]
    minutes = [1 - r["selected_minutes"] / r["total_minutes"] for r in rows if r.get("total_minutes")]
    return {
        "mutations": len(rows),
        "with_ground_truth": len(scored),
        "killed_by_full_suite": len(killed),
        "survived_full_suite": len(scored) - len(killed),
        "detected_by_selection": sum(1 for r in killed if r["detected"]),
        "fault_detection_rate": round(sum(1 for r in killed if r["detected"]) / len(killed), 3) if killed else None,
        "mean_test_recall": round(statistics.mean(r["recall"] for r in killed), 3) if killed else None,
        "escaped_tests": sum(len(r["escaped"]) for r in killed),
        "mean_selection_ratio": round(statistics.mean(ratios), 3) if ratios else None,
        "median_selection_ratio": round(statistics.median(ratios), 3) if ratios else None,
        "mean_time_saved": round(statistics.mean(minutes), 3) if minutes else None,
        "run_all_decisions": sum(1 for r in rows if r.get("mode") == "all"),
    }


def report_markdown(rows: list[dict[str, Any]], totals: dict[str, Any], meta: dict[str, Any]) -> str:
    def pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value * 100:.0f}%"

    out = [
        "# Selection evaluation: mutation benchmark",
        "",
        f"Commit `{meta['commit'][:10]}` · impact map from `{meta['map_commit'][:10]}` · {meta['generated_at']}",
        f"Baseline (unmutated) full run: {meta['baseline_tests']} e2e tests, "
        f"{len(meta['baseline_failed'])} failing before any mutation.",
        "",
        "| Metric | Value | Target |",
        "|---|---|---|",
        f"| Fault detection rate (killed mutants caught by the selection) | "
        f"{pct(totals['fault_detection_rate'])} ({totals['detected_by_selection']}/{totals['killed_by_full_suite']})"
        " | 100% |",
        f"| Mean test recall (failing tests that were selected) | {pct(totals['mean_test_recall'])} | ≥ 95% |",
        f"| Escaped failing tests | {totals['escaped_tests']} | 0 |",
        f"| Median selection ratio (tests run / all) | {pct(totals['median_selection_ratio'])} | ≤ 40% |",
        f"| Mean e2e time saved | {pct(totals['mean_time_saved'])} | ≥ 50% |",
        f"| Mutants the full suite did not kill | {totals['survived_full_suite']} | (suite gap, not selector) |",
        f"| Run-all decisions | {totals['run_all_decisions']} of {totals['mutations']} | |",
        "",
        "| Mutation | Decision | Selected | Failing (full run) | Caught | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            out.append(f"| `{r['id']}` | error: {r['error']} | | | | |")
            continue
        decision = "run all" if r["mode"] == "all" else "; ".join(sorted(set(r["effects"])))
        if not r.get("ground_truth"):
            out.append(f"| `{r['id']}` | {decision} | {r['selected']}/{r['total']} | (selection only) | | |")
            continue
        caught = "—" if not r["killed"] else ("✅" if r["detected"] else "❌ ESCAPE")
        recall = "—" if r["recall"] is None else f"{r['recall'] * 100:.0f}%"
        out.append(
            f"| `{r['id']}` | {decision} | {r['selected']}/{r['total']} | {len(r['failing'])} | {caught} | {recall} |"
        )
    escapes = [(r["id"], t) for r in rows for t in r.get("escaped", [])]
    if escapes:
        out += ["", "## Escapes", "", *[f"- `{mid}`: `{t}`" for mid, t in escapes]]
    return "\n".join(out) + "\n"


def run_mutations(
    selector: Selector, only: list[str] | None = None, baseline: Path | None = None, label: str = ""
) -> dict:
    """Writes eval/mutation-results[-label].json and eval/mutation-report[-label].md. Use a label for a
    partial re-run (e.g. after a fix), so the earlier full round stays as it was."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if baseline is None:
        baseline = EVAL_DIR / "junit" / "baseline.xml"
        baseline.parent.mkdir(parents=True, exist_ok=True)
        print("baseline: full e2e run without mutations ...", flush=True)
        run_e2e(baseline)
    base_results = junit_results(baseline)
    base_failed = failed(base_results)
    rows = []
    for mutation in MUTATIONS:
        if only and mutation.id not in only:
            continue
        print(f"mutation {mutation.id} ...", flush=True)
        row = evaluate_mutation(selector, mutation, base_failed)
        print(f"  -> {json.dumps({k: row.get(k) for k in ('mode', 'selected', 'killed', 'detected', 'recall')})}")
        rows.append(row)
    meta = {
        "commit": git("rev-parse", "HEAD").strip(),
        "map_commit": (selector.map or {}).get("meta", {}).get("commit", ""),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "baseline_tests": len(base_results),
        "baseline_failed": sorted(base_failed),
    }
    totals = aggregate(rows)
    result = {"meta": meta, "totals": totals, "rows": rows}
    suffix = f"-{label}" if label else ""
    (EVAL_DIR / f"mutation-results{suffix}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    (EVAL_DIR / f"mutation-report{suffix}.md").write_text(report_markdown(rows, totals, meta), encoding="utf-8")
    return result


# ---- shadow mode -------------------------------------------------------------------------------


def audit(selector: Selector, selection: dict[str, Any], full_junit: Path, rerun_junit: Path | None = None) -> dict:
    """Compares a selection with a full run of the same commit. A failure that also fails on rerun
    and wasn't selected is an escape; a failure that passes on rerun is flaky and not counted."""
    results = junit_results(full_junit)
    failing = failed(results)
    flaky: set[str] = set()
    if rerun_junit is not None and rerun_junit.exists():
        flaky = failing - failed(junit_results(rerun_junit))
    from selection.selector import Selection

    sel = Selection(selection["mode"], set(selection["selected"]), {}, [], [], selection.get("total", 0))
    selected = set(selector.expand(sel)) if sel.mode == "subset" else set(results)
    # tests new since the map was built are matched by prefix
    prefixes = tuple(s for s in sel.selected if "::" not in s or s.endswith("::"))
    selected |= {n for n in results if prefixes and n.startswith(prefixes)}
    real = failing - flaky
    escapes = sorted(n for n in real if n not in selected and n.split("[", 1)[0] not in sel.selected)
    return {
        "mode": sel.mode,
        "full_run_tests": len(results),
        "full_run_failed": sorted(real),
        "flaky": sorted(flaky),
        "selected": len(selected & set(results)),
        "escapes": escapes,
        "verdict": "escape" if escapes else "ok",
    }


def audit_markdown(result: dict[str, Any]) -> str:
    lines = [
        "## Selection audit (shadow mode)",
        "",
        f"Full run: {result['full_run_tests']} e2e tests, {len(result['full_run_failed'])} failed"
        f" ({len(result['flaky'])} flaky, not counted). Selection ran {result['selected']}.",
        "",
        f"**Verdict:** {'❌ ' + str(len(result['escapes'])) + ' escape(s)' if result['escapes'] else '✅ no escapes'}",
    ]
    lines += [f"- `{e}` failed in the full run but was not selected" for e in result["escapes"]]
    return "\n".join(lines) + "\n"


# ---- history -----------------------------------------------------------------------------------


def history(selector: Selector, commits: int, ref: str = "HEAD") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for sha in git("rev-list", "--first-parent", f"--max-count={commits}", ref).split():
        parents = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
        if not parents:
            continue
        selection = selector.select(changed_files(parents[0], sha), parents[0], sha)
        run = selector.expand(selection)
        rows.append(
            {
                "commit": sha[:10],
                "subject": git("log", "-1", "--format=%s", sha).strip()[:70],
                "mode": selection.mode,
                "selected": len(run),
                "total": selection.total,
            }
        )
    affecting = [r for r in rows if r["selected"]]
    ratios = [r["selected"] / r["total"] for r in rows if r["total"]]
    return {
        "commits": len(rows),
        "no_e2e_needed": len(rows) - len(affecting),
        "run_all": sum(1 for r in rows if r["mode"] == "all"),
        "median_selection_ratio": round(statistics.median(ratios), 3) if ratios else None,
        "rows": rows,
    }
