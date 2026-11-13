"""Order history, order success / failed and tracking pages."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

if TYPE_CHECKING:
    from typing_extensions import Self


class OrdersPage(BasePage):
    PATH = "/orders"

    def __init__(self, page: Page):
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Your orders")
        self.empty_message = page.get_by_text(re.compile("No orders yet", re.I))

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/orders$"))
        return self

    def order(self, number: str) -> Locator:
        return self.page.get_by_text(number)


class OrderSuccessPage(BasePage):
    PATH = "/orders/success"

    def __init__(self, page: Page):
        super().__init__(page)
        self.title = page.get_by_text("Order placed!")
        self.order_number_text = page.get_by_text(re.compile("Your order number is", re.I))
        self.track_order_link = page.get_by_role("link", name="Track order")
        self.back_to_explore_link = page.get_by_role("link", name="Back to explore")

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/orders/success"))
        return self

    def track_order(self) -> TrackingPage:
        self.track_order_link.click()
        return TrackingPage(self.page).wait_loaded()


class TrackingPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.all_orders_link = page.get_by_role("link", name="All orders")

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/tracking/FM-"))
        return self

    @property
    def order_number(self) -> str:
        match = re.search(r"FM-\d+", self.page.url)
        assert match, f"no order number in {self.page.url}"
        return match.group(0)

    def go_to_all_orders(self) -> OrdersPage:
        self.all_orders_link.click()
        return OrdersPage(self.page).wait_loaded()


class OrderFailedPage(BasePage):
    PATH = "/orders/failed"

    def __init__(self, page: Page):
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Order failed")
        self.back_to_explore_link = page.get_by_role("link", name="Back to explore")
