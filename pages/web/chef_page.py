from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.web.cart_panel import CartPanel

if TYPE_CHECKING:
    from typing_extensions import Self


class DishModal:
    """The dish detail modal opened from a `button.dc_card`."""

    def __init__(self, page: Page):
        self.page = page
        self.add_to_cart_button = page.get_by_role("button", name="Add to cart")
        self.additions_heading = page.get_by_role("heading", name="Additions")
        self.first_addition = page.locator('label[for^="addition-"]').first
        self.first_addition_checkbox = self.first_addition.locator('input[type="checkbox"]')
        self.first_addition_checkmark = self.first_addition.locator('span[aria-hidden="true"]')

    def select_first_addition(self) -> DishModal:
        self.first_addition_checkbox.check()
        return self

    def add_to_cart(self) -> CartPanel:
        self.add_to_cart_button.click()
        return CartPanel(self.page)


class ChefPage(BasePage):
    URL_PATTERN = re.compile(r"/chef/\d+")

    def __init__(self, page: Page):
        super().__init__(page)
        self.dish_cards = page.locator("button.dc_card")
        self.not_found_message = page.get_by_text("Chef not found")
        self.switch_kitchens_prompt = page.get_by_text("Switch kitchens?")
        self.cart = CartPanel(page)

    def open(self, chef_id: int) -> Self:  # type: ignore[override]
        self.page.goto(f"/chef/{chef_id}")
        return self

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(self.URL_PATTERN)
        return self

    def dish_card(self, name: str) -> Locator:
        return self.dish_cards.filter(has_text=name).first

    def open_dish(self, index: int = 0) -> DishModal:
        self.dish_cards.nth(index).click()
        return DishModal(self.page)

    def open_dish_by_name(self, name: str) -> DishModal:
        # click() scrolls into view itself and retries if React re-renders the card mid-action;
        # a separate scroll_into_view_if_needed() fails on such a detach.
        self.dish_card(name).click()
        return DishModal(self.page)

    def add_dish_to_cart(self, index: int = 0) -> CartPanel:
        return self.open_dish(index).add_to_cart()
