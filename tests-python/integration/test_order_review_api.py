"""SCRUM-6 Order Ratings: POST /api/customer/orders/{number}/review.

Covers the PRD acceptance criteria at API level: rate a delivered order, only own / delivered /
once, 1-5 whole stars, comment <= 1000 chars, signed-in only, chef rating = rounded average,
and the rating shown wherever the order is shown.
"""

import pytest

from support.api import (
    admin_token,
    cash_order_payload,
    chef_detail,
    create_delivered_order,
    create_order,
    first_chef_and_dish,
    register_customer,
    review_order,
    review_payload,
)

ONLY_DELIVERED = "Only delivered orders can be reviewed."
ALREADY_REVIEWED = "Order already reviewed."
RATING_MESSAGE = "Rating must be a whole number from 1 to 5"
COMMENT_MESSAGE = "Comment must be at most 1000 characters"


@pytest.fixture
def delivered(api) -> dict:
    """A fresh customer with one DELIVERED order: {"token", "email", "number", "chef_id"}."""
    return create_delivered_order(api)


@pytest.fixture
def new_order(api) -> dict:
    """A fresh customer with one NEW (not delivered) order."""
    chef, dish = first_chef_and_dish(api)
    customer = register_customer(api, full_name="Undelivered Customer")
    order = create_order(api, customer["token"], cash_order_payload(chef["id"], dish["id"]))
    return {**customer, "number": order["number"]}


# ---- happy path -----------------------------------------------------------------------------


def test_customer_rates_delivered_order_with_stars_and_comment(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload(5, "Hot and on time"), token=delivered["token"])

    assert res.status_code == 200
    body = res.json()
    assert body["rating"] == 5
    assert body["comment"] == "Hot and on time"
    assert body["createdAt"]


def test_comment_is_optional(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload(4), token=delivered["token"])

    assert res.status_code == 200
    assert res.json()["rating"] == 4
    assert res.json()["comment"] is None


@pytest.mark.parametrize("rating", [1, 5])
def test_boundary_ratings_are_accepted(api, delivered, rating):
    res = api.customer.review_order(delivered["number"], review_payload(rating), token=delivered["token"])

    assert res.status_code == 200
    assert res.json()["rating"] == rating


def test_comment_of_exactly_1000_characters_is_accepted(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload(3, "x" * 1000), token=delivered["token"])

    assert res.status_code == 200
    assert len(res.json()["comment"]) == 1000


# ---- the rating is shown wherever the order is shown (R13) -----------------------------------


def test_review_is_returned_in_my_orders_tracking_and_admin(api, delivered):
    review_order(api, delivered["token"], delivered["number"], 4, "Good")

    my_orders = api.customer.orders(delivered["token"]).json()["list"]
    assert my_orders[0]["review"]["rating"] == 4
    assert my_orders[0]["review"]["comment"] == "Good"

    tracked = api.orders.by_number(delivered["number"]).json()
    assert tracked["review"]["rating"] == 4

    admin_order = api.admin.order_by_id(admin_token(api), tracked["id"]).json()
    assert admin_order["review"]["rating"] == 4
    assert admin_order["review"]["comment"] == "Good"
    assert admin_order["review"]["createdAt"]


def test_unrated_order_has_no_review(api, delivered):
    tracked = api.orders.by_number(delivered["number"]).json()

    assert tracked["review"] is None


# ---- who can rate ---------------------------------------------------------------------------


def test_not_signed_in_cannot_rate(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload(5))

    assert res.status_code == 401


def test_undelivered_order_cannot_be_rated(api, new_order):
    res = api.customer.review_order(new_order["number"], review_payload(5), token=new_order["token"])

    assert res.status_code == 400
    assert res.json()["message"] == ONLY_DELIVERED


def test_rejected_order_cannot_be_rated(api, new_order):
    token = admin_token(api)
    order_id = api.orders.by_number(new_order["number"]).json()["id"]
    assert api.admin.update_order_status(token, order_id, "REJECTED", "Out of stock").ok

    res = api.customer.review_order(new_order["number"], review_payload(5), token=new_order["token"])

    assert res.status_code == 400
    assert res.json()["message"] == ONLY_DELIVERED


def test_order_can_be_rated_only_once(api, delivered):
    review_order(api, delivered["token"], delivered["number"], 5)

    res = api.customer.review_order(delivered["number"], review_payload(1), token=delivered["token"])

    assert res.status_code == 400
    assert res.json()["message"] == ALREADY_REVIEWED
    # The first rating is kept.
    assert api.orders.by_number(delivered["number"]).json()["review"]["rating"] == 5


def test_someone_elses_order_looks_like_it_does_not_exist(api, delivered):
    stranger = register_customer(api, full_name="Stranger")

    res = api.customer.review_order(delivered["number"], review_payload(1), token=stranger["token"])
    missing = api.customer.review_order("FM-999999", review_payload(1), token=stranger["token"])

    assert res.status_code == 404
    assert res.json()["message"] == f"Order {delivered['number']} not found"
    assert missing.status_code == 404
    assert api.orders.by_number(delivered["number"]).json()["review"] is None


# ---- validation -----------------------------------------------------------------------------


@pytest.mark.parametrize("rating", [0, 6, -1, 4.5, 2.01, None], ids=lambda r: f"rating={r}")
def test_rating_outside_1_to_5_whole_stars_is_refused(api, delivered, rating):
    res = api.customer.review_order(delivered["number"], review_payload(rating), token=delivered["token"])

    assert res.status_code == 400
    assert res.json()["message"] == RATING_MESSAGE
    assert api.orders.by_number(delivered["number"]).json()["review"] is None


def test_non_numeric_rating_is_refused(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload("five"), token=delivered["token"])

    assert res.status_code == 400


def test_comment_longer_than_1000_characters_is_refused(api, delivered):
    res = api.customer.review_order(delivered["number"], review_payload(5, "x" * 1001), token=delivered["token"])

    assert res.status_code == 400
    assert res.json()["message"] == COMMENT_MESSAGE


# ---- chef rating (R10, R11) -----------------------------------------------------------------


def test_chef_rating_is_average_of_reviews_rounded_to_one_decimal(api):
    """Expects a chef with no earlier reviews (fresh database or the in-memory mock): 5, 4, 4 -> 4.3."""
    chef_id = first_chef_and_dish(api)[0]["id"]

    for rating in (5, 4, 4):
        order = create_delivered_order(api, chef_id=chef_id)
        review_order(api, order["token"], order["number"], rating)

    assert chef_detail(api, chef_id)["rating"] == 4.3


def test_chef_rating_follows_the_first_review_instead_of_the_static_value(api):
    """Expects a chef with no earlier reviews (fresh database or the in-memory mock)."""
    chef_id = first_chef_and_dish(api)[0]["id"]
    order = create_delivered_order(api, chef_id=chef_id)

    review_order(api, order["token"], order["number"], 2)

    assert chef_detail(api, chef_id)["rating"] == 2.0
