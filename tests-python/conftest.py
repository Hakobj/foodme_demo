import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from clients import FoodMeApi
from support.config import API_BASE_URL
from support.markers import suite_markers
from support.servers import is_up


def _backend_required() -> bool:
    """True when a missing backend must fail the run instead of skipping it.

    Defaults to on in CI (`CI=true`, set by GitHub Actions) so an integration job without a
    backend goes red instead of passing with every test skipped. Override with REQUIRE_BACKEND=0/1.
    """
    value = os.environ.get("REQUIRE_BACKEND", os.environ.get("CI", ""))
    return value.strip().lower() in {"1", "true", "yes"}


@pytest.fixture(scope="session")
def api() -> Iterator[FoodMeApi]:
    """API client objects for the backend.

    Locally, skips cleanly when the backend is down; in CI (or with REQUIRE_BACKEND=1) it fails.
    """
    if not is_up(f"{API_BASE_URL}/actuator/health"):
        reason = f"backend not reachable at {API_BASE_URL} (start Postgres + `./gradlew bootRun`)"
        if _backend_required():
            pytest.fail(f"{reason}; REQUIRE_BACKEND/CI is set, so integration tests may not be skipped", pytrace=False)
        pytest.skip(reason)
    with requests.Session() as session:
        yield FoodMeApi(session, API_BASE_URL)


def pytest_collection_modifyitems(config, items):
    """Marks each test with its level (unit / integration / e2e) and suite from its folder, so `-m e2e` works."""
    tests_root = Path(__file__).parent
    for item in items:
        try:
            parts = item.path.relative_to(tests_root).parts
        except ValueError:
            continue
        for name in suite_markers(parts):
            item.add_marker(getattr(pytest.mark, name))
