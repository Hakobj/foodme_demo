from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from pages.base_page import BasePage


class ResourceListPage(BasePage):
    """A react-admin list (`table tbody tr` rows) whose rows open the edit view."""

    PATH = "/#/"
    EMPTY_TEXT = ""
    EDIT_URL = re.compile(r"#/")
    LIST_TIMEOUT = 15_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.rows = page.locator("table tbody tr")
        self.empty_message = page.get_by_text(self.EMPTY_TEXT)

    def open_first_row(self) -> None:
        self.rows.first.click()
        expect(self.page).to_have_url(self.EDIT_URL)


class ChefsListPage(ResourceListPage):
    PATH = "/#/chefs"
    EMPTY_TEXT = "No Chefs found"
    EDIT_URL = re.compile(r"#/chefs/\d+")
    # Chef names from the Postgres seed (V1-V3).
    SEEDED_CHEF_NAMES = re.compile(
        "Alans Kitchen|Italiano Margarino|Chef Verona|Argentinean|Armenian Traditional|Sakura Kitchen", re.I
    )

    def __init__(self, page: Page):
        super().__init__(page)
        self.seeded_chef = page.get_by_text(self.SEEDED_CHEF_NAMES).first


class DishesListPage(ResourceListPage):
    PATH = "/#/dishes"
    EMPTY_TEXT = "No Dishes found"
    EDIT_URL = re.compile(r"#/dishes/\d+")
