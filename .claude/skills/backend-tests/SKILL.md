---
name: backend-tests
description: Write unit or integration tests for the FoodMe Spring Boot backend (apps/backend) following the repo's existing test style. Use when adding, extending or fixing backend tests, or when a backend change needs test coverage.
---

# Writing backend tests

The existing tests in `apps/backend/src/test/java/am/foodme/backend/` set the standard. Read the closest one before writing a new test:

| Example | Shows |
|---|---|
| `ChefControllerTest` | minimal public GET endpoint test |
| `DishControllerTest` | paging params, asserting on a list DTO |
| `CustomerAuthControllerTest` | JSON bodies via `ObjectMapper` + `Map.of`, unique data per test, error-message assertions, getting a token from the response |
| `OrderControllerTest` | a `customerToken()` helper, payload helper methods, authenticated POST then a follow-up GET |

Tests marked `// FM-FLAKE-nn` are **intentionally flaky** course material. Don't copy their patterns, and don't fix, delete or "stabilise" them unless the user explicitly asks.

## 1. Pick the test type

- **Integration test (default).** Covers any endpoint, security rule, validation, JSON shape, or anything that crosses controller → service → repository. This is what the repo does today.
- **Unit test.** Covers pure logic in a service, mapper or util that you can check without Spring or a database (price math, mapping, branching on input). Use one when the integration setup would hide the case or make it slow to reach.

## 2. Integration tests (house style)

Location and naming:
- `apps/backend/src/test/java/am/foodme/backend/<Controller>Test.java`, in the flat root package like the existing ones.
- One test class per controller. Add to the existing class when one exists.
- Package-private class and methods. Method names follow `action_condition_expectedResult`, e.g. `createOrder_withoutToken_unauthorized`, `register_duplicateEmail_rejected`.

Skeleton:

```java
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class FooControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;   // only if you send JSON or read responses

    @Test
    void getFoo_existingId_returnsFoo() throws Exception {
        mockMvc.perform(get("/api/foo/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1));
    }
}
```

Rules:
- Use literal URL paths (`"/api/order"`), as the existing tests do. A test that pins the path also guards the frozen API contract.
- Build request bodies with `objectMapper.writeValueAsString(Map.of(...))` in a small private helper (`registerPayload(...)`, `cashOrderPayload()`). Don't hand-write JSON strings. The JSON field names must match the API contract exactly (`createOrderDishes`, `dishDtoList`, ...).
- Assert with MockMvc matchers: `status()` first, then `jsonPath(...)`. For values you need later, use `.andReturn().getResponse().getContentAsString()` and `objectMapper.readTree(...)`.
- For errors, assert the status **and** `$.message` (the `GlobalExceptionHandler` body), e.g. `.andExpect(jsonPath("$.message").value("Only CASH payment is supported"))`.
- For each protected endpoint, test both the anonymous case (`isUnauthorized()`) and the authorised happy path.
- Static-import the MockMvc builders and matchers (`get`, `post`, `status`, `jsonPath`) like the existing files.

### Test data

- The `test` profile runs H2 (PostgreSQL mode) with Flyway **off**. The schema comes from the entities (`create-drop`), and seed rows come from `src/test/resources/data.sql`. Latency, the heartbeat, HTTP logging and image seeding are off.
- **Seed data (read-only):** `data.sql` has 3 chefs (1 `marta-k` and 2 `ararat-grill` are ACTIVE, 3 is INACTIVE), dish tags 1–2, and dishes 1–4 (1–3 ACTIVE, 4 INACTIVE; chef 1 owns dishes 1, 2, 4). There is one admin user. Rely on these IDs for reads. Don't mutate seed rows in a test.
- **Data a test creates:** make it unique per test (`"ann-" + UUID.randomUUID() + "@example.com"`) and create it inside the test through the API, as `customerToken()` does.
- **The context is shared.** Every `@SpringBootTest` class with the same config reuses one Spring context and one H2 database, so rows persist across tests and classes. Every test must pass alone, in any order, and in any combination with other tests. Don't use `@TestMethodOrder`/`@Order`. Don't assert on global counts or generated numbers that another test could change. Don't assume list order unless the endpoint documents a sort. Don't compare against the wall clock without tolerance.
- If a test truly needs new seed rows, add them to `data.sql` with IDs that don't collide with existing ones, and check that the other test classes still pass.

### Auth tokens

- **Customer:** register through `/api/auth/register` and read `$.token`. Copy the `customerToken()` helper from `OrderControllerTest` into the new class.
- **Admin:** the seed admin's password isn't documented. Mint a token with the app's own `JwtService`:
  ```java
  @Autowired
  private JwtService jwtService;

  private String adminToken() {
      return jwtService.generateToken("admin", "ADMIN");
  }
  ```
  Send `header("Authorization", "Bearer " + token)`.

## 3. Unit tests

No unit tests exist yet. This is the pattern to use:

- Location mirrors the production package: `src/test/java/am/foodme/backend/service/DishServiceTest.java` for `am.foodme.backend.service.DishService`.
- Plain JUnit 5 + Mockito (`@ExtendWith(MockitoExtension.class)`, `@Mock`, `@InjectMocks`) and AssertJ. All of these come with `spring-boot-starter-test`, so don't add dependencies. No Spring context, no `@ActiveProfiles`.
- Services use constructor injection, so `@InjectMocks` works. You can also construct the service with `new` for clarity.
- Same `action_condition_expectedResult` naming and package-private visibility.
- Mock only collaborators (repositories, other services). Don't mock the class under test or value objects/DTOs. Build entities with setters or constructors.
- Assert on results and thrown exceptions (`assertThatThrownBy(...).isInstanceOf(NotFoundException.class).hasMessage(...)`). Verify interactions only when the interaction *is* the behaviour, like a save or a delete.

See `examples/DishServiceTest.java` in this skill for a complete example.

## 4. What to cover

For each behaviour, cover:
1. the happy path;
2. each validation/`BadRequestException` branch, with its message;
3. not found (404 + message);
4. authorisation: anonymous → 401, wrong role → 403 where relevant;
5. boundaries: minimum order counts, empty lists, paging edges, INACTIVE chefs/dishes being hidden.

Assert on business outcomes (totals, statuses, which items appear), not only on `status().isOk()`.

## 5. Run and verify

From `apps/backend`:

```bash
./gradlew test --tests FooControllerTest                      # one class
./gradlew test --tests 'FooControllerTest.someMethod'         # one method
./gradlew test                                                # full suite: new tests must not break others via shared data
```

- Run a new test at least once on its own and once in the full suite.
- If you're testing a bug fix, confirm the test fails without the fix first.
- An H2 pass doesn't prove Postgres-specific SQL or Flyway migrations work. Say so when a change depends on them.
- If an `FM-FLAKE` test fails in the full run, rerun once and report it. Don't count it against your change.
