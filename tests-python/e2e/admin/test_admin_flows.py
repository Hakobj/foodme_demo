"""Port of apps/admin/e2e/admin-flows.spec.ts. Runs serially (shared seeded admin)."""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.admin import AdminLoginPage, ChefsListPage, DishesListPage, OrdersListPage, Sidebar
from support.api import create_order_via_api


@pytest.fixture
def api_order(api) -> dict:
    """Port of createOrderViaApi: places a fresh CASH / TAKEAWAY order and returns it."""
    return create_order_via_api(api)


class TestAdminAuth:
    def test_rejects_bad_password(self, page: Page):
        login = AdminLoginPage(page).open()
        login.submit("admin", "wrong")
        expect(login.invalid_credentials_error).to_be_visible()

    def test_logs_in_with_seeded_credentials(self, page: Page):
        sidebar = AdminLoginPage(page).login_as_admin()
        expect(sidebar.item("Chefs")).to_be_visible()
        expect(sidebar.item("Dishes")).to_be_visible()


class TestAdminResources:
    @pytest.fixture(autouse=True)
    def sidebar(self, page: Page) -> Sidebar:
        return AdminLoginPage(page).login_as_admin()

    def test_orders_list_shows_rows_after_api_order(self, page: Page, api_order):
        orders = OrdersListPage(page).open().refresh()
        expect(orders.order(api_order["number"])).to_be_visible(timeout=15_000)

    def test_order_show_and_mark_accepted(self, page: Page, api_order):
        order_page = OrdersListPage(page).open().refresh().open_order(api_order["number"])
        expect(order_page.heading(api_order["number"])).to_be_visible()

        order_page.mark_as("ACCEPTED")
        expect(order_page.status_updated_notification).to_be_visible(timeout=order_page.STATUS_TIMEOUT)
        expect(order_page.status("ACCEPTED")).to_be_visible()

    def test_chefs_list_loads_and_opens_edit(self, page: Page):
        chefs = ChefsListPage(page).open()
        expect(chefs.empty_message).to_have_count(0, timeout=chefs.LIST_TIMEOUT)
        expect(chefs.seeded_chef).to_be_visible(timeout=chefs.LIST_TIMEOUT)
        chefs.open_first_row()

    def test_dishes_list_loads_and_opens_edit(self, page: Page):
        dishes = DishesListPage(page).open()
        expect(dishes.empty_message).to_have_count(0, timeout=dishes.LIST_TIMEOUT)
        expect(dishes.rows.first).to_be_visible(timeout=dishes.LIST_TIMEOUT)
        dishes.open_first_row()

    def test_sidebar_navigates_between_resources(self, page: Page, sidebar: Sidebar):
        OrdersListPage(page).open()
        for name, url in (("Chefs", r"#/chefs"), ("Dishes", r"#/dishes"), ("Orders", r"#/orders")):
            sidebar.go_to(name)
            expect(page).to_have_url(re.compile(url))
