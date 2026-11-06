---
name: run-python-tests
description: >-
  Run the FoodMe Python test suite in tests-python/ (pytest + requests + Playwright
  for Python) and report the results: API tests (port of the JUnit suite), storefront
  UI tests and admin UI tests. Use when asked to run the Python tests, pytest, a
  Python test file/function, a marker (-m api / web / admin), re-run failures, or
  check Python tests for flakiness.
---

# Running the Python tests (FoodMe)

The suite lives in `tests-python/` (see its `README.md`). Run what was asked, check prerequisites first, and report honest results. **Don't change app or test code to make tests pass** unless the user asks. A failure caused by a seeded `FM-BUG-NN` or an `FM-FLAKE-NN` test is an expected course result; report it as such.

For the Java/TypeScript suites use the `run-tests` skill instead.

## 1. Pick the scope
| User asks for | Command (from `tests-python/`) |
|---|---|
| "all Python tests" | `pytest` |
| API / backend | `pytest -m api` |
| storefront / web | `pytest -m web` |
| admin / back office | `pytest -m admin` |
| a file | `pytest tests/web/test_layout.py` |
| one test | `pytest tests/api/test_order_api.py::test_create_order_cash_payment_succeeds` |
| by name | `pytest -k "checkout and not idram"` |
| admin class | `pytest "tests/admin/test_admin_flows.py::TestAdminResources"` |

Say which scope you picked in one line.

## 2. Check prerequisites
Stop with a clear message if one fails. Never report a suite as passed when it was skipped.

| Needed for | Check | If missing |
|---|---|---|
| everything | `python --version` is 3.10+ | Install Python |
| everything | `.venv` exists and `python -c "import pytest, requests, playwright"` works inside it | `python -m venv .venv` then `.venv/Scripts/pip install -r requirements.txt` (macOS/Linux: `.venv/bin/pip`). **Ask first**, it downloads packages |
| web, admin | Chromium for Playwright Python: `.venv/Scripts/playwright install chromium` | Ask first |
| everything | Backend up: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/actuator/health` returns `200` | Needs Postgres (`foodme`/`foodme`/`foodme` on `localhost:5432`) + `cd apps/backend && ./gradlew bootRun`. Offer to start the backend in the background; don't start Postgres yourself |
| web / admin | `apps/web/node_modules` / `apps/admin/node_modules` exist | `npm ci` in that app (ask first). The suite starts the Vite dev servers on 5180 / 5174 itself when they aren't running, and stops them afterwards |

If the backend is down, the `api` fixture **skips** every test (`backend not reachable at ...`). Report that as "not run", not as passed.

Always run through the venv: `.venv/Scripts/python -m pytest ...` (Windows) or `.venv/bin/python -m pytest ...`.

## 3. Useful options
```bash
python -m pytest -m web --headed --slowmo 300              # watch the browser
python -m pytest --lf                                      # only the tests that failed last time
python -m pytest -x                                        # stop at the first failure
python -m pytest -m web --tracing retain-on-failure --screenshot only-on-failure   # artifacts in test-results/
python -m pytest --junitxml=test-results/junit.xml         # machine-readable results for counting
python -m pytest -vv -rA                                   # verbose, with a summary of every outcome
```
- Other environments: set `VITE_API_BASE_URL`, `PLAYWRIGHT_BASE_URL`, `ADMIN_BASE_URL`.
- Flakiness check: re-run the test 3–5 times in a shell loop, or install `pytest-repeat` (ask first) and use `--count=5`.
- No parallel runner is installed. Don't add `-n` (pytest-xdist) unless the user agrees; admin tests share the admin account and should stay serial.

## 4. Known behavior of this suite
- `tests/api/test_order_api.py` FM-FLAKE-02 tests expect order `FM-100001`. They only pass on a freshly created database, so they fail on any reused Postgres. That's the seeded flake, not a regression.
- FM-FLAKE-03 (`test_dish_api.py`) compares two endpoints' ordering; FM-FLAKE-04 (`created_at_falls_on_today`) fails around midnight / timezone differences.
- FM-FLAKE-01 (`test_flake_dish_modal.py`) uses a fixed `wait_for_timeout(300)` on purpose.
- FM-BUG-07 (`test_cart_quantity_decrease_keeps_item_until_minimum_is_reached`) and FM-BUG-02 (layout chef count) assert seeded bugs.
- `test_admin_can_login_and_list_orders_after_a_storefront_checkout` opens `/backoffice` on the backend, which exists only when the SPAs are bundled into the backend (Docker build). On a plain `bootRun` that last step can fail: classify as environment.

## 5. Investigate failures (read-only)
For each failure: test node id, `file:line`, the assertion (expected vs actual) from pytest's output. For UI tests, re-run that test with `--tracing on` and point the user to `playwright show-trace test-results/<test>/trace.zip`.

Classify: **seeded bug** (FM-BUG marker), **seeded flake** (FM-FLAKE marker, confirm by re-running), **environment** (backend/dev server down, port busy, missing browser, cold-start timeouts; the backend adds 200–1500 ms latency), or **real regression** (point to the likely cause). Re-run a failure once before calling it flaky, and say so.

## 6. Report
```
Python API:   14 passed, 2 failed (FM-FLAKE-02)          (pytest -m api, 12s)
Python web:   21 passed, 1 failed                        (pytest -m web)
Python admin: not run - backend not reachable on :8081
```
Take counts from pytest's final summary line or `junit.xml`, not from memory. List the exact commands you ran. If you started a backend, say so and give its PID. End by offering next steps: re-run, show a trace, or investigate/fix a specific failure.
