"""Storefront auth forms (validation, duplicate email, ?next= redirect, header state) and order tracking."""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.web import Footer, Header, HomePage, LoginPage, TrackingPage
from support.api import admin_token, cash_order_payload, create_order, first_chef_and_dish, register_customer
from support.config import DEFAULT_PASSWORD


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("ann@localhost", DEFAULT_PASSWORD, "Enter a valid email"),
        ("ann@example.com", "short", "Password must be at least 8 characters"),
    ],
)
def test_sign_in_form_validation(page: Page, email: str, password: str, message: str):
    login = LoginPage(page).open()

    login.sign_in_form.sign_in(email, password)

    expect(login.sign_in_form.field_error(message)).to_be_visible()
    login.wait_loaded()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "A"}, "Enter your name"),
        ({"phone": "1234"}, "Enter a valid phone number"),
        ({"password": "short"}, "Password must be at least 8 characters"),
    ],
)
def test_create_account_form_validation(page: Page, overrides: dict, message: str):
    login = LoginPage(page).open()
    values = {"name": "Valid Name", "phone": "+37491111000", "password": DEFAULT_PASSWORD, **overrides}

    login.account.register(values["name"], phone=values["phone"], password=values["password"])

    expect(login.account.field_error(message)).to_be_visible()
    login.wait_loaded()


def test_registering_an_existing_email_shows_the_api_error(page: Page, api):
    customer = register_customer(api, full_name="Taken Email")
    login = LoginPage(page).open()

    login.account.register("Second Person", email=customer["email"])

    expect(login.account.error).to_have_text("Email already registered")
    login.wait_loaded()


def test_sign_in_redirects_to_next(page: Page, api):
    customer = register_customer(api, full_name="Next Param")

    LoginPage(page).open_with_next("/explore").sign_in_form.sign_in(customer["email"], DEFAULT_PASSWORD)

    expect(page).to_have_url(re.compile(r"/explore$"))


def test_signed_in_header_shows_orders_and_account_instead_of_sign_in(page: Page, api):
    customer = register_customer(api, full_name="Header State")
    LoginPage(page).open().sign_in(customer["email"], DEFAULT_PASSWORD).wait_loaded()
    header = Header(page)

    expect(header.sign_in_link).to_have_count(0)
    expect(header.orders_link).to_be_visible()
    expect(header.account_link).to_have_accessible_name("Account, Header State")
    expect(header.account_link).to_have_text("H")
    expect(Footer(page).link("Sign in")).to_have_count(0)


def test_guest_footer_has_explore_orders_and_sign_in_links(page: Page):
    LoginPage(page).open()
    footer = Footer(page)

    expect(footer.disclaimer).to_be_visible()
    expect(footer.link("Explore")).to_have_attribute("href", "/explore")
    expect(footer.link("Orders")).to_have_attribute("href", "/orders")
    expect(footer.link("Sign in")).to_have_attribute("href", "/login?next=/orders")


def test_logo_and_unknown_routes_lead_home(page: Page):
    HomePage(page).open_path("/no-such-page")
    expect(page).to_have_url(re.compile(r"/$"))

    LoginPage(page).open()
    Header(page).home_link.click()
    expect(page).to_have_url(re.compile(r"/$"))


# ---- tracking ------------------------------------------------------------------------------


@pytest.fixture
def placed_order(api) -> dict:
    """A fresh customer with one NEW order: 2 x the first chef's first dish (TAKEAWAY)."""
    customer = register_customer(api, full_name="Tracking Customer")
    chef, dish = first_chef_and_dish(api)
    payload = cash_order_payload(chef["id"], dish["id"])
    payload["createOrderDishes"][0]["quantity"] = 2
    order = create_order(api, customer["token"], payload)
    return {**order, **customer, "dish": dish["nameEn"], "chef": chef["username"]}


def move_order(api, order: dict, *statuses: str) -> None:
    token = admin_token(api)
    for status in statuses:
        reason = "Out of stock" if status == "REJECTED" else None
        response = api.admin.update_order_status(token, order["id"], status, reason)
        assert response.ok, response.text


@pytest.mark.parametrize(
    ("statuses", "title", "badge"),
    [
        ((), "Order received", "Received"),
        (("ACCEPTED",), "Preparing your order", "Preparing"),
        (("ACCEPTED", "DELIVERED"), "Delivered", "Delivered"),
        (("REJECTED",), "Order declined", "Declined"),
    ],
)
def test_order_status_on_tracking_and_order_history(page: Page, api, placed_order, statuses, title, badge):
    move_order(api, placed_order, *statuses)
    orders = LoginPage(page).open().sign_in(placed_order["email"], DEFAULT_PASSWORD).wait_loaded()

    expect(orders.status_badge(placed_order["number"])).to_have_text(badge)

    tracking = orders.open_tracking(placed_order["number"])
    expect(tracking.status_title(title)).to_be_visible()


def test_tracking_lists_items_chef_and_total(page: Page, placed_order):
    tracking = TrackingPage(page).open_order(placed_order["number"])

    expect(tracking.heading).to_have_text(f"Order {placed_order['number']}")
    expect(tracking.chef_line).to_have_text(f"Chef · {placed_order['chef']}")
    expect(tracking.item_row(placed_order["dish"])).to_contain_text("5,000 AMD")
    expect(tracking.item_row(placed_order["dish"])).to_contain_text("2")
    expect(tracking.total).to_have_text("5,000 AMD")


def test_accepted_order_marks_the_preparing_step_current(page: Page, api, placed_order):
    move_order(api, placed_order, "ACCEPTED")

    tracking = TrackingPage(page).open_order(placed_order["number"])

    expect(tracking.current_step).to_have_count(1)
    expect(tracking.current_step).to_contain_text("Preparing")


def test_unknown_order_number_shows_load_error(page: Page):
    tracking = TrackingPage(page).open_order("FM-999999")
    expect(tracking.load_error).to_be_visible()


def test_order_history_is_empty_for_a_new_customer_and_links_to_explore(page: Page, api):
    customer = register_customer(api, full_name="No Orders")
    orders = LoginPage(page).open().sign_in(customer["email"], DEFAULT_PASSWORD).wait_loaded()

    expect(orders.empty_message).to_be_visible()
    expect(orders.browse_chefs_link).to_be_visible()
