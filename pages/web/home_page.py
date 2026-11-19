from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.web.components import Header

if TYPE_CHECKING:
    from pages.web.chef_page import ChefPage
    from pages.web.explore_page import ExplorePage


class HomePage(BasePage):
    PATH = "/"

    # "Chefs worth knowing" loads slowly because of the API latency (web-testing rules).
    POPULAR_TIMEOUT = 15_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.hero_heading = page.get_by_role("heading", name=re.compile("Real food, made by", re.I), level=1)
        self.order_now_link = page.get_by_role("link", name="Order now").first
        self.steps_heading = page.get_by_role("heading", name=re.compile("Three steps to", re.I), level=2)
        self.popular_heading = page.get_by_role("heading", name="Chefs worth knowing", level=2)
        self.popular_chef_cards = page.locator("section:has-text('Chefs worth knowing') .grid").first.locator(
            "a.cc_card"
        )
        self.cta_heading = page.get_by_role(
            "heading", name=re.compile("Your next favourite meal is one tap away", re.I), level=2
        )
        self.browse_chefs_link = page.get_by_role("link", name=re.compile("Browse chefs", re.I))

    def step_heading(self, name: str) -> Locator:
        return self.page.get_by_role("heading", name=name, level=3)

    def click_order_now(self) -> ExplorePage:
        from pages.web.explore_page import ExplorePage

        self.order_now_link.click()
        return ExplorePage(self.page)

    def open_first_popular_chef(self) -> ChefPage:
        from pages.web.chef_page import ChefPage

        card = self.popular_chef_cards.first
        expect(card).to_be_visible(timeout=self.POPULAR_TIMEOUT)
        card.click()
        return ChefPage(self.page).wait_loaded()
