---
paths:
  - "apps/backend/**"
---

# Backend rules (Spring Boot 3.3, Java 17, Gradle)

## Commands (run from `apps/backend`)
```bash
./gradlew bootRun                 # :8081, needs Postgres (defaults: localhost:5432, db/user/pass = foodme)
./gradlew test                    # JUnit 5 + MockMvc against H2 (profile "test")
./gradlew test --tests OrderControllerTest
./gradlew test --tests 'OrderControllerTest.someMethod'
./gradlew bootJar
```
Swagger UI: `http://localhost:8081/swagger-ui.html`.

## Database and migrations
- All tables live in the `foodme` schema. Prod uses Flyway + `ddl-auto=validate`, so JPA entities must match the migrations exactly.
- Never edit an existing `db/migration/V{n}__*.sql`; add a new `V{n+1}__*.sql`.
- The test profile (`application-test.properties`) uses H2 in PostgreSQL mode, **disables Flyway**, builds the schema with Hibernate `create-drop`, and loads `src/test/resources/data.sql`. A schema change needs both a new migration **and** matching updates to `data.sql`.
- `DatabaseUrlEnvironmentPostProcessor` (registered in `META-INF/spring.factories`) converts `DATABASE_URL=postgresql://...` (Render/Neon) into JDBC settings. If that isn't set, it uses `SPRING_DATASOURCE_URL`, then `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`.

## Tests
- Controller tests use `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")` and call the API through MockMvc. Follow that pattern rather than mocking services.
- The test profile turns off simulated latency, HTTP logging, image seeding and the flaky heartbeat. Keep it that way so the suite stays fast and deterministic.

## Layout
Package `am.foodme.backend`: `controller/api` (`/api/**`), `controller/admin` (`/admin/**`), `service`, `repository` (custom search in `DishSearchRepositoryImpl`), `model` (JPA + Lombok), `dto`, `exceptionHandler`. Signal errors by throwing `BadRequestException` / `NotFoundException`; `GlobalExceptionHandler` turns them into `ErrorResponseDto`.

## Security (`SecurityConfig`, stateless JWT)
- `/api/auth/**` public; `/api/customer/**` and `POST /api/order` require `ROLE_CUSTOMER`; the rest of `/api/**` is public.
- `/admin/auth/login` public; `GET /admin/dish/**` public; all other `/admin/**` requires auth. Unauthenticated requests get 401.
- `/admin/**` is the admin **REST API**. The admin UI is served at `/backoffice`.

## Cross-cutting behavior
- `SpaWebConfig` serves the bundled storefront at `/` and the admin SPA at `/backoffice`. New API prefixes must be added to its "never serve an SPA shell" list (currently `api/`, `admin/`, `actuator/`, `swagger-ui`, `v3/`).
- Images are stored in Postgres (`foodme.image`), served at `/api/images/**`, and seeded from `src/main/resources/img-seed/` by `ImageSeedRunner`. Store image paths as relative `/api/images/...`; `ImageUrlResponseAdvice` makes them absolute. Add any new DTO that carries image URLs to that advice.
- `HttpLoggingFilter` logs `/api/**` and `/admin/**` requests and responses with secrets redacted. If you add a new sensitive field, add it to the redaction list.
- `logback-spring.xml` writes JSON logs and pushes to Loki only when `LOKI_PUSH_URL` is set. Metrics are at `/actuator/prometheus`, health at `/actuator/health`.
- The JVM flags in the Dockerfile and `server.tomcat.threads.max=32` are tuned for Render's 512 MB / 0.1 CPU instance. Avoid adding heavy startup work.

## Intentional demo behavior — do not "fix" unprompted
- `// FM-BUG-NN` markers (`OrderService`, `ChefService`, `OrderDto`, `CreateOrderDishDto`) are seeded bugs for the QA course. Change them only when the task names that bug.
- `SimulatedLatencyConfig` adds 200–1500 ms of delay to `/api/**` and `/admin/**` (not `/api/images/**`).
- `FlakyHeartbeatJob` reports fake errors to GlitchTip (disabled under the `test` profile).
- The hard-coded JWT secret and internal API key, and the open CORS (`*`), are deliberate.
