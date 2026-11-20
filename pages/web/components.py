"""Components shared by several storefront pages."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from support.api import unique_email
from support.config import DEFAULT_PASSWORD

if TYPE_CHECKING:
    from pages.web.explore_page import ExplorePage
    from pages.web.login_page import LoginPage


class Header:
    def __init__(self, page: Page):
        self.page = page
        self.root = page.get_by_role("banner")
        self.explore_chefs_link = self.root.get_by_role("link", name="Explore chefs")
        self.sign_in_link = self.root.get_by_role("link", name="Sign in")

    def go_to_explore(self) -> ExplorePage:
        from pages.web.explore_page import ExplorePage

        self.explore_chefs_link.click()
        return ExplorePage(self.page)

    def go_to_sign_in(self) -> LoginPage:
        from pages.web.login_page import LoginPage

        self.sign_in_link.click()
        return LoginPage(self.page).wait_loaded()


class SignInForm:
    """The "Sign in" tab of the auth panel (/login and checkout)."""

    def __init__(self, page: Page):
        self.page = page
        self.tab = page.get_by_role("tab", name="Sign in")
        self.form = page.get_by_role("form", name="Sign in")
        self.email = self.form.get_by_label("Email")
        self.password = self.form.get_by_label("Password")
        self.submit_button = self.form.get_by_role("button", name="Sign in")
        self.error = self.form.get_by_role("alert")

    def sign_in(self, email: str, password: str = DEFAULT_PASSWORD) -> None:
        self.tab.click()
        self.email.fill(email)
        self.password.fill(password)
        self.submit_button.click()


class CreateAccountForm:
    """The "Create account" tab, used on /login and at checkout."""

    def __init__(self, page: Page):
        self.page = page
        self.tab = page.get_by_role("tab", name="Create account")
        self.form = page.get_by_role("form", name="Create account")
        self.full_name = self.form.get_by_label("Full name")
        self.email = self.form.get_by_label("Email")
        self.phone = self.form.get_by_label("Phone")
        self.password = self.form.get_by_label("Password")
        self.submit_button = self.form.get_by_role("button", name="Create account")

    def signed_in_as(self, name: str) -> Locator:
        return self.page.get_by_text(re.compile(f"Signed in as {re.escape(name)}"))

    def register(
        self, name: str, email: str | None = None, phone: str = "+37493333444", password: str = DEFAULT_PASSWORD
    ) -> dict:
        """Fills and submits the form. Uses a unique email unless one is given. Returns the credentials."""
        email = email or unique_email("e2e")
        self.tab.click()
        self.full_name.fill(name)
        self.email.fill(email)
        self.phone.fill(phone)
        self.password.fill(password)
        self.submit_button.click()
        return {"email": email, "password": password, "name": name}

    def register_and_wait(self, name: str, **kwargs) -> dict:
        """Port of createAccountAtCheckout: registers, then waits for the "Signed in as" text."""
        account = self.register(name, **kwargs)
        expect(self.signed_in_as(name)).to_be_visible()
        return account
