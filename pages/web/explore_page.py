from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

if TYPE_CHECKING:
    from typing_extensions import Self

    from pages.web.chef_page import ChefPage


class ExplorePage(BasePage):
    PATH = "/explore"

    def __init__(self, page: Page):
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="Explore chefs", level=1)
        self.search_box = page.get_by_role("searchbox")
        self.chefs_grid = page.locator(".ep_wrap .grid").first
        self.chef_cards = self.chefs_grid.locator("a.cc_card")
        self.chef_count_text = page.get_by_text(re.compile(r"\d+ chefs cooking near you"))
        # Kitchen filter chips are toggle buttons (aria-pressed); "All" clears the filter.
        self.kitchen_chips = page.locator("button[aria-pressed]")
        self.all_kitchens_chip = page.get_by_role("button", name="All", exact=True)
        self.no_match_message = page.get_by_text("No chefs match")
        self.clear_filters_button = page.get_by_role("button", name="Clear filters")

    def open(self, query: str | None = None) -> Self:
        self.page.goto(f"{self.PATH}?{urlencode({'q': query})}" if query else self.PATH)
        return self

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/explore"))
        return self

    def kitchen_chip(self, kitchen: str) -> Locator:
        return self.page.get_by_role("button", name=kitchen, exact=True)

    def filter_by_kitchen(self, kitchen: str) -> Self:
        self.kitchen_chip(kitchen).click()
        return self

    def chef_card(self, name: str) -> Locator:
        return self.chef_cards.filter(has_text=name)

    def open_chef(self, name: str) -> ChefPage:
        from pages.web.chef_page import ChefPage

        self.chef_card(name).click()
        return ChefPage(self.page).wait_loaded()

    # ---- parts of a chef card ----
    @staticmethod
    def card_image(card: Locator) -> Locator:
        return card.locator("img")

    @staticmethod
    def card_name(card: Locator) -> Locator:
        return card.locator("p.truncate").first

    @staticmethod
    def card_metadata(card: Locator) -> Locator:
        return card.locator("p.truncate").nth(1)

    @staticmethod
    def card_rating(card: Locator) -> Locator:
        return card.locator(".text-amber-500")

    def open_first_chef(self) -> ChefPage:
        from pages.web.chef_page import ChefPage

        first = self.chef_cards.first
        expect(first).to_be_visible()
        first.click()
        return ChefPage(self.page).wait_loaded()
