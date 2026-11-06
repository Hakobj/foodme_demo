from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from pages.web.components import CreateAccountForm

if TYPE_CHECKING:
    from typing_extensions import Self

    from pages.web.orders_pages import OrdersPage


class LoginPage(BasePage):
    PATH = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.account = CreateAccountForm(page)

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/login"))
        return self

    def create_account(self, name: str, phone: str = "+37491111000") -> OrdersPage:
        """Signs up through the "Create account" tab; the app then redirects to the orders history."""
        from pages.web.orders_pages import OrdersPage

        self.account.register(name, phone=phone)
        return OrdersPage(self.page)
