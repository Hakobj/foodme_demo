---
paths:
  - "apps/web/e2e/**"
  - "apps/web/playwright.config.ts"
---

# Storefront e2e testing rules (Playwright)

## Running
```bash
cd apps/web
npm run test:e2e                                  # all specs, chromium, starts `vite --port 5180`
npx playwright test e2e/storefront-flows.spec.ts  # one file
npx playwright test -g "cart quantity"            # by test title
npx playwright show-report                        # HTML report (never auto-opens)
```
- Needs a **running backend + Postgres** at `VITE_API_BASE_URL` (default `http://localhost:8081`). The dev server is reused locally if it's already running on 5180. `PLAYWRIGHT_BASE_URL` points the tests at another storefront, e.g. a Render deploy.
- Tests run fully in parallel. On CI they get 2 retries and `forbidOnly`, and traces are recorded on the first retry.

## Test data
- E2E tests run against the **real Postgres seed** (Flyway `V1`–`V3`), not the backend's JUnit `data.sql`. Don't hard-code chef or dish IDs. Navigate to "first chef card / first dish", or look up IDs through the API first (see `happy-path.spec.ts`, which queries `/api/chef/active` and `/api/chef/{id}`).
- Every test that signs up must use a unique email (`Date.now()` + random suffix). Use the helpers in `e2e/auth.ts`:
  - `createAccountAtCheckout(page, name?)` fills the checkout "Create account" tab through the UI.
  - `registerCustomerViaApi(request, apiBase)` returns `{ token, email }`. Use it when the UI sign-up isn't what's being tested.
- Tests share one database and run in parallel, so never assert global counts (number of orders, number of customers). Assert on data the test created itself, e.g. the order number it placed.
- The cart is IndexedDB and holds **one chef at a time**. Each Playwright test gets a fresh browser context, so the cart starts empty.

## Writing tests
- Prefer role- and label-based locators (`getByRole`, `getByLabel`, `getByText`) with the exact English strings from `src/locales/en/translation.json`. Scope to a container when names repeat, e.g. `page.getByRole("form", { name: "Checkout" }).getByLabel("Full name")` or `page.getByRole("banner").getByRole("link", …)`.
- Existing stable CSS hooks used across specs: `a.cc_card` (chef card), `button.dc_card` (dish card), `aside.uc-panel` (cart panel), `.cic_root` (cart line), `.fm-qty-grp p` (quantity). Reuse these rather than inventing new selectors. If you need a new hook, add an accessible name or label in the component.
- The backend adds **200–1500 ms of latency to every API call**. Use web-first assertions (`await expect(locator).toBeVisible()`, `toHaveCount`, `toHaveURL`), which auto-wait. **Never use `page.waitForTimeout`** (that is exactly the seeded flake FM-FLAKE-01). Wait for a UI state before navigating or reloading, e.g. assert the cart line exists before `page.reload()`.
- For slow sections (home "Chefs worth knowing"), pass an explicit `{ timeout: 15000 }` instead of sleeping.
- Factor repeated flows into local helpers (`addFirstDishToCart` in `storefront-flows.spec.ts`) or into `e2e/auth.ts` if more than one spec needs them.

## Seeded course material — do not "fix" unprompted
- `// FM-BUG-NN` comments mark tests that document a seeded app bug. For example, `layout.spec.ts` expects one chef to be missing from the last page of the list (FM-BUG-02), and `storefront-flows.spec.ts` covers FM-BUG-07. Don't change these to match the buggy behavior, and don't delete them.
- `flake-*.spec.ts` and `// FM-FLAKE-NN` comments are intentionally flaky tests for students to diagnose. Only change them when the task names that flake. When you do, leave the marker and add `FIX` with a one-line reason, matching the existing `// FM-FLAKE-05 FIX: …`.
