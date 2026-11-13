from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from clients import FoodMeApi
from support.config import API_BASE_URL
from support.markers import suite_markers
from support.servers import is_up


@pytest.fixture(scope="session")
def api() -> Iterator[FoodMeApi]:
    """API client objects for the backend. Skips the test run cleanly when the backend is down."""
    if not is_up(f"{API_BASE_URL}/actuator/health"):
        pytest.skip(f"backend not reachable at {API_BASE_URL} (start Postgres + `./gradlew bootRun`)")
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
