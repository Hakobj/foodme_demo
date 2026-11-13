from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import Page, expect

from pages.admin.sidebar import Sidebar
from pages.base_page import BasePage
from support.config import ADMIN_PASSWORD, ADMIN_USERNAME

if TYPE_CHECKING:
    from typing_extensions import Self


class AdminLoginPage(BasePage):
    PATH = "/#/login"
    LOGIN_TIMEOUT = 15_000

    def __init__(self, page: Page):
        super().__init__(page)
        self.heading = page.get_by_role("heading", name="FoodMe Admin")
        self.username = page.get_by_label("Username")
        self.password = page.get_by_label("Password")
        self.sign_in_button = page.get_by_role("button", name="Sign in")
        self.invalid_credentials_error = page.get_by_text("Invalid username or password.")
        self.sidebar = Sidebar(page)

    def open_at(self, admin_root_url: str) -> Self:
        """Opens the login page of an admin served elsewhere, e.g. `<backend>/backoffice`."""
        self.page.goto(f"{admin_root_url.rstrip('/')}/{self.PATH.lstrip('/')}")
        return self

    def submit(self, username: str, password: str) -> Self:
        self.username.fill(username)
        self.password.fill(password)
        self.sign_in_button.click()
        return self

    def login_as_admin(self) -> Sidebar:
        """Port of loginAsAdmin: seeded admin, waits for the "Orders" menu item."""
        self.open()
        expect(self.heading).to_be_visible()
        self.submit(ADMIN_USERNAME, ADMIN_PASSWORD)
        expect(self.sidebar.item("Orders")).to_be_visible(timeout=self.LOGIN_TIMEOUT)
        return self.sidebar
