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

    def open(self, query: str | None = None) -> Self:
        self.page.goto(f"{self.PATH}?{urlencode({'q': query})}" if query else self.PATH)
        return self

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/explore"))
        return self

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
