"""Back-office REST API (/admin/**) against the running backend: admin login, order list and
the order status workflow (NEW -> ACCEPTED -> DELIVERED, NEW/ACCEPTED -> REJECTED)."""

import pytest

from support.api import admin_token, create_order_via_api
from support.config import ADMIN_PASSWORD, ADMIN_USERNAME

UNKNOWN_ORDER_ID = 999_999_999


@pytest.fixture(scope="module")
def token(api) -> str:
    return admin_token(api)


@pytest.fixture
def new_order(api) -> dict:
    """A fresh NEW order with its admin id (the create response only carries the number)."""
    number = create_order_via_api(api)["number"]
    res = api.orders.by_number(number)
    assert res.ok, res.text
    return res.json()


# ---- auth ---------------------------------------------------------------------------------


def test_admin_login_returns_token_username_and_role(api):
    res = api.admin.login(ADMIN_USERNAME, ADMIN_PASSWORD)

    assert res.status_code == 200
    body = res.json()
    assert body["token"]
    assert body["username"] == ADMIN_USERNAME
    assert body["role"]


def test_admin_login_wrong_password_rejected(api):
    res = api.admin.login(ADMIN_USERNAME, "wrong-password")

    assert res.status_code == 400
    assert res.json()["message"] == "Incorrect password"


def test_admin_login_unknown_username_rejected(api):
    res = api.admin.login("nobody-here", ADMIN_PASSWORD)

    assert res.status_code == 400
    assert res.json()["message"] == "Unknown username: nobody-here"


@pytest.mark.parametrize("bad_token", [None, "not-a-jwt"])
def test_admin_orders_without_valid_token_unauthorized(api, bad_token):
    res = api.admin.orders(bad_token)

    assert res.status_code == 401


# ---- orders -------------------------------------------------------------------------------


def test_admin_orders_list_contains_a_new_api_order(api, token, new_order):
    res = api.admin.orders(token, page=0, size=50)

    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    numbers = [o["number"] for o in body["list"]]
    assert new_order["number"] in numbers


def test_admin_orders_list_is_newest_first(api, token, new_order):
    res = api.admin.orders(token, page=0, size=20)

    created = [o["createdAt"] for o in res.json()["list"]]
    assert created == sorted(created, reverse=True)


def test_admin_order_by_id_returns_the_order(api, token, new_order):
    res = api.admin.order_by_id(token, new_order["id"])

    assert res.status_code == 200
    assert res.json()["number"] == new_order["number"]
    assert res.json()["status"] == "NEW"


def test_admin_order_by_unknown_id_not_found(api, token):
    res = api.admin.order_by_id(token, UNKNOWN_ORDER_ID)

    assert res.status_code == 404
    assert res.json()["message"] == f"Order {UNKNOWN_ORDER_ID} not found"


# ---- status workflow ----------------------------------------------------------------------


def test_order_can_go_new_accepted_delivered(api, token, new_order):
    accepted = api.admin.update_order_status(token, new_order["id"], "ACCEPTED")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"

    delivered = api.admin.update_order_status(token, new_order["id"], "DELIVERED")
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "DELIVERED"

    # Persisted: the public lookup sees the final status too.
    assert api.orders.by_number(new_order["number"]).json()["status"] == "DELIVERED"


def test_reject_new_order_stores_reject_reason(api, token, new_order):
    res = api.admin.update_order_status(token, new_order["id"], "REJECTED", reject_reason="Chef is sick")

    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"
    assert res.json()["rejectReason"] == "Chef is sick"


def test_new_order_cannot_skip_to_delivered(api, token, new_order):
    res = api.admin.update_order_status(token, new_order["id"], "DELIVERED")

    assert res.status_code == 400
    assert res.json()["message"] == "Cannot transition order from NEW to DELIVERED"


def test_delivered_order_is_final(api, token, new_order):
    api.admin.update_order_status(token, new_order["id"], "ACCEPTED")
    api.admin.update_order_status(token, new_order["id"], "DELIVERED")

    res = api.admin.update_order_status(token, new_order["id"], "REJECTED", reject_reason="too late")

    assert res.status_code == 400
    assert res.json()["message"] == "Cannot transition order from DELIVERED to REJECTED"


def test_status_change_requires_admin_token(api, new_order):
    res = api.admin.update_order_status("", new_order["id"], "ACCEPTED")

    assert res.status_code == 401
