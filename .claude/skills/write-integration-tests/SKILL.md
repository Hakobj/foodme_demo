---
name: write-integration-tests
description: >-
  Write integration tests for the FoodMe backend: MockMvc tests that boot the
  Spring context with H2 (controllers + security + services + JPA together),
  repository tests, and Playwright API-level tests against a running backend
  with the real Postgres seed. Use when asked to test an endpoint, an API
  contract, auth/permissions, validation errors, or DB queries.
---

# Writing integration tests (FoodMe)

An integration test checks several real layers together: HTTP → security → controller → service → JPA → database. Read `.claude/rules/db-testing.md` first; it explains the H2 vs Postgres split and the test fixture.

## 1. Choose the level
| Want to test | Use |
|---|---|
| An endpoint's status, JSON shape, validation, auth rules | **MockMvc** (`@SpringBootTest`, H2) |
| A custom query (`DishSearchRepositoryImpl`, `@Query` methods) | **MockMvc** through the endpoint, or `@DataJpaTest` |
| A Flyway migration, Postgres-only SQL, the real seed data | **Playwright API test** against a running backend, or `./gradlew bootRun` on Postgres |
| A user flow in the browser | not here, use `write-e2e-tests` |

## 2. MockMvc tests (`apps/backend/src/test/java/am/foodme/backend/`)
Follow the existing classes (`OrderControllerTest`, `DishControllerTest`, `ChefControllerTest`, `CustomerAuthControllerTest`). Add to an existing class when the endpoint belongs to it.

```java
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ChefControllerTest {
    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;

    @Test
    void getChef_unknownId_notFound() throws Exception {
        mockMvc.perform(get("/api/chef/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").exists());
    }
}
```

Rules:
- **Customer auth:** register a fresh customer with a unique email and use its token (copy the `customerToken()` pattern from `OrderControllerTest`). `@WithMockUser(roles = "CUSTOMER")` is not enough for endpoints that load the customer from the JWT.
- **Admin auth:** `POST /admin/auth/login` with `admin` / `admin123` (fixture admin `1`) and send `Authorization: Bearer <token>`.
- **Test each endpoint's error paths**, not just 200: 400 + `$.message` (bad input), 401 (no token), 403 (wrong role), 404 (unknown ID). Check `SecurityConfig` for which rule applies.
- **No shared state:** the H2 database and Spring context live for the whole JVM. Create your own customers/orders and assert on them. Never assert global counts or order numbers, and don't add `@Order`/`@TestMethodOrder` (the existing ones are seeded `FM-FLAKE` material).
- Fixture IDs (chefs 1–2 ACTIVE, 3 INACTIVE; dishes 1–3 ACTIVE, 4 INACTIVE) are fine for read-only lookups. Use them to test ACTIVE/INACTIVE filtering.
- Assert the response contract with `jsonPath`: required fields, types, pagination totals matching the returned items.
- For writes, read back through the API (e.g. `GET /api/customer/orders`) to prove persistence.
- Don't enable latency, HTTP logging, Sentry or the flaky heartbeat in tests.

## 3. Repository tests (optional)
`@DataJpaTest @ActiveProfiles("test")` boots only JPA on H2. Use it for tricky queries (search, pagination). Remember H2 in PostgreSQL mode isn't Postgres: `ILIKE`, sequences and native SQL can behave differently, so also cover Postgres-specific queries at the API level (section 4).

## 4. API tests against the real backend (Playwright `request`)
For behavior that depends on Postgres, Flyway or the seed. Put them in `apps/web/e2e/api-*.spec.ts` and use only the `request` fixture (no `page`):

```ts
import { test, expect } from "@playwright/test";
import { registerCustomerViaApi } from "./auth";
const API = process.env.VITE_API_BASE_URL || "http://localhost:8081";

test("order without token is rejected", async ({ request }) => {
  const res = await request.post(`${API}/api/order`, { data: {} });
  expect(res.status()).toBe(401);
});
```
- Discover IDs through the API (`/api/chef/active`, `/api/chef/{id}`), never hard-code them. The seed differs from `data.sql`.
- Needs Postgres + `./gradlew bootRun`. If the backend isn't reachable at `http://localhost:8081`, say so.

## 5. Run and report
- Backend: `cd apps/backend && ./gradlew test --tests <Class>` (add `--rerun-tasks` if it says UP-TO-DATE). Report pass/fail counts.
- API specs: `cd apps/web && npx playwright test e2e/api-<name>.spec.ts`.
- A test that fails because of a seeded `FM-BUG-NN` is a valid finding: report it, don't "fix" the app unless asked.
