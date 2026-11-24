# Selection Based Testing (e2e)

Runs only the Python e2e tests (`tests-python/e2e`) that a change can affect. How good the selection is gets measured, not assumed; see [EVALUATION.md](EVALUATION.md).

```
              nightly / --collect-impact                          every PR
full e2e run ───────────────────────────▶ impact-map.json ──┐
  per test: front-end modules that ran (V8 coverage, CDP)   │   git diff base...head
            API endpoints it called (mock backend log)      ├─▶ python -m selection select ─▶ selection.json
            Python helpers that ran (sys.setprofile)        │   (+ optional AI reviewer: add-only)
Spring controllers ─▶ endpoint graph (backend.py) ──────────┘           │
                                                                        ▼
                                              pytest -m e2e --select-from=selection.json
                                              (+ shadow: full run + audit for escapes)
```

## How a change is mapped to tests

For each changed file, the first matching rule wins (`rules.py`, `selector.py`):

| # | Rule | Example | Tests |
|---|---|---|---|
| 1 | `RUN_ALL`: affects every test | `apps/web/package-lock.json`, `vite.config.*`, `tests-python/e2e/conftest.py`, `support/config.py`, backend `config/`, `security/` | all |
| 2 | `IGNORE`: nothing in the e2e run depends on it | `*.md`, `agentic-workflows/**`, `.claude/**`, TS e2e specs, unit/integration tests | none |
| 3 | A changed e2e test file | `tests-python/e2e/web/test_cart_totals.py` | its tests, including new ones not in the map yet |
| 3b | `SUITE_FILES`: a suite-wide file | `tests-python/e2e/web/conftest.py` (session fixtures run once), `apps/web/src/main.tsx` | that whole suite |
| 4 | **Impact map** | `apps/web/src/pages/Tracking/index.tsx`, `pages/web/cart_panel.py` | the tests whose footprint contains the file |
| 5 | **Backend → endpoints** | `service/OrderReviewService.java` → controllers that reach it → `POST /api/customer/orders/{*}/review`… | the tests that called one of those endpoints |
| 6 | `FALLBACK_SUITES`: a file no recorded test executed | a new `apps/web/src/components/x.tsx` | the whole web (or admin) suite |
| 7 | Unknown file | `scripts/new.sh` | all |

Then two smoke tests (`ALWAYS`, one per app) are added whenever anything is selected. A missing impact map means everything runs. A map older than 7 days gives a warning.

**Footprints** (`impact.py`):
- **Front end.** Chromium's precise coverage over CDP, on the Vite dev servers, whose module URLs are source paths.
  - A module counts when one of its functions ran. The React Fast Refresh boilerplate that runs on load is ignored.
  - Modules with no functions (JSON, CSS, constants) count when they were loaded.
  - Coverage is per document, so it is snapshotted before every `page.goto()` / `page.reload()`.
  - A switch between the two app origins in one test can't be read reliably, so it counts the whole target app (`apps/admin/src/*`).
- **API.** Every request the mock backend answers, browser and `api` fixture alike, normalised as `GET /api/dish/{*}/active`.
- **Python.** The page objects, clients, support modules and conftest fixtures that ran.

**Backend** (`backend.py`):
- Controller paths come from `@RequestMapping` plus `@Get/Post/Put/Patch/DeleteMapping`, with the `ControllerUtil` constants resolved.
- A change inside one handler selects that endpoint only.
- Any other class reaches the controllers that reference it, transitively by class name.
- Note: in CI the e2e suite runs against the in-memory mock, so a backend-only change selects the right tests, but they can't fail on it. The integration suite and the TypeScript e2e suites against a real backend are the ones that catch backend regressions. The mapping is ready for those runs.

## Commands

```bash
python -m selection select --base origin/main --summary selection.md     # writes selection.json
pytest -m e2e --select-from=selection.json                                # run only those
python -m selection select --files apps/web/src/lib/utils.ts              # what-if for given files
python -m selection explain tests-python/e2e/web/test_cart_totals.py::test_header_cart_badge_counts_items
pytest -m e2e --collect-impact=selection/impact-map.json                  # rebuild the map (full run)
python -m selection evaluate                                              # mutation benchmark (slow)
python -m selection audit --selection selection.json --junit full.xml     # shadow-mode check
python -m selection history --commits 30                                  # cost over past commits
```

## CI

| Workflow | When | Does |
|---|---|---|
| `selective-e2e.yml` | every PR | select (+ AI reviewer if `vars.SELECTION_AI_REVIEW == 'true'`), run the selected tests. In **shadow mode** (default, until `vars.SELECTION_SHADOW == 'false'`) it also runs the full suite and fails the `shadow` job on an escape |
| `impact-map.yml` | nightly on `main` | full run with `--collect-impact`, history replay, PR with the refreshed map |
| `github-actions-foodme-demo.yml` | push to `main` | still runs the full e2e suite (no selection on `main`) |

The optional **AI reviewer** (Claude) sees the diff and the selection. It can only **add** tests the map can't see, such as UI text other tests assert on, or behaviour reached through data or config. `merge-additions` accepts only known node ids or existing e2e test files, and never removes anything.

## Files

`rules.py` (policy) · `impact.py` (recorder) · `pytest_plugin.py` (`--collect-impact`, `--select-from`) · `backend.py` · `selector.py` · `evaluate.py` + `mutations.py` (benchmark, audit, history) · `impact-map.json` (data) · `eval/` (benchmark results). Unit tests: `tests-python/unit/test_selection.py`.
