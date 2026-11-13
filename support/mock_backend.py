"""In-memory FoodMe API used by the Python API workflow tests.

This adapter implements only the HTTP contract needed by tests-python/integration. It does not
start a server, open a socket, or represent a substitute for testing the Spring backend itself.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import requests
from requests.adapters import BaseAdapter

from support.config import ADMIN_PASSWORD, ADMIN_USERNAME, DEFAULT_PASSWORD


class MockFoodMeBackend(BaseAdapter):
    """A small stateful fake for the API endpoints exercised by Python workflow tests."""

    def __init__(self) -> None:
        super().__init__()
        self.reset()

    def reset(self) -> None:
        self.customers: dict[str, dict[str, Any]] = {}
        self.customer_tokens: dict[str, str] = {}
        self.orders: dict[int, dict[str, Any]] = {}
        self.next_order_id = 1
        self.next_customer_id = 1

        self.chefs: dict[int, dict[str, Any]] = {
            1: {
                "id": 1,
                "username": "marta-k",
                "status": "ACTIVE",
                "deliveryPrice": 500,
                "freeDeliveryFrom": 5000,
                "dishes": [
                    {
                        "id": 1,
                        "nameEn": "Lavash Wrap",
                        "status": "ACTIVE",
                        "additions": [],
                    }
                ],
            }
        }

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        del kwargs
        parsed_url = urlsplit(request.url or "")
        path = parsed_url.path
        method = request.method or "GET"
        query = parse_qs(parsed_url.query)
        body = self._request_json(request)
        status, payload = self._dispatch(method, path, query, body, request.headers or {})

        response = requests.Response()
        response.status_code = status
        response.url = request.url
        response.request = request
        response.headers["Content-Type"] = "application/json"
        response.encoding = "utf-8"
        response._content = json.dumps(payload).encode("utf-8")
        return response

    def close(self) -> None:
        pass

    @staticmethod
    def _request_json(request: requests.PreparedRequest) -> dict[str, Any]:
        if not request.body:
            return {}
        raw_body = request.body
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8")
        try:
            parsed = json.loads(raw_body)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _response(status: int, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return status, payload

    def _dispatch(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        body: dict[str, Any],
        headers: Any,
    ) -> tuple[int, dict[str, Any]]:
        if method == "POST" and path == "/api/auth/register":
            return self._register(body)
        if method == "POST" and path == "/api/auth/login":
            return self._login(body)
        if method == "GET" and path == "/api/customer/me":
            customer = self._customer_from_headers(headers)
            if customer is None:
                return self._error(401, "Unauthorized")
            return 200, self._public_customer(customer)
        if method == "GET" and path == "/api/customer/orders":
            customer = self._customer_from_headers(headers)
            if customer is None:
                return self._error(401, "Unauthorized")
            orders = [order for order in self.orders.values() if order["customerId"] == customer["id"]]
            return 200, {"count": len(orders), "list": [self._public_order(o) for o in orders]}

        if method == "GET" and path == "/api/chef/active":
            chefs = [self._public_chef(chef) for chef in self.chefs.values() if chef["status"] == "ACTIVE"]
            return 200, {"count": len(chefs), "exploreChefResponseDtoList": chefs}
        chef_match = re.fullmatch(r"/api/chef/(\d+)", path)
        if method == "GET" and chef_match:
            chef = self.chefs.get(int(chef_match.group(1)))
            if chef is None:
                return self._error(404, f"Chef {chef_match.group(1)} not found")
            return 200, self._public_chef(chef, include_dishes=True)
        dish_match = re.fullmatch(r"/api/dish/(\d+)/active", path)
        if method == "GET" and dish_match:
            chef = self.chefs.get(int(dish_match.group(1)))
            if chef is None:
                return self._error(404, f"Chef {dish_match.group(1)} not found")
            dishes = [dish for dish in chef["dishes"] if dish["status"] == "ACTIVE"]
            return 200, {"count": len(dishes), "dishDtoList": dishes}

        if method == "POST" and path == "/api/order/delivery-price":
            chef_id = body.get("chefId")
            chef = self.chefs.get(chef_id) if isinstance(chef_id, int) else None
            if chef is None:
                return self._error(404, f"Chef {chef_id} not found")
            subtotal = body.get("subtotal")
            is_free = body.get("deliveryMethod") == "TAKEAWAY" or (
                subtotal is not None and subtotal >= chef["freeDeliveryFrom"]
            )
            return 200, {
                "deliveryPrice": 0 if is_free else chef["deliveryPrice"],
                "freeDeliveryFrom": chef["freeDeliveryFrom"],
            }
        if method == "POST" and path == "/api/order":
            customer = self._customer_from_headers(headers)
            if customer is None:
                return self._error(401, "Unauthorized")
            return self._create_order(body, customer)
        number_match = re.fullmatch(r"/api/order/number/([^/]+)", path)
        if method == "GET" and number_match:
            order = next((o for o in self.orders.values() if o["number"] == number_match.group(1)), None)
            if order is None:
                return self._error(404, f"Order {number_match.group(1)} not found")
            return 200, self._public_order(order)

        if method == "POST" and path == "/admin/auth/login":
            return self._admin_login(body)
        if path == "/admin/order" and method == "GET":
            if not self._is_admin(headers):
                return self._error(401, "Unauthorized")
            ordered = sorted(self.orders.values(), key=lambda order: order["createdAt"], reverse=True)
            return 200, {"count": len(ordered), "list": [self._public_order(o) for o in ordered]}
        admin_order_match = re.fullmatch(r"/admin/order/(\d+)(?:/status)?", path)
        if admin_order_match and method in {"GET", "PATCH"}:
            if not self._is_admin(headers):
                return self._error(401, "Unauthorized")
            order_id = int(admin_order_match.group(1))
            order = self.orders.get(order_id)
            if order is None:
                return self._error(404, f"Order {order_id} not found")
            if method == "GET":
                return 200, self._public_order(order)
            return self._update_order_status(order, body)

        return self._error(404, f"No mock route for {method} {path}")

    def _register(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        email = body.get("email", "")
        if any(customer["email"] == email for customer in self.customers.values()):
            return self._error(400, "Email already registered")
        customer_id = self.next_customer_id
        self.next_customer_id += 1
        token = f"customer-{customer_id}"
        customer = {
            "id": customer_id,
            "fullName": body.get("fullName", ""),
            "email": email,
            "phoneNumber": body.get("phoneNumber", ""),
            "password": body.get("password", ""),
        }
        self.customers[email] = customer
        self.customer_tokens[token] = email
        return 200, {"token": token, "customer": self._public_customer(customer)}

    def _login(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        customer = self.customers.get(body.get("email", ""))
        if customer is None or customer["password"] != body.get("password"):
            return self._error(400, "Invalid email or password")
        token = next(token for token, email in self.customer_tokens.items() if email == customer["email"])
        return 200, {"token": token, "customer": self._public_customer(customer)}

    def _admin_login(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        username = body.get("username")
        if username != ADMIN_USERNAME:
            return self._error(400, f"Unknown username: {username}")
        if body.get("password") != ADMIN_PASSWORD:
            return self._error(400, "Incorrect password")
        return 200, {"token": "mock-admin-token", "username": ADMIN_USERNAME, "role": "ADMIN"}

    def _create_order(self, body: dict[str, Any], customer: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if body.get("paymentType") != "CASH":
            return self._error(400, "Only CASH payment is supported")
        order_id = self.next_order_id
        self.next_order_id += 1
        order = {
            "id": order_id,
            "number": f"FM-{100000 + order_id}",
            "status": "NEW",
            "rejectReason": None,
            "createdAt": datetime.now().astimezone().isoformat(timespec="microseconds"),
            "customerId": customer["id"],
            "chefId": body.get("chefId"),
            "receiverName": body.get("receiverName"),
            "receiverPhoneNumber": body.get("receiverPhoneNumber"),
            "receiverEmail": body.get("receiverEmail"),
            "paymentType": body.get("paymentType"),
            "deliveryMethod": body.get("deliveryMethod"),
            "createOrderDishes": body.get("createOrderDishes", []),
        }
        self.orders[order_id] = order
        return 200, self._public_order(order)

    def _update_order_status(self, order: dict[str, Any], body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        current = order["status"]
        requested = body.get("status")
        allowed = {"NEW": {"ACCEPTED", "REJECTED"}, "ACCEPTED": {"DELIVERED", "REJECTED"}}
        if requested not in allowed.get(current, set()):
            return self._error(400, f"Cannot transition order from {current} to {requested}")
        order["status"] = requested
        order["rejectReason"] = body.get("rejectReason") if requested == "REJECTED" else None
        return 200, self._public_order(order)

    def _customer_from_headers(self, headers: Any) -> dict[str, Any] | None:
        auth = headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ")
        email = self.customer_tokens.get(token)
        return self.customers.get(email) if email else None

    @staticmethod
    def _is_admin(headers: Any) -> bool:
        return headers.get("Authorization") == "Bearer mock-admin-token"

    @staticmethod
    def _public_customer(customer: dict[str, Any]) -> dict[str, Any]:
        return {key: customer[key] for key in ("id", "fullName", "email", "phoneNumber")}

    @staticmethod
    def _public_chef(chef: dict[str, Any], include_dishes: bool = False) -> dict[str, Any]:
        result = {key: value for key, value in chef.items() if key != "dishes"}
        if include_dishes:
            result["dishes"] = chef["dishes"]
        return result

    @staticmethod
    def _public_order(order: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in order.items() if key != "customerId"}

    @staticmethod
    def _error(status: int, message: str) -> tuple[int, dict[str, Any]]:
        return status, {"message": message}
