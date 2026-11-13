---
paths:
  - "apps/admin/e2e/**"
  - "apps/admin/playwright.config.ts"
---

# Admin e2e testing rules (Playwright)

## Running
```bash
cd apps/admin
npm run test:e2e                                  # chromium, starts `vite --port 5174 --strictPort`
npx playwright test e2e/admin-flows.spec.ts
npx playwright test -g "mark ACCEPTED"
npx playwright show-report
```
- Needs a **running backend + Postgres** at `VITE_API_BASE_URL` (default `http://localhost:8081`). `ADMIN_BASE_URL` points the tests at another admin URL, e.g. `https://<deploy>/backoffice`.
- Tests run **serially** (`fullyParallel: false`) because they share the single seeded admin and its data. Keep it that way. On CI they get 1 retry, and the dev server start timeout is 120 s.

## Auth and navigation
- Log in through the UI with the seeded admin: username `admin`, password `admin123` (bcrypt hash in `V1__init.sql`). Reuse `loginAsAdmin(page)` in a `test.beforeEach`. It waits for the "Orders" menu item, which is the signal that login finished.
- react-admin uses **hash routing**: navigate with `page.goto("/#/orders")`, `"/#/chefs"`, `"/#/dishes"`, `"/#/login"`, and assert URLs with regexes such as `/#\/orders\/\d+\/show/`.

## Test data
- E2E tests run against the **real Postgres seed** (Flyway `V1`–`V3`). Don't hard-code IDs.
- When a test needs an order, create it through the public API with `createOrderViaApi(request)`. It registers a unique customer, picks the first active chef's first dish, and places a `CASH` / `TAKEAWAY` order. Then find that order in the UI by its returned `number` (`FM-…`).
- react-admin lists don't refresh on their own. Click the **Refresh** button after creating data through the API, before asserting that it shows up.
- Never assert totals or row counts across the whole table. Assert on the row the test created, or that "No … found" is absent.

## Writing tests
- Prefer role- and label-based locators: `getByRole("menuitem", …)`, `getByRole("button", { name: "Mark as ACCEPTED" })`, `getByLabel("Username")`. MUI often renders the same text twice (app-bar title + page heading), so make locators strict-mode safe by narrowing with `level`, `.first()`, or a container. See the `Order ${number}` heading with `level: 5`.
- Table rows: `page.locator("table tbody tr")`.
- API latency is 200–1500 ms. Use auto-waiting `expect` assertions, with `{ timeout: 10000–15000 }` for list loads and notifications ("Order status updated"). Never use `waitForTimeout`.
- The admin app is JS, but specs and `playwright.config.ts` are TypeScript. Keep them in TS.

## Seeded course material
`// FM-BUG-NN` markers in the admin source (e.g. FM-BUG-08 in `OrderShow.jsx`) are seeded bugs. A test can expose one, but don't change the app code to make a test pass unless the task names that bug.
