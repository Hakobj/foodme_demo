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
        self.dialog = page.get_by_role("dialog")
        self.title = self.dialog.get_by_role("heading").first
        self.description = self.dialog.locator("#dish-description")
        self.portion = self.dialog.get_by_text(re.compile(r"^Portion · "))
        self.quantity = self.dialog.locator(".fm-qty-grp p")
        self.increase_button = self.dialog.get_by_role("button", name="Increase quantity")
        self.decrease_button = self.dialog.get_by_role("button", name="Decrease quantity")
        # The button's name also holds the price ("Add to cart · 2,500 AMD").
        self.add_to_cart_button = page.get_by_role("button", name="Add to cart")
        self.additions_heading = page.get_by_role("heading", name="Additions")
        self.first_addition = page.locator('label[for^="addition-"]').first
        self.first_addition_checkbox = self.first_addition.locator('input[type="checkbox"]')
        self.first_addition_checkmark = self.first_addition.locator('span[aria-hidden="true"]')

    def addition(self, name: str) -> Locator:
        """The checkbox of an addition, by its label text (e.g. "Extra cheese")."""
        return self.dialog.get_by_role("checkbox", name=re.compile(re.escape(name)))

    def toggle_addition(self, name: str) -> DishModal:
        self.dialog.locator("label").filter(has_text=name).click()
        return self

    def increase(self, times: int = 1) -> DishModal:
        for _ in range(times):
            self.increase_button.click()
        return self

    def close(self) -> None:
        self.page.keyboard.press("Escape")

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
        self.clear_and_continue_button = page.get_by_role("button", name="Clear & continue")
        self.keep_cart_button = page.get_by_role("button", name="Keep cart & browse")
        self.cart = CartPanel(page)

        hero = page.locator("section.cd_hero")
        self.name_heading = hero.get_by_role("heading", level=1)
        self.hero = hero
        self.delivery_info = hero.get_by_text(re.compile(r"delivery"))
        self.takeaway_badge = hero.get_by_text("Takeaway", exact=True)
        self.phone_link = hero.locator('a[href^="tel:"]')

    def menu_section(self, name: str) -> Locator:
        return self.page.get_by_role("heading", name=name, level=2)

    def quick_add_button(self, dish_name: str) -> Locator:
        return self.page.get_by_role("button", name=f"Add {dish_name} to cart")

    def quick_add(self, dish_name: str) -> CartPanel:
        self.quick_add_button(dish_name).click()
        return self.cart

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
