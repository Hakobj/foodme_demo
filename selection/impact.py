"""Records what each e2e test touches, for the impact map (selection/impact-map.json).

Per test, three footprints:
1. Front-end modules that ran: V8 precise coverage over CDP (Chromium only) on the Vite dev servers,
   whose module URLs are the source paths (`/src/pages/Chef/index.tsx` -> `apps/web/src/...`).
   A module counts when one of its functions ran (ignoring the React Fast Refresh boilerplate that
   runs on load), or when it has no functions at all (JSON, CSS, constants) and was loaded.
   Coverage lives per document, so it is snapshotted before every `page.goto()` / `page.reload()`.
2. API endpoints called, browser and Python `api` fixture alike (`GET /api/chef/{*}`), from the mock.
3. Python helpers that ran (page objects, clients, support, conftest fixtures), via `sys.setprofile`.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from selection.backend import endpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
PY_DIRS = ("pages", "support", "clients", "tests-python")
HMR_MARKERS = ("RefreshRuntime", "$RefreshReg$", "$RefreshSig$", "import.meta.hot")
HMR_NAMES = {"$RefreshReg$", "$RefreshSig$"}
FUNCTION_RE = re.compile(r"=>|\bfunction\b")


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class ImpactRecorder:
    def __init__(self, out_path: Path, origins: dict[str, str]):
        """`origins` maps a dev-server origin (`http://localhost:5180`) to its app dir (`apps/web`)."""
        self.out_path = out_path
        self.origins = {o.rstrip("/"): app for o, app in origins.items()}
        self.tests: dict[str, dict[str, Any]] = {}
        self.outcomes: dict[str, tuple[str, float]] = {}  # reported before the fixture teardown
        self._source_cache: dict[str, str] = {}
        self._functions_cache: dict[str, bool] = {}
        self._py_cache: dict[Any, str] = {}

    # ---- per test ----------------------------------------------------------------------------

    @contextlib.contextmanager
    def record(self, nodeid: str, page: Any, mock_backend: Any) -> Iterator[None]:
        files: set[str] = set()
        endpoints: set[str] = set()
        started = time.monotonic()
        restore_send = self._watch_api(mock_backend, endpoints)
        cdp = self._start_coverage(page)
        restore_nav = self._snapshot_before_navigation(page, cdp, files)
        previous_profiler = sys.getprofile()
        sys.setprofile(self._python_profiler(files))
        try:
            yield
        finally:
            sys.setprofile(previous_profiler)
            self._snapshot(cdp, files)
            restore_nav()
            restore_send()
            with contextlib.suppress(Exception):
                cdp.detach()
            self.tests[nodeid] = {
                "files": sorted(files),
                "endpoints": sorted(endpoints),
                "duration": round(time.monotonic() - started, 2),
            }

    def set_outcome(self, nodeid: str, outcome: str, duration: float) -> None:
        self.outcomes[nodeid] = (outcome, round(duration, 2))

    # ---- API endpoints ------------------------------------------------------------------------

    @staticmethod
    def _watch_api(mock_backend: Any, endpoints: set[str]):
        original = mock_backend.send

        def send(request, **kwargs):
            endpoints.add(endpoint(request.method or "GET", urlsplit(request.url or "").path))
            return original(request, **kwargs)

        mock_backend.send = send  # instance attribute: covers handle_route() and the `api` fixture

        def restore() -> None:
            with contextlib.suppress(AttributeError):
                del mock_backend.send

        return restore

    # ---- front-end coverage -------------------------------------------------------------------

    @staticmethod
    def _start_coverage(page: Any) -> Any:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Profiler.enable")
        cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": False})
        return cdp

    def _snapshot_before_navigation(self, page: Any, cdp: Any, files: set[str]):
        """Wraps page.goto / page.reload: a full navigation drops the old document's coverage."""
        originals = {name: getattr(page, name) for name in ("goto", "reload")}

        def wrap(name: str):
            def navigate(*args, **kwargs):
                self._snapshot(cdp, files)
                before = _origin(page.url)
                result = originals[name](*args, **kwargs)
                after = _origin(page.url)
                if after != before and before in self.origins:  # not the first goto from about:blank
                    # A cross-origin navigation swaps the renderer process and its coverage can't be
                    # read reliably any more: count the whole app on that origin (safe direction).
                    if after in self.origins:
                        files.add(f"{self.origins[after]}/src/*")
                    with contextlib.suppress(Exception):
                        cdp.send("Profiler.enable")
                        cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": False})
                return result

            return navigate

        for name in originals:
            setattr(page, name, wrap(name))

        def restore() -> None:
            for name in originals:
                with contextlib.suppress(AttributeError):
                    delattr(page, name)

        return restore

    def _snapshot(self, cdp: Any, files: set[str]) -> None:
        try:
            scripts = cdp.send("Profiler.takePreciseCoverage")["result"]
        except Exception:  # page already closed / session detached
            return
        for script in scripts:
            rel = self._source_path(script.get("url", ""))
            if rel and self._module_ran(script):
                files.add(rel)

    def _source_path(self, url: str) -> str | None:
        parts = urlsplit(url)
        app = self.origins.get(f"{parts.scheme}://{parts.netloc}")
        if not app or not parts.path.startswith("/src/"):
            return None
        return f"{app}{parts.path}"

    def _module_ran(self, script: dict[str, Any]) -> bool:
        source = self._source(script["url"])
        real = []
        for function in script.get("functions", []):
            start, end = function["ranges"][0]["startOffset"], function["ranges"][0]["endOffset"]
            if start == 0:  # the module body itself
                continue
            if function.get("functionName") in HMR_NAMES or any(m in source[start:end] for m in HMR_MARKERS):
                continue
            real.append(function)
        if any(f["ranges"][0]["count"] > 0 for f in real):
            return True
        # Later snapshots omit functions that didn't run since the previous one (the counters reset),
        # so "has no functions" comes from the source: JSON, CSS and constant modules count when loaded.
        return not self._has_functions(script["url"])

    def _has_functions(self, url: str) -> bool:
        if url not in self._functions_cache:
            lines = self._source(url).splitlines()
            code = "\n".join(line for line in lines if not any(m in line for m in HMR_MARKERS))
            self._functions_cache[url] = bool(FUNCTION_RE.search(code))
        return self._functions_cache[url]

    def _source(self, url: str) -> str:
        if url not in self._source_cache:
            try:
                self._source_cache[url] = requests.get(url, timeout=10).text
            except requests.RequestException:
                self._source_cache[url] = ""
        return self._source_cache[url]

    # ---- Python helpers -----------------------------------------------------------------------

    def _python_profiler(self, files: set[str]):
        cache = self._py_cache
        root = os.path.normcase(str(REPO_ROOT))  # the drive letter's case varies on Windows

        def profiler(frame, event, arg):
            if event != "call":
                return
            code = frame.f_code
            rel = cache.get(code)
            if rel is None:
                rel = ""
                filename = os.path.normcase(os.path.abspath(code.co_filename))
                if filename.startswith(root):
                    candidate = Path(filename[len(root) :].lstrip("\\/")).as_posix()
                    # test modules select themselves (rule in selector.py); conftest fixtures count
                    if candidate.startswith(PY_DIRS) and not Path(candidate).name.startswith("test_"):
                        rel = candidate
                cache[code] = rel
            if rel:
                files.add(rel)

        return profiler

    # ---- output --------------------------------------------------------------------------------

    def write(self, commit: str) -> Path:
        """Merges this run into the map: tests that ran are replaced, the others kept."""
        data: dict[str, Any] = {"meta": {}, "tests": {}}
        if self.out_path.exists():
            data = json.loads(self.out_path.read_text(encoding="utf-8"))
        for nodeid, record in self.tests.items():
            outcome, duration = self.outcomes.get(nodeid, ("unknown", record["duration"]))
            data["tests"][nodeid] = {**record, "outcome": outcome, "call_duration": duration}
        data["meta"] = {
            "commit": commit,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tests": len(data["tests"]),
            "collector": "selection.impact (V8 coverage via CDP + mock API log + sys.setprofile)",
        }
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return self.out_path
