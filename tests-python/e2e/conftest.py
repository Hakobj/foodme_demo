"""E2E tests run the real storefront / back office in a browser against an in-memory backend mock.

Every browser request to the backend URL is intercepted by Playwright and answered by the mock,
and the Python `api` fixture talks to the same mock, so no backend or database is needed.
"""

from collections.abc import Iterator

import pytest
import requests
from playwright.sync_api import BrowserContext

from clients import FoodMeApi
from support.config import ADMIN_BASE_URL, API_BASE_URL
from support.mock_e2e_backend import MockE2EBackend
from support.servers import ensure_dev_server, stop


@pytest.fixture(scope="session")
def mock_backend() -> MockE2EBackend:
    return MockE2EBackend()


@pytest.fixture(scope="session")
def api(mock_backend: MockE2EBackend) -> Iterator[FoodMeApi]:
    with requests.Session() as session:
        session.mount(API_BASE_URL, mock_backend)
        yield FoodMeApi(session, API_BASE_URL)


@pytest.fixture(autouse=True)
def mocked_backend(context: BrowserContext, mock_backend: MockE2EBackend) -> None:
    """Fresh mock data per test; the browser's backend calls go to the mock."""
    mock_backend.reset()
    context.route(f"{API_BASE_URL}/**", mock_backend.handle_route)


@pytest.fixture(scope="session")
def admin_server() -> Iterator[str]:
    proc = ensure_dev_server(ADMIN_BASE_URL, app="admin", port=5174)
    yield ADMIN_BASE_URL
    stop(proc)
