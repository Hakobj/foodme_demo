"""Selection policy. Patterns are fnmatch globs on repo-relative POSIX paths (`*` also matches `/`).

The order of the checks in selector.py is: RUN_ALL -> IGNORE -> changed test files -> impact map ->
backend endpoint mapping -> FALLBACK_SUITES -> unknown file (run all). When unsure, run more.
"""

E2E_ROOT = "tests-python/e2e/"

# Files nothing in the e2e run depends on.
IGNORE = [
    "*.md",
    "*.patch",
    "agentic-workflows/*",
    ".claude",  # the symlinks themselves
    ".agents",
    ".claude/*",
    ".agents/*",
    ".agent/*",
    "workflows/*",  # agent tooling (status line)
    "ci/*",  # scripts of the triage workflow; the e2e run never imports them
    ".agentsecrets/*",
    ".playwright-mcp/*",
    "jira/*",
    "infra/*",
    "docs/*",
    ".mcp.json",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "qodana.yaml",
    "render*.yaml",  # deployment config
    "apps/backend/qodana.yaml",
    "apps/*/Dockerfile",
    "apps/*/nginx.conf",
    "apps/*/vercel.json",
    "apps/*/.env.example",
    "apps/*/.gitignore",
    "apps/*/.prettierrc.json",
    "apps/*/eslint.config.js",
    "apps/web/.oxlintrc.json",
    "apps/web/components.json",
    "apps/*/e2e/*",  # the TypeScript Playwright suites run on their own
    "apps/*/playwright.config.ts",
    "apps/backend/src/test/*",
    "tests-python/unit/*",
    "tests-python/integration/*",
    "selection/impact-map.json",  # data, refreshed by the nightly job
    ".github/workflows/*",  # except the ones listed in RUN_ALL
    "pyproject.toml",  # lint / type-check config only
]

# Files that can change the behaviour of any e2e test.
RUN_ALL = [
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/vite.config.*",
    "apps/web/tsconfig*.json",
    "apps/web/index.html",
    "apps/web/tailwind.config.js",
    "apps/admin/package.json",
    "apps/admin/package-lock.json",
    "apps/admin/vite.config.*",
    "apps/admin/index.html",
    "pytest.ini",
    "requirements*.txt",
    "tests-python/conftest.py",
    "tests-python/e2e/conftest.py",
    "support/config.py",
    "support/servers.py",
    "pages/base_page.py",
    "selection/*.py",
    ".github/workflows/selective-e2e.yml",
    # cross-cutting backend code: every endpoint goes through it
    "apps/backend/build.gradle",
    "apps/backend/settings.gradle",
    "apps/backend/gradle/*",
    "apps/backend/gradlew*",
    "apps/backend/src/main/resources/*",
    "apps/backend/src/main/java/am/foodme/backend/config/*",
    "apps/backend/src/main/java/am/foodme/backend/security/*",
    "apps/backend/src/main/java/am/foodme/backend/exceptionHandler/*",
    "apps/backend/src/main/java/am/foodme/backend/BackendApplication.java",
]

# Files that affect a whole suite, checked BEFORE the impact map: session fixtures (base_url, dev
# server) run once per session, so the map only attributes them to the first test that ran.
SUITE_FILES = [
    ("tests-python/e2e/web/conftest.py", "tests-python/e2e/web/"),
    ("tests-python/e2e/admin/conftest.py", "tests-python/e2e/admin/"),
    ("apps/web/src/main.tsx", "tests-python/e2e/web/"),
    ("apps/admin/src/main.jsx", "tests-python/e2e/admin/"),
]

# A changed file that matches here but has no entry in the impact map (e.g. a new module, or code
# no recorded test executed) selects the whole suite on the right. First match wins.
FALLBACK_SUITES = [
    ("tests-python/e2e/web/*", "tests-python/e2e/web/"),
    ("tests-python/e2e/admin/*", "tests-python/e2e/admin/"),
    ("apps/web/*", "tests-python/e2e/web/"),
    ("pages/web/*", "tests-python/e2e/web/"),
    ("apps/admin/*", "tests-python/e2e/admin/"),
    ("pages/admin/*", "tests-python/e2e/admin/"),
    ("support/*", E2E_ROOT),
    ("clients/*", E2E_ROOT),
    ("pages/*", E2E_ROOT),
]

# Backend Java files with no path to a controller (scheduled jobs, unused helpers) have no e2e impact.
BACKEND_SRC = "apps/backend/src/main/java/"

# Smoke tests that run on every change, whatever was selected (one per app).
ALWAYS = [
    "tests-python/e2e/web/test_happy_path.py::test_explore_chef_add_2_dishes_cart_total_cash_checkout_success",
    "tests-python/e2e/admin/test_admin_flows.py::TestAdminAuth::test_logs_in_with_seeded_credentials",
]

# The map is rebuilt nightly. Older than this, the selection still runs but warns.
MAP_MAX_AGE_DAYS = 7
