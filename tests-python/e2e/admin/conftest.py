import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, admin_server):
    return {**browser_context_args, "base_url": admin_server}
