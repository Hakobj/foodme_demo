from collections.abc import Iterator

import pytest
import requests

from clients import FoodMeApi
from support.config import API_BASE_URL
from support.servers import is_up


@pytest.fixture(scope="session")
def api() -> Iterator[FoodMeApi]:
    """API client objects for the backend. Skips the test run cleanly when the backend is down."""
    if not is_up(f"{API_BASE_URL}/actuator/health"):
        pytest.skip(f"backend not reachable at {API_BASE_URL} (start Postgres + `./gradlew bootRun`)")
    with requests.Session() as session:
        yield FoodMeApi(session, API_BASE_URL)


def pytest_collection_modifyitems(items):
    """Marks each test with its suite (api / web / admin) from its folder, so `-m web` works."""
    for item in items:
        suite = item.path.parent.name
        if suite in ("api", "web", "admin"):
            item.add_marker(getattr(pytest.mark, suite))
