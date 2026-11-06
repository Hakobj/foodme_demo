---
name: write-e2e-tests
description: >-
  Write Playwright end-to-end tests for the FoodMe storefront (apps/web/e2e) and
  the admin back office (apps/admin/e2e) that drive a real browser against a
  running backend. Use when asked to add, write or fix e2e/UI tests, cover a user
  flow (explore, cart, checkout, login, orders, admin order management), or turn
  a bug report into a regression test.
---

# Writing e2e tests (FoodMe)

E2E tests drive the real UI in Chromium against a real backend and the Postgres seed. Read `.claude/rules/web-testing.md` (storefront) or `.claude/rules/admin-testing.md` (admin) first; this skill is the workflow on top of those rules.

## 1. Plan the scenario
- Write the flow as user steps + expected results before coding (e.g. *explore → open chef → add dish → increase qty → checkout → order success*).
- Cover what users actually hit: signed-in and signed-out, empty cart, validation errors, `/orders/success` and `/orders/failed`, mobile width for layout bugs.
- Include edge cases, not only the first item: a dish with `minimumOrderCount > 1`, an INACTIVE chef, a second chef (cart `"mismatch"`). Find such data through the API.
- Check the UI by reading the page/component source for roles, labels and translated text (`src/locales/en/translation.json`).

## 2. Where things go
| App | Specs | Port | Helpers |
|---|---|---|---|
| Storefront | `apps/web/e2e/<area>.spec.ts` | 5180 | `e2e/auth.ts`: `createAccountAtCheckout`, `registerCustomerViaApi` |
| Admin | `apps/admin/e2e/<area>.spec.ts` | 5174 | `loginAsAdmin`, `createOrderViaApi` in `admin-flows.spec.ts` |

Add to an existing spec when the flow belongs there. Move a helper into `e2e/auth.ts` (or a new `e2e/helpers.ts`) once two specs need it. Don't name files `flake-*` (those are seeded course material).

## 3. Writing the test
```ts
import { test, expect } from "@playwright/test";
import { registerCustomerViaApi } from "./auth";

const API = process.env.VITE_API_BASE_URL || "http://localhost:8081";

test.describe("Cart", () => {
  test("quantity cannot go below the dish minimum", async ({ page, request }) => {
    // Arrange: find a dish with minimumOrderCount > 1 through the API
    // Act: open its chef page, add to cart, click "Decrease quantity"
    const cart = page.locator("aside.uc-panel");
    await expect(cart.locator(".fm-qty-grp p")).toHaveText(String(min));
    await expect(cart.getByRole("button", { name: "Decrease quantity" })).toBeDisabled();
  });
});
```

Rules:
- **Locators:** `getByRole` / `getByLabel` / `getByText` first. Otherwise the existing CSS hooks: `a.cc_card` (chef card), `button.dc_card` (dish card), `aside.uc-panel` (cart), `.cic_root` (cart item), `.fm-qty-grp p` (quantity). Scope to a container (`cart.getByRole(...)`) so each locator matches exactly one element.
- **Waiting:** web-first assertions only (`toBeVisible`, `toHaveText`, `toHaveCount`, `toHaveURL`). **Never `waitForTimeout`.** The backend adds 200–1500 ms latency, so this matters. Assert a value (`toHaveText(/^\d+$/)`) before reading it with `textContent()`.
- **Data:** unique emails (`Date.now()` + random suffix via the helpers). Set up preconditions through the API (`request`), then test the UI. Never hard-code IDs or rely on counts, the seed and other parallel tests change them.
- **Independence:** web runs `fullyParallel`. Each test creates its own customer and cart. No `test.describe.serial` unless the flow truly is one story.
- **Admin:** hash routes (`/#/orders`), log in with `loginAsAdmin`, click **Refresh** after creating data through the API, then assert.
- **Assertions** state the business result (order number shown, status changed, total equals subtotal + delivery), not only that a page loaded.
- A failing assertion caused by a seeded `FM-BUG-NN` is a valid result. Report it, and don't change app code unless asked. If the test should stay green in CI, mark it `test.fail()` with a comment naming the bug.

## 4. Run and report
Needs Postgres + backend on `http://localhost:8081` (`cd apps/backend && ./gradlew bootRun`). Playwright starts the Vite dev server itself.
```bash
cd apps/web   && npx playwright test e2e/<spec>.spec.ts            # one spec
cd apps/web   && npx playwright test -g "quantity cannot"          # one test
cd apps/web   && npx playwright test e2e/<spec>.spec.ts --repeat-each=5   # flakiness check
cd apps/admin && npx playwright test e2e/<spec>.spec.ts
npx playwright show-report
```
Run new tests at least with `--repeat-each=3` to catch flakiness. Report pass/fail. If the backend isn't running, say so and don't claim the test passes.
