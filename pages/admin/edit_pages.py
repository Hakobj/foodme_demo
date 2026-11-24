"""Back-office dashboard and the react-admin edit forms for chefs and dishes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

if TYPE_CHECKING:
    from typing_extensions import Self


class DashboardPage(BasePage):
    PATH = "/#/"
    LOAD_TIMEOUT = 15_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.cards = page.locator(".MuiCard-root")

    def stat(self, label: str) -> Locator:
        """The value under a stat card's label ("Total orders", "Recent revenue", "Chefs", "Dishes")."""
        card = self.cards.filter(has=self.page.get_by_text(label, exact=True))
        return card.locator("h5")


class ResourceEditPage(BasePage):
    """A react-admin <Edit><SimpleForm>: labelled inputs plus a Save button."""

    RESOURCE = ""
    SAVE_TIMEOUT = 10_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.save_button = page.get_by_role("button", name="Save")
        self.saved_notification = page.get_by_text("Element updated")

    def open_record(self, record_id: int) -> Self:
        self.page.goto(f"/#/{self.RESOURCE}/{record_id}")
        return self.wait_loaded()

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(rf"#/{self.RESOURCE}/\d+"))
        return self

    def field(self, label: str) -> Locator:
        return self.page.get_by_label(label, exact=True)

    def fill(self, label: str, value: str) -> Self:
        self.field(label).fill(value)
        return self

    def save(self) -> Self:
        """Saves and waits for the PUT. react-admin saves in "undoable" mode: the notification shows
        at once, the request only goes out when the undo window closes (about 5 s)."""
        with self.page.expect_response(lambda r: r.request.method == "PUT", timeout=self.SAVE_TIMEOUT + 10_000):
            self.save_button.click()
            expect(self.saved_notification).to_be_visible(timeout=self.SAVE_TIMEOUT)
        return self


class ChefEditPage(ResourceEditPage):
    RESOURCE = "chefs"


class DishEditPage(ResourceEditPage):
    RESOURCE = "dishes"
