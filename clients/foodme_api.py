"""One client per backend controller, grouped behind the `FoodMeApi` facade (the `api` fixture)."""

import requests

from clients.base import BaseClient


class AuthClient(BaseClient):
    """`/api/auth` — customer sign-up and login."""

    def register(self, payload: dict) -> requests.Response:
        return self._post("/api/auth/register", json=payload)

    def login(self, email: str, password: str) -> requests.Response:
        return self._post("/api/auth/login", json={"email": email, "password": password})


class CustomerClient(BaseClient):
    """`/api/customer` — endpoints that need a customer JWT."""

    def me(self, token: str | None = None) -> requests.Response:
        return self._get("/api/customer/me", token=token)

    def orders(self, token: str | None = None) -> requests.Response:
        return self._get("/api/customer/orders", token=token)


class ChefClient(BaseClient):
    """`/api/chef`."""

    def active(self, page: int = 0, size: int = 12) -> requests.Response:
        return self._get("/api/chef/active", params={"page": page, "size": size})

    def by_id(self, chef_id: int) -> requests.Response:
        return self._get(f"/api/chef/{chef_id}")


class DishClient(BaseClient):
    """`/api/dish`."""

    def active_for_chef(self, chef_id: int, page: int = 0, size: int = 50) -> requests.Response:
        return self._get(f"/api/dish/{chef_id}/active", params={"page": page, "size": size})


class OrderClient(BaseClient):
    """`/api/order`."""

    def create(self, payload: dict, token: str | None = None) -> requests.Response:
        return self._post("/api/order", json=payload, token=token)

    def by_number(self, number: str) -> requests.Response:
        return self._get(f"/api/order/number/{number}")

    def delivery_price(self, chef_id: int, subtotal: float | None, delivery_method: str) -> requests.Response:
        return self._post(
            "/api/order/delivery-price",
            json={"chefId": chef_id, "subtotal": subtotal, "deliveryMethod": delivery_method},
        )


class AdminClient(BaseClient):
    """`/admin/**` — back-office REST API."""

    def login(self, username: str, password: str) -> requests.Response:
        return self._post("/admin/auth/login", json={"username": username, "password": password})

    def orders(self, token: str, page: int = 0, size: int = 20) -> requests.Response:
        return self._get("/admin/order", token=token, params={"page": page, "size": size})

    def order_by_id(self, token: str, order_id: int) -> requests.Response:
        return self._get(f"/admin/order/{order_id}", token=token)

    def update_order_status(
        self, token: str, order_id: int, status: str, reject_reason: str | None = None
    ) -> requests.Response:
        return self._patch(
            f"/admin/order/{order_id}/status", json={"status": status, "rejectReason": reject_reason}, token=token
        )


class FoodMeApi:
    """Facade over all clients, sharing one HTTP session."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url
        self.auth = AuthClient(session, base_url)
        self.customer = CustomerClient(session, base_url)
        self.chefs = ChefClient(session, base_url)
        self.dishes = DishClient(session, base_url)
        self.orders = OrderClient(session, base_url)
        self.admin = AdminClient(session, base_url)
