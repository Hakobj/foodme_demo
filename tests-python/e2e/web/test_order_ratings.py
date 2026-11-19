"""SCRUM-6 Order Ratings on the storefront: My Orders "Rate order" window, tracking, chef rating.

Orders are created and delivered through the API; the customer signs in through the UI.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.web import ExplorePage, LoginPage, OrdersPage, TrackingPage
from support.api import (
    cash_order_payload,
    create_delivered_order,
    create_order,
    first_chef_and_dish,
    register_customer,
    review_order,
)
from support.config import DEFAULT_PASSWORD


@pytest.fixture
def delivered(api) -> dict:
    return create_delivered_order(api, full_name="Rating Customer")


def sign_in(page: Page, customer: dict) -> OrdersPage:
    return LoginPage(page).open().sign_in(customer["email"], DEFAULT_PASSWORD).wait_loaded()


def test_customer_rates_delivered_order_and_rating_survives_reload(page: Page, delivered):
    orders = sign_in(page, delivered)
    number = delivered["number"]

    dialog = orders.rate_order(number)
    expect(dialog.comment).to_have_attribute("placeholder", "Tell us about your order")
    dialog.submit(4, "Arrived hot, great portions")

    expect(dialog.dialog).to_be_hidden()
    expect(orders.order_rating(number)).to_have_accessible_name("Rated 4 out of 5")
    expect(orders.order_card(number)).to_contain_text("Arrived hot, great portions")
    expect(orders.rate_order_button(number)).to_have_count(0)

    orders.reload()
    expect(orders.order_rating(number)).to_have_accessible_name("Rated 4 out of 5")
    expect(orders.rate_order_button(number)).to_have_count(0)


def test_rating_is_shown_on_order_tracking(page: Page, api, delivered):
    review_order(api, delivered["token"], delivered["number"], 5, "Perfect")
    sign_in(page, delivered)

    tracking = TrackingPage(page).open_order(delivered["number"])

    expect(tracking.review_stars).to_have_accessible_name("Rated 5 out of 5")
    expect(tracking.review_section).to_contain_text("Perfect")


def test_undelivered_order_has_no_rating_option(page: Page, api):
    customer = register_customer(api, full_name="Waiting Customer")
    chef, dish = first_chef_and_dish(api)
    order = create_order(api, customer["token"], cash_order_payload(chef["id"], dish["id"]))

    orders = sign_in(page, customer)

    expect(orders.order_card(order["number"])).to_be_visible()
    expect(orders.rate_order_button(order["number"])).to_have_count(0)


def test_submit_is_disabled_until_a_star_is_chosen(page: Page, delivered):
    dialog = sign_in(page, delivered).rate_order(delivered["number"])

    expect(dialog.submit_button).to_be_disabled()
    dialog.choose(3)
    expect(dialog.submit_button).to_be_enabled()


def test_stars_work_with_the_keyboard(page: Page, delivered):
    dialog = sign_in(page, delivered).rate_order(delivered["number"])

    dialog.choose(1)
    dialog.star(1).press("ArrowRight")
    dialog.star(2).press("ArrowRight")

    expect(dialog.star(3)).to_be_checked()
    expect(dialog.submit_button).to_be_enabled()


def test_failed_save_shows_reason_and_keeps_window_open(page: Page, api, delivered):
    orders = sign_in(page, delivered)
    dialog = orders.rate_order(delivered["number"])
    # Rated in another tab meanwhile: the UI still offers the button, the backend refuses.
    review_order(api, delivered["token"], delivered["number"], 2)

    dialog.submit(5)

    expect(dialog.error).to_have_text("Order already reviewed.")
    expect(dialog.dialog).to_be_visible()
    expect(dialog.submit_button).to_be_enabled()


def test_chef_rating_on_storefront_comes_from_reviews(page: Page, api):
    chef_id = first_chef_and_dish(api)[0]["id"]
    for rating in (5, 4, 4):
        order = create_delivered_order(api, chef_id=chef_id)
        review_order(api, order["token"], order["number"], rating)

    explore = ExplorePage(page).open()

    expect(explore.chef_cards.first).to_contain_text("4.3")
