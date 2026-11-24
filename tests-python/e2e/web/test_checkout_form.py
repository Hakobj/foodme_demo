"""Checkout: account gate, contact prefill, client-side validation, price summary, order payload."""

import pytest
from playwright.sync_api import Page, expect

from pages.web import CartPanel, CheckoutPage
from support.api import admin_token, register_customer
from support.config import DEFAULT_PASSWORD


@pytest.fixture
def checkout(cart_with_first_dish: CartPanel) -> CheckoutPage:
    """Signed-in checkout: one dish in the cart and a fresh account created at checkout."""
    checkout = cart_with_first_dish.go_to_checkout()
    checkout.created_account = checkout.create_account("Form Tester", phone="+37491555666")  # type: ignore[attr-defined]
    return checkout


def test_guest_checkout_shows_account_panel_instead_of_the_form(cart_with_first_dish: CartPanel):
    checkout = cart_with_first_dish.go_to_checkout()

    expect(checkout.heading).to_be_visible()
    expect(checkout.account.tab).to_be_visible()
    expect(checkout.sign_in_form.tab).to_be_visible()
    expect(checkout.form).to_have_count(0)
    expect(checkout.place_order_button).to_have_count(0)


def test_existing_customer_signs_in_at_checkout(page: Page, api, cart_with_first_dish: CartPanel):
    customer = register_customer(api, full_name="Returning Buyer", phone="+37491777888")
    checkout = cart_with_first_dish.go_to_checkout()

    checkout.sign_in(customer["email"], DEFAULT_PASSWORD)

    expect(checkout.signed_in_text).to_have_text("Signed in as Returning Buyer")
    expect(checkout.full_name).to_have_value("Returning Buyer")
    expect(checkout.email).to_have_value(customer["email"])


def test_contact_fields_are_prefilled_from_the_new_account(checkout: CheckoutPage):
    expect(checkout.full_name).to_have_value("Form Tester")
    expect(checkout.phone).to_have_value("+37491555666")
    expect(checkout.email).to_have_value(checkout.created_account["email"])  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("full_name", "A", "Enter your name"),
        ("phone", "123", "Enter a valid phone number"),
        ("email", "ann@localhost", "Enter a valid email"),  # passes the browser check, not zod
    ],
)
def test_invalid_contact_field_blocks_the_order(page: Page, checkout: CheckoutPage, field: str, value: str, message):
    checkout.fill_address("Yerevan", "Abovyan")
    getattr(checkout, field).fill(value)

    checkout.submit_invalid()

    expect(checkout.field_error(message)).to_be_visible()
    expect(getattr(checkout, field)).to_have_attribute("aria-invalid", "true")
    checkout.wait_loaded()


def test_delivery_requires_city_and_street(checkout: CheckoutPage):
    checkout.choose_delivery().submit_invalid()

    expect(checkout.field_error("City is required")).to_be_visible()
    expect(checkout.field_error("Street is required")).to_be_visible()
    checkout.wait_loaded()


def test_takeaway_does_not_require_an_address(checkout: CheckoutPage):
    checkout.choose_takeaway()
    success = checkout.place_order().wait_loaded()
    expect(success.title).to_be_visible()


def test_price_summary_for_delivery(checkout: CheckoutPage):
    checkout.choose_delivery()

    expect(checkout.summary_value("Subtotal")).to_have_text("2,500 AMD")
    expect(checkout.summary_value("Delivery")).to_have_text("500 AMD")
    expect(checkout.summary_value("Total")).to_have_text("3,000 AMD")
    expect(checkout.price_summary).to_contain_text("Add 2,500 AMD more for free delivery.")


def test_price_summary_for_takeaway_has_free_delivery(checkout: CheckoutPage):
    checkout.choose_takeaway()

    expect(checkout.summary_value("Delivery")).to_have_text("Free")
    expect(checkout.summary_value("Total")).to_have_text("2,500 AMD")


def test_order_carries_note_address_and_receiver(page: Page, api, checkout: CheckoutPage):
    checkout.choose_delivery()
    checkout.fill_receiver("Note Writer", "+37491000111", "note@example.com")
    checkout.fill_address("Gyumri", "Rizhkov", building="3", apartment="12")
    checkout.note.fill("Ring twice, please")

    checkout.place_order().wait_loaded()

    orders = api.admin.orders(admin_token(api), page=0, size=20).json()["list"]
    order = next(o for o in orders if o["receiverName"] == "Note Writer")
    assert order["note"] == "Ring twice, please"
    assert order["deliveryMethod"] == "DELIVERY"
    assert order["paymentType"] == "CASH"
    assert order["receiverPhoneNumber"] == "+37491000111"
    assert order["addressDto"]["city"] == "Gyumri"
    assert order["addressDto"]["apartment"] == "12"


def test_takeaway_order_has_no_address(page: Page, api, checkout: CheckoutPage):
    checkout.choose_takeaway()
    checkout.fill_receiver("Pickup Person", "+37491000222", "pickup@example.com")

    checkout.place_order().wait_loaded()

    orders = api.admin.orders(admin_token(api), page=0, size=20).json()["list"]
    order = next(o for o in orders if o["receiverName"] == "Pickup Person")
    assert order["deliveryMethod"] == "TAKEAWAY"
    assert order["addressDto"] is None


def test_placing_an_order_empties_the_cart(page: Page, checkout: CheckoutPage):
    checkout.choose_takeaway()
    checkout.place_order().wait_loaded()

    expect(CheckoutPage(page).open().empty_cart_message).to_be_visible()
