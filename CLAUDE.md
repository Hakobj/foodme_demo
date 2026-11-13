# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

FoodMe is a food-ordering demo used as a **QA course project**. It is a monorepo deployed to Render's free tier:

- `apps/backend` — Spring Boot 3.3 (Java 17, Gradle), PostgreSQL + Flyway, JWT auth
- `apps/web` — customer storefront: React 19 + TypeScript + Vite + Tailwind
- `apps/admin` — back office: react-admin + MUI (plain JS/JSX)
- `infra/monitoring` — Prometheus + Loki + Grafana + Grafana MCP in one container (see `infra/monitoring/README.md`)
- `tests-python` — Python port of the test suites (pytest + requests + Playwright), tests only: `unit/`, `integration/`, `e2e/`
- `clients/`, `pages/`, `support/` (repo root) — API clients, page objects and helpers for `tests-python`; `pytest.ini`, `pyproject.toml`, `requirements*.txt` and `.venv` are at the repo root too. Run pytest from the repo root (see `TESTING.md`)

App-specific commands, conventions and architecture live in path-scoped rules that load when you work in that app: `.claude/rules/backend.md`, `.claude/rules/web.md`, `.claude/rules/admin.md`. Testing rules: `.claude/rules/web-testing.md`, `.claude/rules/admin-testing.md`, `.claude/rules/db-testing.md`.

Skills live in `.claude/skills/`: code review (`backend-review`, `frontend-review`), test writing (`write-unit-tests`, `write-integration-tests`, `write-e2e-tests`), running tests (`run-tests` for Java/TypeScript, `run-python-tests` for `tests-python/`) and `jira`. `.agents/skills/` and `.agents/rules/` are symlinks to `.claude/skills/` and `.claude/rules/`, so other agents see the same files. Edit them under `.claude/` only.

`AGENTS.md` is a symlink to this file, so other coding agents read the same instructions. Edit `CLAUDE.md` only.

## Seeded bugs — do not "fix" them unprompted

The code contains **intentional bugs** for students to find, marked with `// FM-BUG-NN` comments and tracked in Jira. Some e2e tests assert against them. Only change seeded-bug code when the task is explicitly about that bug. The same goes for tests marked `// FM-FLAKE-NN`; when you do fix one, keep the marker and add `FIX: <reason>`. The simulated API latency, the "flaky heartbeat" fake errors, the hard-coded secrets, open CORS and the open `/mcp` endpoint are also deliberate.

## Single-origin deployment

Production is **one** Docker image (`apps/backend/Dockerfile`, built with the repo root as context). It builds both SPAs and bundles them into the backend's static resources:
- storefront at `/`
- admin UI at `/backoffice`
- `/admin/**` is the admin **REST API**, `/api/**` is the public/customer API

Both frontends call the API same-origin in production and `http://localhost:8081` in dev, unless `VITE_API_BASE_URL` is set. `VITE_*` vars are baked in at build time.

Local full-stack testing: run Postgres (`foodme`/`foodme`/`foodme` on `localhost:5432`), then the backend with `./gradlew bootRun`. The e2e suites in web and admin need that running backend.

## Deployment
- `render.yaml` — app service + free Postgres. The service name is personalized per student (`foodme-<github-username>`). Env: `SENTRY_DSN`, `VITE_SENTRY_DSN_WEB`, `VITE_SENTRY_DSN_ADMIN`, `LOKI_PUSH_URL`.
- `render-monitoring.yaml` — the monitoring stack, configured with `BACKEND_HOST`. All components share one container because Render free services can't receive private-network traffic. Grafana login `admin`/`admin`; Grafana MCP at `/mcp`.
- Error tracking is GlitchTip (Sentry-compatible), one project each for backend/web/admin.

Note: `.env.example` still references `infra/docker-compose.yml` and Jenkins, which no longer exist in the repo.
