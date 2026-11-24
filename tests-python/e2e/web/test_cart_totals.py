"""Cart panel on the chef page: subtotal, delivery fee, free-delivery hint, total, header badge.

Chef 1: dishes 2,500 AMD, delivery 500 AMD, free delivery from 5,000 AMD.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.web import CheckoutPage, ChefPage, Header


@pytest.mark.parametrize(
    ("quantity", "subtotal", "delivery", "total", "hint"),
    [
        (1, "2,500 AMD", "500 AMD", "3,000 AMD", "Add 2,500 AMD more for free delivery."),
        (2, "5,000 AMD", "Free", "5,000 AMD", None),
        (3, "7,500 AMD", "Free", "7,500 AMD", None),
    ],
)
def test_cart_summary_applies_free_delivery_threshold(
    page: Page, quantity: int, subtotal: str, delivery: str, total: str, hint: str | None
):
    chef_page = ChefPage(page).open(1)
    cart = chef_page.quick_add("House Special").wait_for_items(1)
    for _ in range(quantity - 1):
        cart.increase()
    expect(cart.quantity).to_have_text(str(quantity))

    expect(cart.summary_value("Subtotal")).to_have_text(subtotal)
    expect(cart.summary_value("Delivery")).to_have_text(delivery)
    expect(cart.summary_value("Total")).to_have_text(total)
    if hint:
        expect(cart.free_delivery_hint).to_have_text(hint)
    else:
        expect(cart.free_delivery_hint).to_have_count(0)


def test_cart_subtotal_adds_up_different_dishes(page: Page):
    chef_page = ChefPage(page).open(1)
    chef_page.quick_add("House Special").wait_for_items(1)
    cart = chef_page.quick_add("Chef's Salad").wait_for_items(2)

    expect(cart.summary_value("Subtotal")).to_have_text("5,000 AMD")
    expect(cart.item_count_badge).to_have_text("2")


def test_header_cart_badge_counts_items(page: Page):
    chef_page = ChefPage(page).open(1)
    header = Header(page)
    expect(header.cart_link).to_have_accessible_name("Cart")

    cart = chef_page.quick_add("House Special").wait_for_items(1)
    cart.increase()

    expect(header.cart_link).to_have_accessible_name("Cart, 2 items")
    expect(header.cart_link).to_have_text("2")


def test_header_cart_link_opens_checkout_with_the_cart(page: Page):
    ChefPage(page).open(1).quick_add("House Special").wait_for_items(1)

    Header(page).cart_link.click()

    expect(page).to_have_url(re.compile(r"/checkout$"))
    expect(CheckoutPage(page).heading).to_be_visible()
