"""Unit tests for the API flows in support/api.py. The `FoodMeApi` is a mock, so these check the
flow logic (which data is picked, which calls are made, how failures surface) without a backend."""

from unittest.mock import MagicMock

import pytest

from support import api as flows
from support.config import ADMIN_PASSWORD, ADMIN_USERNAME


def response(status: int = 200, body: object = None) -> MagicMock:
    res = MagicMock()
    res.status_code = status
    res.ok = status < 400
    res.json.return_value = body
    res.text = str(body)
    return res


@pytest.fixture
def api() -> MagicMock:
    return MagicMock()


def chefs_page(*chefs: dict) -> MagicMock:
    return response(body={"exploreChefResponseDtoList": list(chefs), "count": len(chefs)})


def test_register_customer_returns_token_and_generated_email(api):
    api.auth.register.return_value = response(body={"token": "tok"})

    customer = flows.register_customer(api, full_name="Ann", phone="+37490000001")

    payload = api.auth.register.call_args.args[0]
    assert customer == {"token": "tok", "email": payload["email"]}
    assert payload["fullName"] == "Ann"
    assert payload["phoneNumber"] == "+37490000001"


def test_register_customer_failure_raises_with_status(api):
    api.auth.register.return_value = response(400, {"message": "Email already registered"})

    with pytest.raises(AssertionError, match="register failed: 400"):
        flows.register_customer(api)


def test_active_chefs_returns_the_chef_list(api):
    api.chefs.active.return_value = chefs_page({"id": 1}, {"id": 2})

    assert flows.active_chefs(api, size=5) == [{"id": 1}, {"id": 2}]
    api.chefs.active.assert_called_once_with(size=5)


def test_first_chef_and_dish_picks_first_of_each(api):
    api.chefs.active.return_value = chefs_page({"id": 1}, {"id": 2})
    api.chefs.by_id.return_value = response(body={"id": 1, "dishes": [{"id": 10}, {"id": 11}]})

    chef, dish = flows.first_chef_and_dish(api)

    assert chef == {"id": 1}
    assert dish == {"id": 10}
    api.chefs.by_id.assert_called_once_with(1)


@pytest.mark.parametrize("dishes", [[], None])
def test_first_chef_and_dish_chef_without_dishes_fails_loudly(api, dishes):
    api.chefs.active.return_value = chefs_page({"id": 7})
    api.chefs.by_id.return_value = response(body={"id": 7, "dishes": dishes})

    with pytest.raises(AssertionError, match="id=7"):
        flows.first_chef_and_dish(api)


def test_find_dish_with_additions_skips_chefs_without_additions(api):
    api.chefs.active.return_value = chefs_page({"id": 1}, {"id": 2})
    details = {
        1: {"dishes": [{"nameEn": "Plain", "additions": []}]},
        2: {"dishes": [{"nameEn": "Soup"}, {"nameEn": "Khinkali", "additions": [{"id": 5}]}]},
    }
    api.chefs.by_id.side_effect = lambda chef_id: response(body=details[chef_id])

    assert flows.find_dish_with_additions(api) == (2, "Khinkali")


def test_find_dish_with_additions_only_looks_at_first_12_dishes(api):
    api.chefs.active.return_value = chefs_page({"id": 1})
    dishes = [{"nameEn": f"d{i}"} for i in range(12)] + [{"nameEn": "late", "additions": [{"id": 1}]}]
    api.chefs.by_id.return_value = response(body={"dishes": dishes})

    with pytest.raises(AssertionError, match="no active chef"):
        flows.find_dish_with_additions(api)


def test_create_order_sends_payload_with_token_and_returns_body(api):
    api.orders.create.return_value = response(body={"number": "FM-1", "status": "NEW"})

    order = flows.create_order(api, "tok", {"chefId": 1})

    assert order == {"number": "FM-1", "status": "NEW"}
    api.orders.create.assert_called_once_with({"chefId": 1}, token="tok")


def test_create_order_failure_raises_with_status(api):
    api.orders.create.return_value = response(400, {"message": "Only CASH payment is supported"})

    with pytest.raises(AssertionError, match="create order failed: 400"):
        flows.create_order(api, "tok", {})


def test_create_order_via_api_orders_first_dish_for_new_customer(api):
    api.chefs.active.return_value = chefs_page({"id": 3})
    api.chefs.by_id.return_value = response(body={"dishes": [{"id": 30}]})
    api.auth.register.return_value = response(body={"token": "tok"})
    api.orders.create.return_value = response(body={"number": "FM-2"})

    order = flows.create_order_via_api(api, name="Zara", note="n")

    payload = api.orders.create.call_args.args[0]
    assert order == {"number": "FM-2"}
    assert payload["chefId"] == 3
    assert payload["createOrderDishes"] == [{"dishId": 30, "quantity": 1}]
    assert payload["receiverName"] == "Zara"
    assert payload["note"] == "n"
    assert api.orders.create.call_args.kwargs == {"token": "tok"}


def test_admin_token_logs_in_with_seeded_credentials(api):
    api.admin.login.return_value = response(body={"token": "admin-tok"})

    assert flows.admin_token(api) == "admin-tok"
    api.admin.login.assert_called_once_with(ADMIN_USERNAME, ADMIN_PASSWORD)


def test_admin_token_empty_token_fails(api):
    api.admin.login.return_value = response(body={"token": ""})

    with pytest.raises(AssertionError):
        flows.admin_token(api)
