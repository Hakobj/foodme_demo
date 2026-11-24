"""Selects the e2e tests a change can affect, from a git diff and the impact map.

For every changed file, in this order (selection/rules.py holds the patterns):
1. RUN_ALL           -> every e2e test (build config, shared fixtures, cross-cutting backend code)
2. IGNORE            -> no tests (docs, other suites, pipeline runs, ...)
3. e2e test file     -> the tests in that file (also new tests that aren't in the map yet)
3b. SUITE_FILES      -> the whole suite (suite conftest, app entry point)
4. impact map        -> the tests whose recorded footprint contains the file
5. backend source    -> the tests that called an endpoint the file can affect (selection/backend.py)
6. FALLBACK_SUITES   -> the whole suite of that app (a file no recorded test touched)
7. anything else     -> every e2e test (unknown file: be safe)
Then the ALWAYS smoke tests are added. A missing impact map means every test runs.
"""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from selection import rules
from selection.backend import BackendIndex

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = REPO_ROOT / "selection" / "impact-map.json"


def matches(path: str, patterns: list[str]) -> str | None:
    return next((p for p in patterns if fnmatch.fnmatchcase(path, p)), None)


# ---- git --------------------------------------------------------------------------------------


@dataclass
class Change:
    path: str
    status: str  # A, M, D, R
    lines: set[int] = field(default_factory=set)  # changed lines in the new file


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def changed_files(base: str, head: str | None = None, cwd: Path = REPO_ROOT) -> list[Change]:
    """Files changed between merge-base(base, head) and head; head=None means the working tree."""
    rev = [f"{base}...{head}"] if head else [base]
    changes: dict[str, Change] = {}
    for line in git("diff", "--name-status", "-M", *rev, cwd=cwd).splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        for path in parts[1:]:  # a rename lists the old and the new path: both matter
            changes[path] = Change(path, status)
    current: Change | None = None
    for line in git("diff", "-U0", "-M", *rev, cwd=cwd).splitlines():
        if line.startswith("+++ "):
            name = line[6:] if line.startswith("+++ b/") else ""
            current = changes.get(name)
        elif line.startswith("@@") and current is not None:
            hunk = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if hunk:
                start, count = int(hunk.group(1)), int(hunk.group(2) or 1)
                current.lines.update(range(start, start + max(count, 1)))
    return list(changes.values())


# ---- selection --------------------------------------------------------------------------------


@dataclass
class Selection:
    mode: str  # "subset" | "all"
    selected: set[str]
    reasons: dict[str, set[str]]  # test or prefix -> changed files that selected it
    files: list[dict[str, Any]]  # per changed file: what it did
    warnings: list[str]
    total: int
    base: str = ""
    head: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "base": self.base,
            "head": self.head,
            "mode": self.mode,
            "selected": sorted(self.selected),
            "selected_count": len(self.selected),
            "total": self.total,
            "reasons": {k: sorted(v) for k, v in sorted(self.reasons.items())},
            "files": self.files,
            "warnings": self.warnings,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


