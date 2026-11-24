from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

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
        self.foreign_cart_message = self.root.get_by_text("Cart has another kitchen")
        self.go_to_current_cart_link = self.root.get_by_role("link", name="Go to current cart")
        self.free_delivery_hint = self.root.get_by_text(re.compile(r"more for free delivery"))
        self.item_count_badge = self.root.locator("h3 + span")

    def summary_value(self, label: str) -> Locator:
        """The amount next to "Subtotal", "Delivery" or "Total" in the panel's price summary."""
        # exact label match, so "Total" doesn't also match the "Subtotal" row
        label_span = self.page.get_by_text(label, exact=True)
        return self.root.locator("div.flex.items-baseline").filter(has=label_span).locator("span").last

    def item(self, name: str) -> Locator:
        return self.items.filter(has_text=name)

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
