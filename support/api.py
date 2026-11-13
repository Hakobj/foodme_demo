"""Test data builders and API flows shared by all suites (port of e2e/auth.ts and the Java test
helpers). Flows go through the `clients.FoodMeApi` client objects."""

import random
import time
import uuid

from clients import FoodMeApi
from support.config import ADMIN_PASSWORD, ADMIN_USERNAME, DEFAULT_PASSWORD

# ---- data builders -------------------------------------------------------------------------


def unique_email(prefix: str = "api") -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{random.randint(0, 999_999)}-{uuid.uuid4().hex[:6]}@example.com"


def register_payload(full_name: str, email: str, phone: str = "+37491234567", password: str = DEFAULT_PASSWORD) -> dict:
    return {"fullName": full_name, "email": email, "phoneNumber": phone, "password": password}


def cash_order_payload(
    chef_id: int,
    dish_id: int,
    quantity: int = 1,
    receiver_name: str = "Ann",
    phone: str = "+37491234567",
    email: str = "ann@example.com",
    note: str | None = "ring twice",
    payment_type: str = "CASH",
) -> dict:
    body = {
        "chefId": chef_id,
        "receiverName": receiver_name,
        "receiverPhoneNumber": phone,
        "receiverEmail": email,
        "paymentType": payment_type,
        "deliveryMethod": "TAKEAWAY",
        "createOrderDishes": [{"dishId": dish_id, "quantity": quantity}],
    }
    if note is not None:
        body["note"] = note
    return body


# ---- flows (preconditions; they assert so a broken setup fails loudly) ----------------------


def register_customer(api: FoodMeApi, full_name: str = "E2E Customer", phone: str = "+37490000000") -> dict:
    """Registers a fresh customer and returns {"token", "email"}."""
    email = unique_email()
    res = api.auth.register(register_payload(full_name, email, phone))
    assert res.ok, f"register failed: {res.status_code} {res.text}"
    return {"token": res.json()["token"], "email": email}


def active_chefs(api: FoodMeApi, size: int = 12) -> list:
    res = api.chefs.active(size=size)
    assert res.ok, res.text
    return res.json()["exploreChefResponseDtoList"]


def chef_detail(api: FoodMeApi, chef_id: int) -> dict:
    res = api.chefs.by_id(chef_id)
    assert res.ok, res.text
    return res.json()


def first_chef_and_dish(api: FoodMeApi) -> tuple[dict, dict]:
    chef = active_chefs(api)[0]
    dishes = chef_detail(api, chef["id"]).get("dishes") or []
    assert dishes, f"first active chef (id={chef['id']}) has no dishes"
    return chef, dishes[0]


def find_dish_with_additions(api: FoodMeApi) -> tuple[int, str]:
    """Returns (chef_id, dish_name) for a dish early in a chef's menu that has additions."""
    for chef in active_chefs(api):
        dishes = (chef_detail(api, chef["id"]).get("dishes") or [])[:12]
        found = next((d for d in dishes if d.get("additions")), None)
        if found:
            return chef["id"], found["nameEn"]
    raise AssertionError("no active chef has a dish with additions")


def create_order(api: FoodMeApi, token: str, payload: dict) -> dict:
    res = api.orders.create(payload, token=token)
    assert res.ok, f"create order failed: {res.status_code} {res.text}"
    return res.json()


def create_order_via_api(
    api: FoodMeApi,
    name: str = "Admin E2E",
    phone: str = "+37495555666",
    email: str = "admin-e2e@example.com",
    note: str = "admin e2e order",
) -> dict:
    """Port of createOrderViaApi: fresh customer + CASH/TAKEAWAY order for the first chef's first dish."""
    chef, dish = first_chef_and_dish(api)
    customer = register_customer(api, full_name=name, phone=phone)
    return create_order(
        api,
        customer["token"],
        cash_order_payload(chef["id"], dish["id"], receiver_name=name, phone=phone, email=email, note=note),
    )


def admin_token(api: FoodMeApi) -> str:
    res = api.admin.login(ADMIN_USERNAME, ADMIN_PASSWORD)
    assert res.ok, res.text
    token = res.json()["token"]
    assert token
    return token
