"""pytest options for Selection Based Testing, registered by tests-python/conftest.py.

--collect-impact=PATH   record each e2e test's footprint and merge it into PATH (the impact map)
--select-from=FILE      run only the e2e tests listed in a selection.json (`python -m selection select`)
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from selection.impact import REPO_ROOT, ImpactRecorder


def add_options(parser: pytest.Parser) -> None:
    group = parser.getgroup("selection", "Selection Based Testing")
    group.addoption("--collect-impact", metavar="PATH", help="record e2e test footprints into this impact map")
    group.addoption("--select-from", metavar="FILE", help="run only the e2e tests in this selection.json")


def filter_items(items: list[pytest.Item], selection: dict) -> tuple[list[pytest.Item], list[pytest.Item]]:
    """Splits items into (keep, drop). Only e2e tests are filtered; entries are node ids (with or
    without the `[chromium-...]` parameter part) or path prefixes such as `tests-python/e2e/web/`."""
    if selection.get("mode") == "all":
        return list(items), []
    wanted = set(selection.get("selected", []))
    prefixes = tuple(w for w in wanted if "::" not in w or w.endswith("::"))
    keep, drop = [], []
    for item in items:
        nodeid = item.nodeid
        base = nodeid.split("[", 1)[0]
        selected = nodeid in wanted or base in wanted or bool(prefixes and nodeid.startswith(prefixes))
        if item.get_closest_marker("e2e") is None or selected:
            keep.append(item)
        else:
            drop.append(item)
    return keep, drop


class SelectionPlugin:
    def __init__(self, config: pytest.Config):
        self.recorder: ImpactRecorder | None = None
        out = config.getoption("--collect-impact")
        if out:
            from support.config import ADMIN_BASE_URL, WEB_BASE_URL

            self.recorder = ImpactRecorder(Path(out), {WEB_BASE_URL: "apps/web", ADMIN_BASE_URL: "apps/admin"})

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, config: pytest.Config, items: list[pytest.Item]) -> None:
        selection_file = config.getoption("--select-from")
        if not selection_file:
            return
        selection = json.loads(Path(selection_file).read_text(encoding="utf-8"))
        keep, drop = filter_items(items, selection)
        if drop:
            config.hook.pytest_deselected(items=drop)
            items[:] = keep

    @pytest.fixture(autouse=True)
    def _impact_footprint(self, request: pytest.FixtureRequest) -> Iterator[None]:
        if self.recorder is None or request.node.get_closest_marker("e2e") is None:
            yield
            return
        page = request.getfixturevalue("page")
        mock_backend = request.getfixturevalue("mock_backend")
        with self.recorder.record(request.node.nodeid, page, mock_backend):
            yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):
        outcome = yield
        report = outcome.get_result()
        if self.recorder is not None and report.when == "call":
            self.recorder.set_outcome(item.nodeid, report.outcome, report.duration)

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        if self.recorder is None or not self.recorder.tests:
            return
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()
        path = self.recorder.write(commit)
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(f"impact map: {len(self.recorder.tests)} tests recorded -> {path}")
