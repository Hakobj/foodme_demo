"""Port of OrderControllerTest.java.

Tests are defined in the same order the JUnit class runs them (@Order 1..5, then the rest);
pytest runs them in file order.
"""

from datetime import date

import pytest

from support.api import cash_order_payload, first_chef_and_dish, register_customer


@pytest.fixture
def customer_token(api):
    return register_customer(api, full_name="Ann", phone="+37491234567")["token"]


@pytest.fixture(scope="module")
def cash_order(api):
    chef, dish = first_chef_and_dish(api)
    return cash_order_payload(chef["id"], dish["id"], quantity=2)


# FM-FLAKE-02
def test_create_order_first_order_gets_number_100001(api, customer_token, cash_order):
    res = api.orders.create(cash_order, token=customer_token)

    assert res.status_code == 200
    assert res.json()["number"] == "FM-100001"


# FM-FLAKE-02
def test_get_order_by_number_first_order_is_fm100001(api, customer_token, cash_order):
    api.orders.create(cash_order, token=customer_token)

    res = api.orders.by_number("FM-100001")

    assert res.status_code == 200
    assert res.json()["number"] == "FM-100001"


def test_create_order_cash_payment_succeeds(api, customer_token, cash_order):
    res = api.orders.create(cash_order, token=customer_token)

    assert res.status_code == 200
    assert res.json()["status"] == "NEW"
    number = res.json()["number"]
    assert number

    # Persistence: read it back. Count is scoped to this fresh customer.
    orders = api.customer.orders(customer_token)
    assert orders.status_code == 200
    assert orders.json()["count"] == 1
    assert orders.json()["list"][0]["number"] == number


def test_create_order_non_cash_payment_rejected_with_bad_request(api, customer_token, cash_order):
    body = {
        **cash_order,
        "paymentType": "CARD",
        "createOrderDishes": [{**cash_order["createOrderDishes"][0], "quantity": 1}],
    }
    body.pop("note", None)

    res = api.orders.create(body, token=customer_token)

    assert res.status_code == 400
    assert res.json()["message"] == "Only CASH payment is supported"


# FM-FLAKE-04
def test_create_order_created_at_falls_on_today(api, customer_token, cash_order):
    res = api.orders.create(cash_order, token=customer_token)
    assert res.status_code == 200
    number = res.json()["number"]

    order = api.orders.by_number(number)
    assert order.status_code == 200

    assert order.json()["createdAt"].startswith(date.today().isoformat())


def test_create_order_without_token_unauthorized(api, cash_order):
    res = api.orders.create(cash_order)

    assert res.status_code == 401
