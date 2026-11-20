---
paths:
  - "apps/backend/src/test/**"
  - "apps/backend/src/main/resources/db/**"
  - "apps/backend/src/main/resources/application-test.properties"
  - "apps/backend/src/main/java/am/foodme/backend/model/**"
  - "apps/backend/src/main/java/am/foodme/backend/repository/**"
---

# Backend & database testing rules (JUnit 5, MockMvc, H2, Flyway)

## Running
```bash
cd apps/backend
./gradlew test                                            # whole suite
./gradlew test --tests OrderControllerTest                # one class
./gradlew test --tests 'OrderControllerTest.createOrder_cashPayment_succeeds'
./gradlew test --rerun-tasks                              # force a rerun when Gradle says UP-TO-DATE
```
Reports are in `build/reports/tests/test/index.html`.

## Two different databases — know which one you're testing
| | JUnit suite (`test` profile) | Running app / e2e |
|---|---|---|
| Engine | H2 in-memory, `MODE=PostgreSQL` | PostgreSQL |
| Schema | Hibernate `create-drop` from the JPA entities | Flyway `db/migration/V*.sql`, then `ddl-auto=validate` |
| Data | `src/test/resources/data.sql` (tiny) | Seed rows inside `V1`–`V3` migrations |

Consequences:
- **The JUnit suite never runs the Flyway migrations.** A green `./gradlew test` doesn't prove a migration is correct. After adding or changing a migration or an entity, also start the app against a real Postgres (`./gradlew bootRun`). Flyway applies the migrations, then Hibernate `validate` fails startup if the entities and the schema disagree.
- A schema change needs **three** edits: a new `V{n+1}__*.sql` migration (never edit an applied one), the JPA entity, and `data.sql` if the new columns are `NOT NULL` or the tests need rows.
- Keep `data.sql` SQL portable between H2 (PostgreSQL mode) and Postgres. Sequences `data.sql` relies on are created there explicitly (e.g. `foodme.order_number_seq`).
- Migrations that insert rows with explicit IDs must advance the matching sequence (`SELECT setval('foodme.<table>_id_seq', …)`, as `V1` does). Otherwise later inserts collide.
- Everything lives in the `foodme` schema. Qualify table names (`foodme.dish`) in SQL.

## Test fixture (`data.sql`)
- Chefs: `1` Marta's Kitchen (ACTIVE), `2` Ararat Grill House (ACTIVE), `3` Old Yerevan Kitchen (**INACTIVE**).
- Dishes: `1` Lavash Wrap, `2` Khashlama (chef 1), `3` Pork Khorovats (chef 2), all ACTIVE. `4` Inactive Dish (chef 1, **INACTIVE**).
- Dish tags `1` Starters, `2` Mains. Admin `1` = `admin`.
- These IDs exist only in the JUnit fixture. Don't copy them into Playwright tests, which run against the Postgres seed.
- Add a fixture row to `data.sql` only when a test can't build what it needs through the API. Prefer creating customers and orders through endpoints inside the test.

## Writing tests
- Follow the existing style: `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")`, inject `MockMvc` + `ObjectMapper`, and drive the HTTP API with `jsonPath` assertions. Test names are `method_condition_expectation` (e.g. `createOrder_withoutToken_unauthorized`).
- To get a customer token, call `POST /api/auth/register` with a unique email (`UUID` / counter) and read `token` from the response (see `customerToken()` in `OrderControllerTest`).
- **State leaks between tests and between classes.** The Spring context is cached and the H2 database (`DB_CLOSE_DELAY=-1`) lives for the whole JVM, so anything a test writes is visible to later tests. Don't rely on test order (`@Order`) or global values such as "the first order number is FM-100001". Assert on data the test created, and scope counts to a fresh customer.
- Assert error responses through `GlobalExceptionHandler`'s shape: `status().isBadRequest()` + `jsonPath("$.message")`.
- The test profile disables latency, HTTP logging, image seeding, Sentry and the flaky heartbeat. Don't turn them on in tests.

## Seeded course material — do not "fix" unprompted
- `// FM-FLAKE-NN` (e.g. FM-FLAKE-02 / -03 / -04 in `OrderControllerTest` and `DishControllerTest`) marks intentionally flaky or order-dependent tests for students to diagnose. Change them only when the task names that flake, and keep the marker (add `FIX: <reason>`).
- `// FM-BUG-NN` in `src/main` marks seeded app bugs. A new test may expose one, but don't change the production code to make it pass unless the task names that bug.
