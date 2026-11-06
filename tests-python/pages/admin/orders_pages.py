from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage


class OrdersListPage(BasePage):
    PATH = "/#/orders"

    def __init__(self, page: Page):
        super().__init__(page)
        self.refresh_button = page.get_by_role("button", name="Refresh")
        self.rows = page.locator("table tbody tr")

    def refresh(self) -> OrdersListPage:
        """react-admin lists don't refresh on their own after data is created through the API."""
        self.refresh_button.click()
        return self

    def order(self, number: str) -> Locator:
        return self.page.get_by_text(number)

    def open_order(self, number: str) -> OrderShowPage:
        self.order(number).click()
        return OrderShowPage(self.page).wait_loaded()


class OrderShowPage(BasePage):
    STATUS_TIMEOUT = 10_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.status_updated_notification = page.get_by_text("Order status updated")

    def wait_loaded(self) -> OrderShowPage:
        expect(self.page).to_have_url(re.compile(r"#/orders/\d+/show"))
        return self

    def heading(self, number: str) -> Locator:
        # The app-bar title and the page heading both render "Order FM-..."; level 5 is the page heading.
        return self.page.get_by_role("heading", name=f"Order {number}", level=5)

    def status(self, status: str) -> Locator:
        return self.page.get_by_text(status).first

    def mark_as(self, status: str) -> OrderShowPage:
        self.page.get_by_role("button", name=f"Mark as {status}").click()
        return self
