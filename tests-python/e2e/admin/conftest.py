import pytest

from support.config import ADMIN_BASE_URL
from support.servers import ensure_dev_server, stop


@pytest.fixture(scope="session")
def admin_server(api):
    proc = ensure_dev_server(ADMIN_BASE_URL, app="admin", port=5174)
    yield ADMIN_BASE_URL
    stop(proc)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, admin_server):
    return {**browser_context_args, "base_url": admin_server}
