---
name: backend-review
description: >-
  Code review for the FoodMe Spring Boot backend (apps/backend). Use when asked to
  review backend changes, a backend PR/branch/commit, Java services, controllers,
  DTOs, JPA entities, repositories, security config, Flyway migrations or JUnit
  tests. Checks correctness, auth rules, migration/entity/test-data consistency,
  FM-BUG/FM-FLAKE course markers, and runs the test suite.
---

# Backend review (FoodMe)

Review only. Report findings and **do not edit files** unless the user asks for fixes.

## 1. Find the scope
- If the user named a PR, branch, commit or path, review that.
- Otherwise use, in order: uncommitted changes (`git diff HEAD -- apps/backend`), then the branch vs `main` (`git diff main...HEAD -- apps/backend`), then the last commit (`git show HEAD -- apps/backend`).
- Say which scope you picked in one line.
- Read every changed file **in full**, plus the callers and callees of changed methods. A diff hunk alone is not enough to judge Spring wiring or JPA behavior.

## 2. Checklist

### Correctness
- [ ] Null handling on `Optional`, lazy relations and request DTO fields. Missing entities should throw `NotFoundException`, invalid input `BadRequestException` (handled by `GlobalExceptionHandler` → `ErrorResponseDto`), never a raw 500.
- [ ] Money and quantity arithmetic: off-by-one at minimums (`minimumOrderCount`), rounding, platform fee / delivery price / `freeDeliveryFrom` thresholds (`>` vs `>=`).
- [ ] Pagination: page/size boundaries, total counts matching the returned items, no item dropped or duplicated on the last page.
- [ ] Filters on `status` (ACTIVE/INACTIVE) for chefs and dishes are applied wherever public endpoints return them.
- [ ] `@Transactional` on multi-step writes, e.g. creating an order with its dishes and additions. No read-then-write races on counters or sequences.
- [ ] `spring.jpa.open-in-view=false`, so lazy collections touched outside a transaction throw `LazyInitializationException`. Check that mapping to DTOs happens inside the service or transaction.
- [ ] N+1 queries in list endpoints (loops calling repositories, or lazy collections inside a stream).

### Security (`SecurityConfig`)
- [ ] New endpoints land under the right prefix. `/api/**` is public by default, except `/api/customer/**` and `POST /api/order`, which need `ROLE_CUSTOMER`. `/admin/**` needs auth, except `/admin/auth/login` and `GET /admin/dish/**`. A new admin-only GET under `/admin/dish/**` would be **public**, so flag it.
- [ ] Customer endpoints act on the **authenticated** customer, not on a customer ID from the request (IDOR).
- [ ] No passwords, tokens or JWTs in logs or responses. New sensitive request fields are redacted by `HttpLoggingFilter`.
- [ ] Validation annotations (`@Valid`, `@NotNull`, `@Email`, sizes) on new request DTOs.

### Database
- [ ] A schema change has all three parts: a **new** `db/migration/V{n+1}__*.sql` (applied migrations never edited), the entity update, and `src/test/resources/data.sql` when tests need it.
- [ ] Entities match the migration exactly (names, types, nullability), because prod runs `ddl-auto=validate`. Tables are qualified `foodme.*`.
- [ ] Migrations inserting explicit IDs advance the sequence with `setval`.
- [ ] Migration SQL is Postgres-valid. The H2 suite will **not** catch broken migrations.

### Cross-cutting
- [ ] New API path prefixes are added to `SpaWebConfig`'s list of paths that never get an SPA shell.
- [ ] New DTOs with image URLs are handled by `ImageUrlResponseAdvice`, and stored paths stay relative (`/api/images/...`).
- [ ] No heavy startup work (Render free tier: 512 MB / 0.1 CPU).

### Tests
- [ ] Changed behavior has a MockMvc test (`@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")`) named `method_condition_expectation`.
- [ ] Tests don't depend on order or global state. The H2 database and the Spring context are shared across the JVM, so tests must create their own customers and orders and assert on them.
- [ ] Error paths are tested: 400 with `$.message`, 401, 404.

### Course markers
- `// FM-BUG-NN` is a seeded bug. If the change touches one without the task naming it, flag it as **scope**. If it fixes one, the marker must stay with `FIX: <reason>`.
- `// FM-FLAKE-NN` tests are intentionally flaky. The same rules apply.
- `SimulatedLatencyConfig`, `FlakyHeartbeatJob`, the hard-coded JWT secret and the open CORS are deliberate. Don't report them as findings.

## 3. Verify
Run `./gradlew test` from `apps/backend` (or `--tests <Class>` for the affected classes) and report the pass/fail counts. If an entity or migration changed and Postgres is available, also run `./gradlew bootRun` until Flyway and Hibernate validation finish, then stop it. If you can't run something, say so.

## 4. Report
Summarize the scope and the test results in one or two lines, then list findings **most severe first**:

```
[severity: high|medium|low] [category] apps/backend/…/File.java:LINE
What is wrong (one sentence).
Failure scenario: concrete input/state → wrong output/crash.
Suggested fix: one or two lines.
```

Only report findings you verified in the code. Put open questions in a separate **Unverified** list. If nothing survived verification, say so plainly. End by offering to apply the fixes.
