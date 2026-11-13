from playwright.sync_api import Page
from typing_extensions import Self


class BasePage:
    """Every page object wraps a Playwright `Page`. `PATH` is relative to the context `base_url`."""

    PATH = "/"

    def __init__(self, page: Page):
        self.page = page

    def open(self) -> Self:
        self.page.goto(self.PATH)
        return self

    def reload(self) -> Self:
        self.page.reload()
        return self
