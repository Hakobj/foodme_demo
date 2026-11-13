"""POST /api/order/delivery-price and GET /api/order/number/{n} against the running backend.

The chef is looked up through the API (one with a paid delivery and a free-delivery threshold),
so the tests don't depend on fixed seed IDs.
"""

import pytest

from support.api import active_chefs

UNKNOWN_CHEF_ID = 999_999_999


@pytest.fixture(scope="module")
def chef(api) -> dict:
    """An active chef whose delivery costs money and who has a free-delivery threshold."""
    chefs = [c for c in active_chefs(api, size=50) if (c.get("deliveryPrice") or 0) > 0 and c.get("freeDeliveryFrom")]
    if not chefs:
        pytest.skip("no active chef with a paid delivery and a freeDeliveryFrom threshold in the seed")
    return chefs[0]


def test_takeaway_is_always_free(api, chef):
    res = api.orders.delivery_price(chef["id"], chef["freeDeliveryFrom"] - 1, "TAKEAWAY")

    assert res.status_code == 200
    assert res.json()["deliveryPrice"] == 0
    assert res.json()["freeDeliveryFrom"] == chef["freeDeliveryFrom"]


def test_delivery_below_threshold_costs_the_chef_delivery_price(api, chef):
    res = api.orders.delivery_price(chef["id"], chef["freeDeliveryFrom"] - 1, "DELIVERY")

    assert res.status_code == 200
    assert res.json()["deliveryPrice"] == chef["deliveryPrice"]


def test_delivery_above_threshold_is_free(api, chef):
    res = api.orders.delivery_price(chef["id"], chef["freeDeliveryFrom"] + 1, "DELIVERY")

    assert res.status_code == 200
    assert res.json()["deliveryPrice"] == 0


# FM-BUG-03: "free from X" should include X itself; the backend compares with `>` instead of `>=`.
def test_delivery_exactly_at_threshold_is_free(api, chef):
    res = api.orders.delivery_price(chef["id"], chef["freeDeliveryFrom"], "DELIVERY")

    assert res.status_code == 200
    assert res.json()["deliveryPrice"] == 0


def test_delivery_without_subtotal_costs_the_chef_delivery_price(api, chef):
    res = api.orders.delivery_price(chef["id"], None, "DELIVERY")

    assert res.status_code == 200
    assert res.json()["deliveryPrice"] == chef["deliveryPrice"]


def test_delivery_price_unknown_chef_not_found(api):
    res = api.orders.delivery_price(UNKNOWN_CHEF_ID, 1000, "DELIVERY")

    assert res.status_code == 404
    assert res.json()["message"] == f"Chef {UNKNOWN_CHEF_ID} not found"


def test_order_by_unknown_number_not_found(api):
    res = api.orders.by_number("FM-000000")

    assert res.status_code == 404
    assert res.json()["message"] == "Order FM-000000 not found"
