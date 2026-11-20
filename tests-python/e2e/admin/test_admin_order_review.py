"""SCRUM-6 Order Ratings in the back office: the "Customer review" section on order details
and the stars in the order list. Runs serially (shared seeded admin)."""

from playwright.sync_api import Page, expect

from pages.admin import AdminLoginPage, OrdersListPage
from support.api import create_delivered_order, create_order_via_api, review_order


def test_rated_order_shows_stars_comment_and_date(page: Page, api):
    order = create_delivered_order(api, full_name="Admin Review Customer")
    review_order(api, order["token"], order["number"], 2, "Cold when it arrived")
    AdminLoginPage(page).login_as_admin()

    orders = OrdersListPage(page).open().refresh()
    expect(orders.order_rating(order["number"])).to_have_accessible_name("Rated 2 out of 5")
    show = orders.open_order(order["number"])

    expect(show.customer_review).to_be_visible()
    expect(show.review_stars(2)).to_be_visible()
    expect(show.review_comment("Cold when it arrived")).to_be_visible()
    expect(show.no_review_text).to_have_count(0)


def test_delivered_unrated_order_says_no_review_yet(page: Page, api):
    order = create_delivered_order(api, full_name="Admin Unrated Customer")
    AdminLoginPage(page).login_as_admin()

    show = OrdersListPage(page).open().refresh().open_order(order["number"])

    expect(show.no_review_text).to_be_visible()


def test_review_section_is_hidden_for_undelivered_order(page: Page, api):
    number = create_order_via_api(api)["number"]
    AdminLoginPage(page).login_as_admin()

    show = OrdersListPage(page).open().refresh().open_order(number)

    expect(show.heading(number)).to_be_visible()
    expect(show.customer_review).to_have_count(0)