class Selector:
    def __init__(self, impact_map: dict[str, Any] | None, repo_root: Path = REPO_ROOT):
        self.map = impact_map
        self.tests: dict[str, dict[str, Any]] = (impact_map or {}).get("tests", {})
        self.repo_root = repo_root
        self._backend: BackendIndex | None = None

    @classmethod
    def from_file(cls, path: Path = DEFAULT_MAP) -> Selector:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        return cls(data)

    @property
    def backend(self) -> BackendIndex:
        if self._backend is None:
            self._backend = BackendIndex(self.repo_root)
        return self._backend

    # tests whose footprint contains `path` (a file, or a whole-app wildcard recorded for cross-origin)
    def tests_touching(self, path: str) -> set[str]:
        hits = set()
        for nodeid, record in self.tests.items():
            for recorded in record.get("files", []):
                if recorded == path or ("*" in recorded and fnmatch.fnmatchcase(path, recorded)):
                    hits.add(nodeid)
                    break
        return hits

    def tests_calling(self, endpoints: set[str]) -> set[str]:
        return {n for n, r in self.tests.items() if endpoints & set(r.get("endpoints", []))}

    def tests_in(self, prefix: str) -> set[str]:
        return {n for n in self.tests if n.startswith(prefix)}

    def select(self, changes: list[Change], base: str = "", head: str = "") -> Selection:
        warnings: list[str] = []
        if self.map is None:
            return Selection("all", set(), {}, [], ["no impact map: running every e2e test"], 0, base, head)
        warnings += self._map_warnings()
        selected: set[str] = set()
        reasons: dict[str, set[str]] = {}
        report: list[dict[str, Any]] = []
        run_all_because: list[str] = []

        def add(targets: set[str], why: str) -> None:
            for target in targets:
                selected.add(target)
                reasons.setdefault(target, set()).add(why)

        for change in sorted(changes, key=lambda c: c.path):
            path = change.path
            effect, count = self._classify(change, add, run_all_because)
            report.append({"file": path, "status": change.status, "effect": effect, "tests": count})

        if run_all_because:
            return Selection(
                "all", set(self.tests), {"*": set(run_all_because)}, report, warnings, len(self.tests), base, head
            )
        if selected:  # only add the smoke tests when the change affects the e2e run at all
            add({t for t in rules.ALWAYS if t in self._known_bases()}, "always-run smoke test")
        return Selection("subset", selected, reasons, report, warnings, len(self.tests), base, head)

    def _classify(self, change: Change, add, run_all_because: list[str]) -> tuple[str, int]:
        path = change.path
        if pattern := matches(path, rules.RUN_ALL):
            run_all_because.append(path)
            return f"run all (rule {pattern})", len(self.tests)
        if matches(path, rules.IGNORE):
            return "ignored", 0
        if path.startswith(rules.E2E_ROOT) and Path(path).name.startswith("test_") and path.endswith(".py"):
            # the file itself (as a prefix) also covers tests that were added after the map was built
            add({f"{path}::"} | self.tests_in(f"{path}::"), path)
            return "changed test file", len(self.tests_in(f"{path}::")) or 1
        for pattern, suite in rules.SUITE_FILES:
            if fnmatch.fnmatchcase(path, pattern):
                hits = self.tests_in(suite) | self.tests_touching(path)
                add(hits | {suite}, path)
                return f"suite-wide file: {suite}", len(hits)
        hits = self.tests_touching(path)
        if hits:
            add(hits, path)
            return "impact map", len(hits)
        if path.startswith(rules.BACKEND_SRC) and path.endswith(".java"):
            endpoints = self.backend.endpoints_for_change(path, change.lines if change.status != "D" else None)
            hits = self.tests_calling(endpoints)
            add(hits, path)
            return (f"backend: {len(endpoints)} endpoint(s)" if endpoints else "backend: no endpoint reached"), len(
                hits
            )
        for pattern, suite in rules.FALLBACK_SUITES:
            if fnmatch.fnmatchcase(path, pattern):
                hits = self.tests_in(suite)
                add(hits | {suite}, path)
                return f"not in the map: whole suite {suite}", len(hits)
        run_all_because.append(path)
        return "unknown file: run all", len(self.tests)

    def _known_bases(self) -> set[str]:
        return {n.split("[", 1)[0] for n in self.tests}

    def _map_warnings(self) -> list[str]:
        assert self.map is not None
        generated = self.map.get("meta", {}).get("generated_at", "")
        try:
            age_days = (time.time() - time.mktime(time.strptime(generated, "%Y-%m-%dT%H:%M:%SZ"))) / 86400
        except ValueError:
            return ["impact map has no generation time"]
        failed = [n for n, r in self.tests.items() if r.get("outcome") not in ("passed", None)]
        out = []
        if age_days > rules.MAP_MAX_AGE_DAYS:
            out.append(f"impact map is {age_days:.0f} days old (rebuild: nightly job or --collect-impact)")
        if failed:
            out.append(f"{len(failed)} test(s) failed while the map was recorded; their footprint may be partial")
        return out

    def expand(self, selection: Selection) -> list[str]:
        """Concrete node ids of the map that a selection runs (prefix entries expanded)."""
        if selection.mode == "all":
            return sorted(self.tests)
        prefixes = tuple(s for s in selection.selected if "::" not in s or s.endswith("::"))
        out = set()
        for nodeid in self.tests:
            base = nodeid.split("[", 1)[0]
            if nodeid in selection.selected or base in selection.selected or nodeid.startswith(prefixes):
                out.add(nodeid)
        return sorted(out)


def merge_additions(
    selector: Selector, selection: dict[str, Any], additions: list[Any]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Adds reviewer-suggested tests to a selection.json. Only known node ids (with or without the
    parameter part) and e2e test files are accepted, and nothing is ever removed."""
    if selection.get("mode") == "all" or not isinstance(additions, list):
        return selection, []
    known = set(selector.tests) | {n.split("[", 1)[0] for n in selector.tests}
    selected = set(selection.get("selected", []))
    accepted: list[dict[str, str]] = []
    for entry in additions:
        if not isinstance(entry, dict):
            continue
        test, reason = str(entry.get("test", "")).strip(), str(entry.get("reason", "")).strip()[:200]
        is_file = test.startswith(rules.E2E_ROOT) and test.endswith(".py") and (selector.repo_root / test).exists()
        if test in selected or not (test in known or is_file):
            continue
        target = f"{test}::" if is_file else test
        selected.add(target)
        selection.setdefault("reasons", {})[target] = [f"AI reviewer: {reason or 'no reason given'}"]
        accepted.append({"test": target, "reason": reason})
    selection["selected"] = sorted(selected)
    selection["selected_count"] = len(selected)
    selection["ai_additions"] = accepted
    return selection, accepted


# ---- reporting --------------------------------------------------------------------------------


def estimated_minutes(selector: Selector, nodeids: list[str]) -> float:
    return sum(selector.tests.get(n, {}).get("duration", 0.0) for n in nodeids) / 60


def summary_markdown(selector: Selector, selection: Selection) -> str:
    run = selector.expand(selection)
    total_min = estimated_minutes(selector, sorted(selector.tests))
    run_min = estimated_minutes(selector, run)
    lines = [
        "## Selection Based Testing",
        "",
        f"**Mode:** `{selection.mode}` · **e2e tests:** {len(run)} of {selection.total} "
        f"· **est. time:** {run_min:.1f} of {total_min:.1f} min",
        "",
        "| Changed file | Effect | Tests |",
        "|---|---|---|",
    ]
    lines += [f"| `{f['file']}` | {f['effect']} | {f['tests']} |" for f in selection.files] or ["| (none) | | |"]
    if selection.warnings:
        lines += ["", *[f"> ⚠️ {w}" for w in selection.warnings]]
    if selection.mode == "subset" and run:
        lines += ["", "<details><summary>Selected tests</summary>", ""]
        for nodeid in run:
            why = selection.reasons.get(nodeid) or selection.reasons.get(nodeid.split("[", 1)[0]) or set()
            lines.append(f"- `{nodeid}` ← {', '.join(sorted(why)) or 'prefix'}")
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"
