# FoodMe tests in Python (pytest + Playwright)

Python test suite for FoodMe. The tests live in `tests-python/`, split by test level. The page objects,
API clients and helpers (`clients/`, `pages/`, `support/`), the config (`pytest.ini`, `pyproject.toml`),
the requirements and the `.venv` sit at the repo root. It includes a port of the 44 original automated tests (the original suites stay where they are) plus new tests.

| Folder | Level | What it covers | Needs |
|---|---|---|---|
| `tests-python/unit/` | unit | The suite's own helpers in isolation: data builders, API flows, API clients, config, dev-server helpers, marker mapping (mocks, no I/O) | nothing |
| `tests-python/integration/` | integration | Backend REST API over HTTP: port of the JUnit/MockMvc suite + admin API, order status workflow, delivery price | backend |
| `tests-python/e2e/web/` | e2e | Storefront UI through Playwright (port of `apps/web/e2e/*.spec.ts` + sign-in) | backend + web dev server |
| `tests-python/e2e/admin/` | e2e | Back office UI through Playwright (port of `apps/admin/e2e` + reject / deliver) | backend + admin dev server |

Each test is marked from its folder: `unit`, `integration` (also `api`), `e2e` (also `web` / `admin`).

## Structure (Page Object Model)
`tests-python/` holds only tests. `pytest.ini` sets `testpaths = tests-python` and puts the repo root on
`pythonpath`, so helpers are imported as `from pages.web import ...`, `from clients import FoodMeApi`, `from support.api import ...`.
```
tests-python/
  conftest.py         `api` fixture + folder -> marker mapping
  unit/               unit tests (no backend, no browser)
  integration/        API tests against the running backend
  e2e/web/, e2e/admin/  Playwright UI tests; they only talk to page objects / API clients

<repo root>
  pytest.ini, pyproject.toml, requirements*.txt, .venv/
  clients/            API client objects, one per backend controller, behind the `FoodMeApi` facade
                      (the `api` fixture): api.auth / api.customer / api.chefs / api.dishes / api.orders / api.admin
  pages/base_page.py
  pages/web/          storefront page objects: HomePage, ExplorePage, ChefPage + DishModal, CartPanel,
                      CheckoutPage, LoginPage, OrdersPage, OrderSuccessPage, TrackingPage, OrderFailedPage,
                      shared components Header + CreateAccountForm
  pages/admin/        back-office page objects: AdminLoginPage, Sidebar, OrdersListPage, OrderShowPage,
                      ChefsListPage, DishesListPage
  support/api.py      test-data builders + API flows (register_customer, create_order_via_api, ...)
  support/config.py   URLs / credentials (env overrides)
  support/servers.py  starts the Vite dev servers for e2e when they aren't running
  support/markers.py  folder -> pytest marker mapping (used by conftest.py)
```
Rules for new tests:
- Page objects hold locators and actions; tests hold the business assertions (`expect(...)`).
  Navigation actions return the next page object (`cart.go_to_checkout()` -> `CheckoutPage`).
- No raw selectors or URLs in tests: add a locator or method to the page object instead.
- Locators and waiting follow `.claude/rules/web-testing.md` / `admin-testing.md` (role/label first,
  web-first assertions, never `wait_for_timeout`).

## Setup
```bash
# from the repo root
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt                 # runtime deps + ruff + mypy
playwright install chromium
```

## Lint / static analysis
Config lives in `pyproject.toml` (scoped to `clients/`, `pages/`, `support/`, `tests-python/`). Run from the repo root.
```bash
ruff check .            # lint (pyflakes, bugbear, pytest-style, import order, ...)
ruff format --check .   # formatting
mypy                    # type check clients/, pages/, support/, tests-python/
```

## Run
Run pytest from the repo root with `.venv` activated. A bare `pytest` only picks up `testpaths` from the
repo root; from any other folder, pass the path, e.g. `pytest ../tests-python -m unit`.

Unit tests need nothing else: `pytest -m unit` (under a second).

Integration and e2e tests need Postgres + the backend on `http://localhost:8081` (`cd apps/backend && ./gradlew bootRun`).
The web/admin Vite dev servers (5180 / 5174) are started automatically when not already running
(requires `npm ci` in `apps/web` / `apps/admin`).
```bash
pytest                       # everything
pytest -m unit               # unit tests only (no backend needed)
pytest -m integration        # backend API tests (same as -m api)
pytest -m e2e                # all UI tests (web + admin)
pytest -m web                # storefront UI
pytest -m admin              # back office UI
pytest tests-python/e2e/web/test_layout.py -k mobile
pytest -m web --headed --slowmo 300
```
Env overrides: `VITE_API_BASE_URL`, `PLAYWRIGHT_BASE_URL`, `ADMIN_BASE_URL`.

## Differences from the Java suite
The JUnit tests run in-process on H2 with `data.sql`; these run over HTTP against the live
backend and the Postgres seed (V1–V3), so fixture-specific assertions were rewritten:
- `tests-python/integration/test_chef_api.py`: the chef is looked up through the API instead of asserting chef 1 = `marta-k` and `count == 2`.
- `test_dish_api.py`: no fixed `count == 2` / `"Lavash Wrap"`; FM-FLAKE-03 compares the first dish of `/api/dish/{id}/active` with the chef's menu order instead.
- `test_order_api.py`: FM-FLAKE-02 tests still expect `FM-100001`, so they pass only on a fresh database.

`FM-BUG-NN` / `FM-FLAKE-NN` markers are kept exactly as in the originals (seeded course material).
