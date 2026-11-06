from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Page, expect

if TYPE_CHECKING:
    from pages.web.checkout_page import CheckoutPage


class CartPanel:
    """The cart side panel (`aside.uc-panel`). The cart holds one chef at a time."""

    def __init__(self, page: Page):
        self.page = page
        self.root = page.locator("aside.uc-panel")
        self.items = self.root.locator(".cic_root")
        self.first_item = self.items.first
        self.quantity = self.root.locator(".fm-qty-grp p")
        self.increase_button = self.root.get_by_role("button", name="Increase quantity")
        self.decrease_button = self.root.get_by_role("button", name="Decrease quantity")
        self.remove_button = self.root.get_by_role("button", name="Remove item")
        self.empty_message = self.root.get_by_text(re.compile("empty", re.I))
        self.checkout_link = self.root.get_by_role("link", name="Go to checkout")

    def increase(self) -> CartPanel:
        self.increase_button.click()
        return self

    def decrease(self) -> CartPanel:
        self.decrease_button.click()
        return self

    def remove_item(self) -> CartPanel:
        self.remove_button.click()
        return self

    def wait_for_items(self, count: int) -> CartPanel:
        expect(self.items).to_have_count(count)
        return self

    def quantity_value(self) -> int:
        """Reads the quantity only after it has rendered as a number (web-testing rule)."""
        expect(self.quantity).to_have_text(re.compile(r"^\d+$"))
        return int(self.quantity.inner_text())

    def go_to_checkout(self) -> CheckoutPage:
        from pages.web.checkout_page import CheckoutPage

        self.checkout_link.click()
        return CheckoutPage(self.page).wait_loaded()
