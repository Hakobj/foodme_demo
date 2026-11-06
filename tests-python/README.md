# FoodMe tests in Python (pytest + Playwright)

Python port of all 44 automated tests. The original suites stay where they are.

| Folder | Port of | Tests |
|---|---|---|
| `tests/api/` | `apps/backend/src/test/java/**` (JUnit + MockMvc) | 15 |
| `tests/web/` | `apps/web/e2e/*.spec.ts` | 22 |
| `tests/admin/` | `apps/admin/e2e/admin-flows.spec.ts` | 7 |

## Structure (Page Object Model)
```
clients/          API client objects, one per backend controller, behind the `FoodMeApi` facade
                  (the `api` fixture): api.auth / api.customer / api.chefs / api.dishes / api.orders / api.admin
pages/base_page.py
pages/web/        storefront page objects: HomePage, ExplorePage, ChefPage + DishModal, CartPanel,
                  CheckoutPage, LoginPage, OrdersPage, OrderSuccessPage, TrackingPage, OrderFailedPage,
                  shared components Header + CreateAccountForm
pages/admin/      back-office page objects: AdminLoginPage, Sidebar, OrdersListPage, OrderShowPage,
                  ChefsListPage, DishesListPage
support/api.py    test-data builders + API flows (register_customer, create_order_via_api, ...)
tests/            the tests; they only talk to page objects / API clients
```
Rules for new tests:
- Page objects hold locators and actions; tests hold the business assertions (`expect(...)`).
  Navigation actions return the next page object (`cart.go_to_checkout()` -> `CheckoutPage`).
- No raw selectors or URLs in tests: add a locator or method to the page object instead.
- Locators and waiting follow `.claude/rules/web-testing.md` / `admin-testing.md` (role/label first,
  web-first assertions, never `wait_for_timeout`).

## Setup
```bash
cd tests-python
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt                 # runtime deps + ruff + mypy
playwright install chromium
```

## Lint / static analysis
Config lives in `pyproject.toml`.
```bash
ruff check .            # lint (pyflakes, bugbear, pytest-style, import order, ...)
ruff format --check .   # formatting
mypy                    # type check clients/, pages/, support/, tests/
```

## Run
Needs Postgres + the backend on `http://localhost:8081` (`cd apps/backend && ./gradlew bootRun`).
The web/admin Vite dev servers (5180 / 5174) are started automatically when not already running
(requires `npm ci` in `apps/web` / `apps/admin`).
```bash
pytest                       # everything
pytest -m api                # backend API tests only
pytest -m web                # storefront UI
pytest -m admin              # back office UI
pytest tests/web/test_layout.py -k mobile
pytest -m web --headed --slowmo 300
```
Env overrides: `VITE_API_BASE_URL`, `PLAYWRIGHT_BASE_URL`, `ADMIN_BASE_URL`.

## Differences from the Java suite
The JUnit tests run in-process on H2 with `data.sql`; these run over HTTP against the live
backend and the Postgres seed (V1–V3), so fixture-specific assertions were rewritten:
- `test_chef_api.py`: the chef is looked up through the API instead of asserting chef 1 = `marta-k` and `count == 2`.
- `test_dish_api.py`: no fixed `count == 2` / `"Lavash Wrap"`; FM-FLAKE-03 compares the first dish of `/api/dish/{id}/active` with the chef's menu order instead.
- `test_order_api.py`: FM-FLAKE-02 tests still expect `FM-100001`, so they pass only on a fresh database.

`FM-BUG-NN` / `FM-FLAKE-NN` markers are kept exactly as in the originals (seeded course material).
