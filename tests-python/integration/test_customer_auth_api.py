"""Port of CustomerAuthControllerTest.java."""

from support.api import register_payload, unique_email
from support.config import DEFAULT_PASSWORD


def test_register_returns_token_and_profile(api):
    email = unique_email("ann")
    res = api.auth.register(register_payload("Ann Test", email))

    assert res.status_code == 200
    body = res.json()
    assert body["token"]
    assert body["customer"]["email"] == email
    assert body["customer"]["fullName"] == "Ann Test"


def test_register_duplicate_email_rejected(api):
    email = unique_email("ann")
    assert api.auth.register(register_payload("Ann", email)).status_code == 200

    res = api.auth.register(register_payload("Ann", email))

    assert res.status_code == 400
    assert res.json()["message"] == "Email already registered"


def test_login_with_registered_account_succeeds(api):
    email = unique_email("ann")
    assert api.auth.register(register_payload("Ann", email)).status_code == 200

    res = api.auth.login(email, DEFAULT_PASSWORD)

    assert res.status_code == 200
    assert res.json()["token"]
    assert res.json()["customer"]["email"] == email


def test_login_wrong_password_rejected(api):
    email = unique_email("ann")
    assert api.auth.register(register_payload("Ann", email)).status_code == 200

    res = api.auth.login(email, "nope1234")

    assert res.status_code == 400
    assert res.json()["message"] == "Invalid email or password"


def test_me_and_orders_require_customer_token(api):
    assert api.customer.me().status_code == 401
    assert api.customer.orders().status_code == 401

    email = unique_email("ann")
    register = api.auth.register(register_payload("Ann", email))
    assert register.status_code == 200
    token = register.json()["token"]

    me = api.customer.me(token)
    assert me.status_code == 200
    assert me.json()["email"] == email

    orders = api.customer.orders(token)
    assert orders.status_code == 200
    assert orders.json()["count"] == 0
    assert isinstance(orders.json()["list"], list)
