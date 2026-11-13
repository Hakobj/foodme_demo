"""Unit tests for the test-data builders in support/api.py (pure functions, no I/O)."""

import re

from support.api import cash_order_payload, register_payload, unique_email
from support.config import DEFAULT_PASSWORD


def test_unique_email_uses_prefix_and_example_domain():
    email = unique_email("ann")

    assert re.fullmatch(r"ann-\d+-\d+-[0-9a-f]{6}@example\.com", email)


def test_unique_email_default_prefix_is_api():
    assert unique_email().startswith("api-")


def test_unique_email_is_different_on_each_call():
    emails = {unique_email() for _ in range(50)}

    assert len(emails) == 50


def test_register_payload_uses_default_phone_and_password():
    payload = register_payload("Ann Test", "ann@example.com")

    assert payload == {
        "fullName": "Ann Test",
        "email": "ann@example.com",
        "phoneNumber": "+37491234567",
        "password": DEFAULT_PASSWORD,
    }


def test_register_payload_overrides_phone_and_password():
    payload = register_payload("Ann", "a@example.com", phone="+37400000000", password="other123")

    assert payload["phoneNumber"] == "+37400000000"
    assert payload["password"] == "other123"


def test_cash_order_payload_defaults_to_cash_takeaway_with_one_dish():
    payload = cash_order_payload(chef_id=3, dish_id=7)

    assert payload["chefId"] == 3
    assert payload["paymentType"] == "CASH"
    assert payload["deliveryMethod"] == "TAKEAWAY"
    assert payload["createOrderDishes"] == [{"dishId": 7, "quantity": 1}]
    assert payload["note"] == "ring twice"


def test_cash_order_payload_passes_quantity_and_receiver_fields():
    payload = cash_order_payload(1, 2, quantity=4, receiver_name="Bob", phone="+37499999999", email="b@example.com")

    assert payload["createOrderDishes"][0]["quantity"] == 4
    assert payload["receiverName"] == "Bob"
    assert payload["receiverPhoneNumber"] == "+37499999999"
    assert payload["receiverEmail"] == "b@example.com"


def test_cash_order_payload_without_note_omits_the_key():
    payload = cash_order_payload(1, 2, note=None)

    assert "note" not in payload


def test_cash_order_payload_allows_other_payment_type():
    assert cash_order_payload(1, 2, payment_type="CARD")["paymentType"] == "CARD"
