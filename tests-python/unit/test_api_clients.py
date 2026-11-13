"""Unit tests for the API client objects in clients/: each method must hit the right URL with the
right method, body, params and auth header. The HTTP session is a mock, so nothing is sent."""

from unittest.mock import MagicMock

import pytest
import requests

from clients import FoodMeApi
from clients.base import bearer

BASE = "http://backend.test"


@pytest.fixture
def session() -> MagicMock:
    return MagicMock(spec=requests.Session)


@pytest.fixture
def api(session) -> FoodMeApi:
    return FoodMeApi(session, BASE)


def test_bearer_with_token_builds_authorization_header():
    assert bearer("abc") == {"Authorization": "Bearer abc"}


@pytest.mark.parametrize("token", [None, ""])
def test_bearer_without_token_is_empty(token):
    assert bearer(token) == {}


def test_facade_shares_one_session_and_base_url(api, session):
    clients = [api.auth, api.customer, api.chefs, api.dishes, api.orders, api.admin]

    assert all(c.session is session for c in clients)
    assert all(c.base_url == BASE for c in clients)


def test_client_returns_the_raw_response(api, session):
    response = MagicMock(spec=requests.Response)
    session.get.return_value = response

    assert api.chefs.by_id(1) is response


def test_auth_register_posts_payload_without_auth(api, session):
    api.auth.register({"email": "a@example.com"})

    session.post.assert_called_once_with(f"{BASE}/api/auth/register", json={"email": "a@example.com"}, headers={})


def test_auth_login_posts_email_and_password(api, session):
    api.auth.login("a@example.com", "pw")

    session.post.assert_called_once_with(
        f"{BASE}/api/auth/login", json={"email": "a@example.com", "password": "pw"}, headers={}
    )


def test_customer_me_sends_bearer_token(api, session):
    api.customer.me("tok")

    session.get.assert_called_once_with(f"{BASE}/api/customer/me", headers={"Authorization": "Bearer tok"})


def test_customer_orders_without_token_sends_no_auth_header(api, session):
    api.customer.orders()

    session.get.assert_called_once_with(f"{BASE}/api/customer/orders", headers={})


def test_chefs_active_uses_default_paging(api, session):
    api.chefs.active()

    session.get.assert_called_once_with(f"{BASE}/api/chef/active", headers={}, params={"page": 0, "size": 12})


def test_chefs_by_id_puts_id_in_path(api, session):
    api.chefs.by_id(42)

    session.get.assert_called_once_with(f"{BASE}/api/chef/42", headers={})


def test_dishes_active_for_chef_passes_paging(api, session):
    api.dishes.active_for_chef(5, page=2, size=10)

    session.get.assert_called_once_with(f"{BASE}/api/dish/5/active", headers={}, params={"page": 2, "size": 10})


def test_orders_create_posts_payload_with_token(api, session):
    api.orders.create({"chefId": 1}, token="tok")

    session.post.assert_called_once_with(
        f"{BASE}/api/order", json={"chefId": 1}, headers={"Authorization": "Bearer tok"}
    )


def test_orders_by_number_puts_number_in_path(api, session):
    api.orders.by_number("FM-100001")

    session.get.assert_called_once_with(f"{BASE}/api/order/number/FM-100001", headers={})


def test_orders_delivery_price_posts_request_body(api, session):
    api.orders.delivery_price(3, 5000.0, "DELIVERY")

    session.post.assert_called_once_with(
        f"{BASE}/api/order/delivery-price",
        json={"chefId": 3, "subtotal": 5000.0, "deliveryMethod": "DELIVERY"},
        headers={},
    )


def test_admin_login_posts_username_and_password(api, session):
    api.admin.login("admin", "pw")

    session.post.assert_called_once_with(
        f"{BASE}/admin/auth/login", json={"username": "admin", "password": "pw"}, headers={}
    )


def test_admin_orders_sends_token_and_paging(api, session):
    api.admin.orders("tok", page=1, size=5)

    session.get.assert_called_once_with(
        f"{BASE}/admin/order", headers={"Authorization": "Bearer tok"}, params={"page": 1, "size": 5}
    )


def test_admin_order_by_id_sends_token(api, session):
    api.admin.order_by_id("tok", 9)

    session.get.assert_called_once_with(f"{BASE}/admin/order/9", headers={"Authorization": "Bearer tok"})


def test_admin_update_order_status_patches_status_and_reason(api, session):
    api.admin.update_order_status("tok", 9, "REJECTED", reject_reason="out of stock")

    session.patch.assert_called_once_with(
        f"{BASE}/admin/order/9/status",
        json={"status": "REJECTED", "rejectReason": "out of stock"},
        headers={"Authorization": "Bearer tok"},
    )
