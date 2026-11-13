"""Storefront sign-in for an existing account (created through the API) and its order history."""

from playwright.sync_api import Page, expect

from pages.web import LoginPage
from support.api import cash_order_payload, create_order, first_chef_and_dish, register_customer
from support.config import DEFAULT_PASSWORD


def test_existing_customer_signs_in_and_sees_empty_order_history(page: Page, api):
    customer = register_customer(api, full_name="Sign In User")

    orders = LoginPage(page).open().sign_in(customer["email"], DEFAULT_PASSWORD).wait_loaded()

    expect(orders.heading).to_be_visible()
    expect(orders.empty_message).to_be_visible()


def test_signed_in_customer_sees_order_placed_through_the_api(page: Page, api):
    customer = register_customer(api, full_name="History User")
    chef, dish = first_chef_and_dish(api)
    order = create_order(api, customer["token"], cash_order_payload(chef["id"], dish["id"]))

    orders = LoginPage(page).open().sign_in(customer["email"], DEFAULT_PASSWORD).wait_loaded()

    expect(orders.order(order["number"])).to_be_visible()


def test_wrong_password_shows_error_and_stays_on_login(page: Page, api):
    customer = register_customer(api, full_name="Wrong Password User")
    login = LoginPage(page).open()

    login.sign_in(customer["email"], "wrong-password")

    expect(login.sign_in_form.error).to_have_text("Invalid email or password")
    login.wait_loaded()
