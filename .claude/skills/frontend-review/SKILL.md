---
name: frontend-review
description: >-
  Code review for the FoodMe frontends: the storefront (apps/web, React 19 + TS +
  Tailwind 4) and the admin back office (apps/admin, react-admin + MUI, JS).
  Use when asked to review frontend/UI changes, components, pages, hooks, cart
  logic, forms, API clients, Tailwind/CSS, or Playwright e2e specs. Checks
  correctness, state/cart logic, API usage, i18n, layout traps, test quality and
  FM-BUG/FM-FLAKE course markers; runs build, lint and e2e.
---

# Frontend review (FoodMe)

Review only. Report findings and **do not edit files** unless the user asks for fixes.

## 1. Find the scope
- If the user named a PR, branch, commit or path, review that.
- Otherwise use, in order: uncommitted changes (`git diff HEAD -- apps/web apps/admin`), then the branch vs `main`, then the last commit (`git show HEAD -- apps/web apps/admin`).
- Say which scope and which app(s) you picked.
- Read every changed file **in full**, plus the components and hooks that use the changed code.

## 2. Checklist — both apps
- [ ] **API calls** go through the shared client: web uses `src/api/foodme.ts` → `apiClient` (`src/api/client.ts`); admin uses `src/api/*-api.js` → `api` in `base-api.js`, which prefixes paths with `/admin`. Flag direct `fetch`/`axios` calls, hard-coded hosts and duplicated base-URL logic.
- [ ] **Loading, error and empty states** exist for every request. The backend adds 200–1500 ms of latency, so missing spinners and double submits are real bugs. Submit buttons are disabled while pending.
- [ ] **Auth:** a 401 clears the token (web: `/api/customer/*` → `clearStoredAuth`; admin: `localStorage.token` → redirect to `BASE_URL + login`). No tokens in logs or URLs.
- [ ] **Base paths:** admin in-app links and redirects are built from `import.meta.env.BASE_URL`, because production serves it at `/backoffice/` and `/admin/**` is the API. `VITE_*` values are build-time only.
- [ ] **Course markers:** `// FM-BUG-NN` / `// FM-FLAKE-NN` are seeded course material. If a change touches one that the task didn't name, flag it as **scope**. A fix must keep the marker with `FIX: <reason>`. `flakyHeartbeat` is deliberate, so don't report it.

## 3. Checklist — storefront (`apps/web`)
- [ ] **Cart (`src/hooks/useCart.ts`, Dexie):** one chef per cart (`"mismatch"` unless `replaceOtherChef`). Quantities never go below `Math.max(minimumOrderCount, 1)`. Check deletion thresholds for off-by-one (`<` vs `<=`). Read-then-write updates on the same row run in `db.transaction("rw", …)` or `modify()`, otherwise rapid clicks race. `uid` = `chefId-dishId-sortedAdditionIds`.
- [ ] **Prices:** subtotal, additions, delivery fee and the free-delivery threshold agree with what the backend computes. Number formatting is consistent.
- [ ] **Server state** uses TanStack Query (sensible query keys, invalidation after mutations), not ad-hoc `useEffect` fetching.
- [ ] **Forms** use react-hook-form + zod schemas in `src/schemas/`. Validation messages are shown, fields have labels.
- [ ] **i18n:** user-facing strings come from `src/locales/en/translation.json`. No hard-coded English in JSX.
- [ ] **Types:** no `any` or non-null `!` that hides a real null. Shared types live in `src/types/index.ts`. `npm run build` (`tsc -b`) must pass.
- [ ] **Accessibility:** buttons and inputs have accessible names (e2e tests depend on them).
- [ ] **Tailwind traps (verified in this repo):**
  - `tailwind.config.js` **replaces** `theme.spacing` with a fixed pixel scale. Classes whose key isn't on that scale (e.g. `px-3.5`, `gap-1.5`, `p-0.5`) compile to **nothing**. Check each new spacing class against the config.
  - The `Button` primitive is `inline-flex whitespace-nowrap`: it won't wrap. A row of buttons inside `.bezel-inner` / `overflow-hidden` (checkout summary, price summary, delivery form) clips. Do the math: inner width = `min(viewport, max-w-*)` − padding − border.
  - `sm:`/`md:` are viewport breakpoints, not container widths.
- [ ] **States:** signed-in and signed-out, empty cart, `/orders/success`, `/orders/failed`, loading, error. Not just the happy path.

## 4. Checklist — admin (`apps/admin`)
- [ ] Plain JS/JSX only. No TS files.
- [ ] react-admin wiring: `dataProvider.js` maps resources correctly (list `total`, `id` field, sorting/pagination params). `authProvider.js` handles `checkError` for 401/403.
- [ ] Order status values match `src/constants/OrderStatus.jsx` and the backend enum. Status transitions only offer valid next states.
- [ ] Notifications on success and failure for mutations. Lists refresh after changes.
- [ ] `npm run lint` (eslint) passes.

## 5. Checklist — e2e specs (if changed)
- [ ] Role- and label-based locators, or the existing CSS hooks (`a.cc_card`, `button.dc_card`, `aside.uc-panel`, `.cic_root`, `.fm-qty-grp p`). Locators must match exactly one element (strict mode).
- [ ] **No `waitForTimeout`.** Use web-first `expect` assertions. Values read with `textContent()` are first asserted (e.g. `toHaveText(/^\d+$/)`).
- [ ] Unique test data (`Date.now()` + random suffix, the helpers in `e2e/auth.ts`). No hard-coded IDs. No global counts. Tests are independent of each other.
- [ ] Edge cases are covered, not only the first item (e.g. a dish with `minimumOrderCount > 1`, found through the API).
- [ ] Admin: hash routes (`/#/orders`), `loginAsAdmin`, click **Refresh** after creating data through the API.

## 6. Verify
Run what applies and report the results:
- web: `npm run build` and `npm run lint` in `apps/web`
- admin: `npm run build` and `npm run lint` in `apps/admin`
- If e2e specs or user flows changed and the backend is reachable at `http://localhost:8081`, run the affected specs, e.g. `npx playwright test e2e/<spec>.ts`.
- For layout or CSS changes, offer to open the page in a browser at desktop width and at ~375 px (a source read plus green tests is not a visual review).

If a step can't run (no backend, no node_modules), say so instead of skipping it silently.

## 7. Report
Summarize the scope and the verification results in one or two lines, then list findings **most severe first**:

```
[severity: high|medium|low] [category] apps/web/src/…/file.tsx:LINE
What is wrong (one sentence).
Failure scenario: concrete user action/state → wrong result.
Suggested fix: one or two lines.
```

Only report findings you verified in the code. Put open questions in a separate **Unverified** list. If nothing survived verification, say so plainly. End by offering to apply the fixes.
