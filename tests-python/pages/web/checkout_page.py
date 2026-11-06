from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from pages.web.components import CreateAccountForm

if TYPE_CHECKING:
    from typing_extensions import Self

    from pages.web.orders_pages import OrderSuccessPage


class CheckoutPage(BasePage):
    PATH = "/checkout"

    def __init__(self, page: Page):
        super().__init__(page)
        self.account = CreateAccountForm(page)
        self.empty_cart_message = page.get_by_text(re.compile("Your cart is empty", re.I))

        self.form = page.get_by_role("form", name="Checkout")
        self.full_name = self.form.get_by_label("Full name")
        self.phone = self.form.get_by_label("Phone")
        self.email = self.form.get_by_label("Email")

        self.delivery_option = page.get_by_role("button", name="Delivery To your door")
        self.takeaway_option = page.get_by_role("button", name="Takeaway Pick up")
        self.city = page.get_by_label("City")
        self.street = page.get_by_label("Street")
        self.building = page.get_by_label("Building")
        self.apartment = page.get_by_label("Apartment")

        self.cash_payment = page.get_by_role("radio", name=re.compile("Cash on delivery", re.I))
        self.bank_card_payment = page.get_by_role("radio", name=re.compile("Bank card", re.I))
        self.idram_payment = page.get_by_role("radio", name=re.compile("Idram", re.I))

        self.place_order_button = page.get_by_role("button", name="Place order")

        self.summary = page.locator(".cs_wrap")
        self.summary_first_quantity = self.summary.locator(".tabular-nums.text-zinc-400").first
        self.summary_first_additions = self.summary.get_by_text(re.compile(r"^\+ ")).first

    def wait_loaded(self) -> Self:
        expect(self.page).to_have_url(re.compile(r"/checkout"))
        return self

    def create_account(self, name: str = "Casey Delivery", **kwargs) -> dict:
        return self.account.register_and_wait(name, **kwargs)

    def choose_delivery(self) -> Self:
        self.delivery_option.click()
        return self

    def choose_takeaway(self) -> Self:
        self.takeaway_option.click()
        return self

    def fill_receiver(self, name: str, phone: str, email: str) -> Self:
        self.full_name.fill(name)
        self.phone.fill(phone)
        self.email.fill(email)
        return self

    def fill_address(self, city: str, street: str, building: str | None = None, apartment: str | None = None) -> Self:
        self.city.fill(city)
        self.street.fill(street)
        if building is not None:
            self.building.fill(building)
        if apartment is not None:
            self.apartment.fill(apartment)
        return self

    def place_order(self) -> OrderSuccessPage:
        from pages.web.orders_pages import OrderSuccessPage

        self.place_order_button.click()
        return OrderSuccessPage(self.page)
