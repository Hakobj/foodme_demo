---
name: run-tests
description: >-
  Run FoodMe test cases and report the results: backend JUnit/MockMvc tests
  (apps/backend, Gradle + H2), storefront Playwright e2e (apps/web) and admin
  Playwright e2e (apps/admin). Use when asked to run tests, run a specific test
  or spec, run the whole suite, re-run failures, check for flaky tests, or
  "check that everything passes".
---

# Running tests (FoodMe)

Run what was asked, check the prerequisites first, and report honest results. **Don't change code to make tests pass** unless the user asks; a failure caused by a seeded `FM-BUG-NN` or an `FM-FLAKE-NN` test is an expected result for this course, so report it as such.

## 1. Pick the scope
| User asks for | Run |
|---|---|
| "backend tests", a Java class or method | Backend (section 3) |
| "web", "storefront", a spec in `apps/web/e2e` | Web e2e (section 4) |
| "admin", "back office", `admin-flows.spec.ts` | Admin e2e (section 5) |
| "all tests", "everything" | Backend, then web e2e, then admin e2e |
| "tests for my change" | Map changed files (`git status`, `git diff --name-only`) to the matching suite and specs |

Say which scope you picked in one line.

## 2. Check prerequisites (only for the suites you'll run)
Run these checks and stop with a clear message if one fails. Don't report a suite as passed if it couldn't start.

| Needed for | Check | If missing |
|---|---|---|
| Backend tests | `java -version` reports 17+ | Tell the user to install JDK 17 and set `JAVA_HOME` (`./gradlew` fails with `JAVA_HOME is not set`) |
| e2e (web, admin) | `apps/<app>/node_modules` exists | `npm ci` in that app. Ask first, it downloads packages |
| e2e | Playwright Chromium installed | `npx playwright install chromium`. Ask first |
| e2e | Backend reachable: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/actuator/health` returns `200` | Needs Postgres (`foodme`/`foodme`/`foodme` on `localhost:5432`) + `cd apps/backend && ./gradlew bootRun`. Offer to start it in the background; don't start Postgres yourself |

Backend JUnit tests do **not** need Postgres or a running backend; they use in-memory H2.

## 3. Backend (`apps/backend`)
```bash
cd apps/backend
./gradlew test                                               # whole suite
./gradlew test --tests OrderControllerTest                   # one class
./gradlew test --tests 'OrderControllerTest.createOrder_cashPayment_succeeds'   # one test
./gradlew test --tests '*Controller*'                        # pattern
./gradlew test --rerun-tasks                                 # when Gradle says UP-TO-DATE
```
- Results: `build/test-results/test/*.xml` (parse for counts and failure messages), HTML report at `build/reports/tests/test/index.html`.
- Count tests/failures/skipped from the XML (`<testsuite tests=".." failures=".." errors=".." skipped="..">`), not from memory.

## 4. Storefront e2e (`apps/web`)
Playwright starts the Vite dev server on port 5180 by itself (`reuseExistingServer` locally). It runs fully parallel.
```bash
cd apps/web
npx playwright test                                  # all specs
npx playwright test e2e/storefront-flows.spec.ts     # one spec
npx playwright test -g "cart quantity"               # tests whose title matches
npx playwright test e2e/x.spec.ts:42                 # test at a line
npx playwright test --last-failed                    # only what failed last run
npx playwright test --repeat-each=5 --workers=1      # flakiness check
npx playwright test --reporter=list                  # readable output in the terminal
```
`npm run test:e2e:all` runs web then admin.

## 5. Admin e2e (`apps/admin`)
Dev server on port 5174 (`--strictPort`, so a busy port fails the run), serial (`fullyParallel: false`). Logs in as `admin` / `admin123`.
```bash
cd apps/admin
npx playwright test
npx playwright test -g "order status"
```
Set `ADMIN_BASE_URL` / `PLAYWRIGHT_BASE_URL` / `VITE_API_BASE_URL` only when testing against another environment (e.g. the Render deploy).

## 6. Investigate failures (read-only)
For each failure:
- Show the test name, file:line and the assertion message (expected vs received).
- e2e: look at `test-results/<test>/error-context.md` and screenshots if present; for a trace, re-run that one test with `--trace on` and tell the user `npx playwright show-trace <path>` / `npx playwright show-report`.
- Classify it:
  - **Seeded bug:** the failing code or test has an `FM-BUG-NN` marker (or the behavior matches one in `CLAUDE.md`).
  - **Seeded flake:** `FM-FLAKE-NN` test, or `flake-*.spec.ts`. Confirm by re-running it with `--repeat-each`.
  - **Environment:** backend down, port busy, missing browser, timeouts on cold start (the backend adds 200–1500 ms latency).
  - **Real regression:** none of the above. Point to the likely cause in the code.
- Re-run a failure once before calling it flaky, and say that you did.

## 7. Report
```
Backend:  42 passed, 1 failed, 0 skipped   (./gradlew test, 38s)
Web e2e:  18 passed, 2 failed               (npx playwright test)
Admin e2e: not run - backend not reachable on :8081

Failures
- OrderControllerTest.listOrders_secondPage_returnsRest  [seeded flake FM-FLAKE-02]
  expected 2 but was 3 (OrderControllerTest.java:140)
- storefront-flows › cart quantity decrease  [real regression?]
  ...
```
List the exact commands you ran. Don't leave a backend you started running without telling the user (give its PID or stop it if they ask). End by offering next steps: re-run, open the report, or investigate/fix a specific failure.
