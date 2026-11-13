---
name: write-unit-tests
description: >-
  Write unit tests for FoodMe: backend services and helpers in apps/backend
  (JUnit 5 + Mockito + AssertJ, no Spring context) and pure frontend logic in
  apps/web (utils, zod schemas, cart functions). Use when asked to add, write or
  improve unit tests, test a single class/function in isolation, or raise
  coverage of service logic.
---

# Writing unit tests (FoodMe)

A unit test checks one class or function in isolation: no Spring context, no database, no HTTP, no browser. It runs in milliseconds. If the test needs `MockMvc`, a real database or a running backend, use `write-integration-tests` or `write-e2e-tests` instead.

## 1. Pick the target
- Read the code under test **in full**, plus its collaborators' signatures.
- List the behaviors before writing code: happy path, each branch, boundaries (`minimumOrderCount`, 0/1/negative quantities, `freeDeliveryFrom` `>` vs `>=`), nulls/empty lists, and thrown exceptions (`NotFoundException`, `BadRequestException`).
- If the code has a `// FM-BUG-NN` marker, a test may **expose** that bug, but don't change production code to make it pass unless the task names that bug. Say in the test name or comment which bug it exposes.

## 2. Backend (`apps/backend`)
Already available through `spring-boot-starter-test`: JUnit 5, Mockito, AssertJ. No dependency changes are needed.

- Location mirrors the main package: `src/test/java/am/foodme/backend/service/OrderServiceTest.java`.
- Good targets: `service/*Service.java` (pricing, order creation, status changes, pagination math), `security/JwtService`, `exceptionHandler/GlobalExceptionHandler`, `config/DatabaseUrlEnvironmentPostProcessor`.
- Services use constructor injection (`private final` fields). Build them with mocks, no `@SpringBootTest`:

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
    @Mock OrderRepository orderRepository;
    @Mock ChefRepository chefRepository;
    @Mock DishRepository dishRepository;
    @Mock CustomerRepository customerRepository;
    MeterRegistry meterRegistry = new SimpleMeterRegistry();   // real, not mocked
    OrderService service;

    @BeforeEach
    void setUp() {
        service = new OrderService(orderRepository, chefRepository, dishRepository,
                customerRepository, meterRegistry);
    }

    @Test
    void createOrder_unknownChef_throwsNotFound() {
        when(chefRepository.findById(99L)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.createOrder(orderDto(99L), "ann@example.com"))
                .isInstanceOf(NotFoundException.class);
    }
}
```
  (Check the real constructor and method signatures before copying this.)
- Build entities and DTOs with small private factory methods in the test (`chef()`, `dish(price, min)`). Don't load `data.sql` IDs.
- Use `ArgumentCaptor` to assert what was passed to `save(...)` (totals, status, number), not only the return value.
- Money: assert exact values with `isEqualByComparingTo` for `BigDecimal`, `isEqualTo` for integers.
- Don't mock what you own and is pure (DTO mappers, value objects); mock repositories and external services only.
- Naming: `method_condition_expectation` (same as the rest of the suite).
- Run: `cd apps/backend && ./gradlew test --tests OrderServiceTest`.

## 3. Frontend (`apps/web`, `apps/admin`)
**Neither app has a unit-test runner today** (only Playwright). Adding one is a dependency change, so **ask the user first**. The recommended setup for `apps/web`:

- `npm i -D vitest fake-indexeddb` (+ `@testing-library/react jsdom` only if testing components or hooks).
- `package.json` script: `"test": "vitest run"`. Vitest reuses `vite.config.ts`; set `test: { environment: "node" }` (or `"jsdom"` for components) and `include: ["src/**/*.test.ts?(x)"]` so it never picks up `e2e/*.spec.ts`.
- Put tests next to the code: `src/lib/utils.test.ts`.

Good targets, most valuable first:
- `src/hooks/useCart.ts` exported functions (`addDishToCart`, `incrementCartItem`, `decrementCartItem`, `removeCartItem`, `clearCart`, `getCartChefId`): import `fake-indexeddb/auto` at the top of the test, `await db.delete(); await db.open()` in `beforeEach`. Cover: one-chef-per-cart `"mismatch"`, `replaceOtherChef`, decrement never below `Math.max(minimumOrderCount, 1)`, `uid` built from sorted addition IDs.
- `src/schemas/*.ts` (zod): `safeParse` valid and invalid inputs, assert the error path and message key.
- `src/lib/utils.ts`: `formatAmd`, `translate` (missing language, `undefined` list), `sameLabel`.

Admin (`apps/admin`) is plain JS: unit tests would be `*.test.js` with the same Vitest setup. `dataProvider.js` is the most useful target (mock `api` from `base-api.js`).

## 4. Quality bar
- One behavior per test, Arrange / Act / Assert visible. No logic (loops/ifs) in tests.
- Deterministic: no real time, randomness or network. Inject or fake them.
- Every assertion would fail if the behavior broke (check by mentally flipping `<` to `<=`).
- Run the new tests, report pass/fail, and show the command used. If something can't run (e.g. no JDK: `JAVA_HOME is not set`), say so instead of claiming it passes.
