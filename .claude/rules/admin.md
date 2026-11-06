---
paths:
  - "apps/admin/**"
---

# Admin back-office rules (react-admin 5 + MUI, React 18, plain JS/JSX)

## Commands (run from `apps/admin`)
```bash
npm ci
npm run dev                       # Vite dev server at root "/"; API defaults to http://localhost:8081
npm run build                     # vite build (production base = /backoffice/)
npm run lint                      # eslint
npm run test:e2e                  # Playwright (chromium), auto-starts dev server on :5174 (strict port)
npx playwright test e2e/admin-flows.spec.ts
npx playwright test -g "test name"
```
- E2E tests hit a **real backend** (`VITE_API_BASE_URL`, default `http://localhost:8081`), so the backend and Postgres must be running. `ADMIN_BASE_URL` overrides the admin URL. Tests run **serially** (`fullyParallel: false`).
- The seeded admin account is the `admin` user in `V1__init.sql`.

## Conventions
- This app is JavaScript/JSX, not TypeScript. Don't add TS files or type annotations.
- All HTTP goes through `src/api/base-api.js`: the `api` helper prefixes every path with `/admin`, attaches `Authorization: Bearer <localStorage.token>`, and unwraps `response.data`. Resource-specific calls are in `src/api/*-api.js`.
- react-admin wiring: `src/providers/dataProvider.js` and `src/providers/authProvider.js`. Pages are in `src/pages/<resource>/` (`*List`, `*Edit`, `*Show`), and routes are guarded by `src/security/ProtectedRoute.jsx` / `GuestRoute.jsx`.
- Order status values are in `src/constants/OrderStatus.jsx`. Keep them in sync with the backend.

## Routing and base path
- In production the backend serves this SPA at `/backoffice` (Vite `base` is `/backoffice/` only in production mode). `/admin/**` on the backend is the REST API, not this UI.
- Build in-app paths from `import.meta.env.BASE_URL` (as `LOGIN_PATH` in `base-api.js` does), never as hard-coded `/` paths. On 401 the client clears the token and redirects to the login path.
- API base: an explicit `VITE_API_BASE_URL` wins; otherwise `http://localhost:8081` in dev and `""` (same origin) in production. `VITE_*` vars are baked in at build time.

## Intentional demo behavior — do not "fix" unprompted
- `// FM-BUG-NN` markers (e.g. FM-BUG-08 in `src/pages/orders/OrderShow.jsx`) are seeded bugs for the QA course. Change them only when the task names that bug.
- `src/lib/flakyHeartbeat.js` reports fake errors to GlitchTip.
- API calls have 200–1500 ms of simulated latency. Use auto-waiting assertions in tests.
