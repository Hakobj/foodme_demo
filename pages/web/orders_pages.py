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

    def order_card(self, number: str) -> Locator:
        return self.page.get_by_role("listitem", name=f"Order {number}")

    def rate_order_button(self, number: str) -> Locator:
        return self.order_card(number).get_by_role("button", name="Rate order")

    def order_rating(self, number: str) -> Locator:
        """The read-only stars shown in place of the button once the order is rated."""
        return self.order_card(number).get_by_role("img", name=re.compile(r"Rated \d out of 5"))

    def rate_order(self, number: str) -> RateOrderDialog:
        self.rate_order_button(number).click()
        dialog = RateOrderDialog(self.page)
        expect(dialog.dialog).to_be_visible()
        return dialog


class RateOrderDialog:
    """SCRUM-6 "Rate order" window: 5 stars, optional comment, submit."""

    def __init__(self, page: Page):
        self.page = page
        self.dialog = page.get_by_role("dialog", name=re.compile("Rate order"))
        self.comment = self.dialog.get_by_placeholder("Tell us about your order")
        self.submit_button = self.dialog.get_by_role("button", name="Submit rating")
        self.cancel_button = self.dialog.get_by_role("button", name="Cancel")
        self.error = self.dialog.get_by_role("alert")

    @staticmethod
    def _star_name(rating: int) -> str:
        return "1 star" if rating == 1 else f"{rating} stars"

    def star(self, rating: int) -> Locator:
        """The radio input for `rating` stars (visually hidden; use `choose()` to click it like a user)."""
        return self.dialog.get_by_role("radio", name=self._star_name(rating), exact=True)

    def choose(self, rating: int) -> RateOrderDialog:
        # The radio is screen-reader only; a user clicks the star drawn by its label.
        # `has=` is resolved inside each label, so it is built from the page, not the dialog.
        radio = self.page.get_by_role("radio", name=self._star_name(rating), exact=True)
        self.dialog.locator("label").filter(has=radio).click()
        return self

    def submit(self, rating: int, comment: str | None = None) -> RateOrderDialog:
        self.choose(rating)
        if comment is not None:
            self.comment.fill(comment)
        self.submit_button.click()
        return self


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
        self.review_section = page.get_by_role("region", name="Your rating")
        self.review_stars = self.review_section.get_by_role("img", name=re.compile(r"Rated \d out of 5"))

    def open_order(self, number: str) -> Self:
        self.page.goto(f"/tracking/{number}")
        return self.wait_loaded()

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
