---
paths:
  - "apps/web/**"
---

# Storefront rules (React 19 + TypeScript + Vite 8 + Tailwind 4)

## Commands (run from `apps/web`)
```bash
npm ci
npm run dev                       # Vite dev server; API defaults to http://localhost:8081
npm run build                     # tsc -b && vite build (type errors fail the build)
npm run lint                      # oxlint
npm run test:e2e                  # Playwright (chromium), auto-starts dev server on :5180
npx playwright test e2e/happy-path.spec.ts
npx playwright test -g "test name"
npm run test:e2e:all              # web e2e, then admin e2e
```
- E2E tests hit a **real backend** (`VITE_API_BASE_URL`, default `http://localhost:8081`), so the backend and Postgres must be running. `PLAYWRIGHT_BASE_URL` overrides the storefront URL.
- Shared e2e helpers (creating an account at checkout, registering a customer via the API) are in `e2e/auth.ts`. Reuse them, and keep emails unique with timestamp + random suffixes as they do.

## Conventions
- Use the `@/` import alias for `src/`.
- UI primitives in `src/components/ui` are shadcn-style (`components.json`, Radix + `class-variance-authority` + `cn()` from `lib/utils`). Page-level pieces go in `src/components/sections`, pages in `src/pages/<Name>/index.tsx`, routes in `src/router.tsx`.
- Server data goes through TanStack Query, using `src/api/foodme.ts` built on `apiClient` in `src/api/client.ts`. Don't call `fetch` directly.
- Forms use react-hook-form + zod schemas in `src/schemas/`.
- User-facing strings go through i18next (`src/locales/en/translation.json`).
- Shared types live in `src/types/index.ts`.

## API base URL
`client.ts` resolves the API base like this: an explicit `VITE_API_BASE_URL` wins; otherwise `http://localhost:8081` in dev and `""` (same-origin relative) in production, because the backend serves this SPA at `/`. A bare host gets `https://` prepended. `VITE_*` vars (including `VITE_SENTRY_DSN`) are baked in at build time.

## State
- The cart lives in IndexedDB via Dexie (`src/lib/db.ts`, `src/hooks/useCart.ts`). A cart holds dishes from **one chef only**: `addDishToCart` returns `"mismatch"` unless `replaceOtherChef` is passed. Quantities respect `dish.minimumOrderCount`. A cart line's `uid` is `chefId-dishId-sortedAdditionIds`.
- The customer auth token is stored via `src/lib/auth-storage.ts`. A 401 on `/api/customer/*` clears it.

## Intentional demo behavior — do not "fix" unprompted
- `src/lib/flakyHeartbeat.ts` reports a fake error to GlitchTip about one minute in ten.
- Some e2e tests assert seeded-bug behavior marked `FM-BUG-NN` (e.g. `layout.spec.ts` expects FM-BUG-02, `storefront-flows.spec.ts` covers FM-BUG-07). `flake-*.spec.ts` files are flaky on purpose, as course material.
- Expect API calls to be slow (200–1500 ms of simulated latency). Rely on Playwright's auto-waiting assertions, never on fixed sleeps.
