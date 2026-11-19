import pytest
from playwright.sync_api import Page

from pages.web import CartPanel, ExplorePage
from support.config import WEB_BASE_URL
from support.servers import ensure_dev_server, stop


@pytest.fixture(scope="session")
def web_server(api):
    proc = ensure_dev_server(WEB_BASE_URL, app="web", port=5180)
    yield WEB_BASE_URL
    stop(proc)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, web_server):
    return {**browser_context_args, "base_url": web_server}


@pytest.fixture
def cart_with_first_dish(page: Page) -> CartPanel:
    """Port of addFirstDishToCart: explore -> first chef -> first dish -> Add to cart."""
    cart = ExplorePage(page).open().open_first_chef().add_dish_to_cart()
    return cart.wait_for_items(1)
