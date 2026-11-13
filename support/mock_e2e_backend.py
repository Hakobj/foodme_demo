"""In-memory FoodMe backend for the e2e (browser) tests.

Extends the integration mock (`support/mock_backend.py`, unchanged) with:
- seed data shaped like the real API responses the storefront and back office render
  (6 chefs, 3 dishes each, dish tags, additions, images as inline SVG data URIs);
- the extra endpoints the UIs call (`/api/dish/tags`, `/admin/chef`, `/admin/dish`, ...);
- `handle_route()`, which answers a Playwright-intercepted browser request from this mock.

The same instance serves both the browser (via `context.route`) and the Python `api` fixture,
so data a test creates through the API shows up in the UI.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from playwright.sync_api import Route

from support.mock_backend import MockFoodMeBackend

CHEF_NAMES = [
    "Alans Kitchen",
    "Italiano Margarino",
    "Chef Verona",
    "Argentinean",
    "Armenian Traditional",
    "Sakura Kitchen",
]
KITCHENS = ["Comfort food", "Italian", "Desserts", "Argentinean", "Armenian", "Japanese"]
DISH_NAMES = ["House Special", "Signature Plate", "Chef's Salad"]


def _image(label: str, color: str = "#06c167") -> str:
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300'>"
        f"<rect width='100%' height='100%' fill='{color}'/>"
        f"<text x='50%' y='50%' fill='white' font-size='28' text-anchor='middle'>{label}</text></svg>"
    )
    return "data:image/svg+xml;utf8," + svg.replace("#", "%23")


def _tr(value: str) -> list[dict[str, str]]:
    return [{"lang": lang, "value": value} for lang in ("en", "hy", "ru")]


class MockE2EBackend(MockFoodMeBackend):
    def reset(self) -> None:
        super().reset()
        self.tag = {"id": 1, "nameEn": "Main", "nameHy": "Main", "nameRu": "Main"}
        self.chefs = {}
        self.dishes: dict[int, dict[str, Any]] = {}
        for index, name in enumerate(CHEF_NAMES):
            chef_id = index + 1
            dishes = [self._new_dish(chef_id, chef_id * 10 + n, dish) for n, dish in enumerate(DISH_NAMES)]
            self.dishes.update({d["id"]: d for d in dishes})
            self.chefs[chef_id] = {
                "id": chef_id,
                "username": name,
                "avatarUrl": _image(name[:1]),
                "bannerUrl": _image(name, "#333333"),
                "name": _tr(name),
                "description": _tr(f"Home cooking from {name}."),
                "kitchen": _tr(KITCHENS[index]),
                "rating": 4.5,
                "status": "ACTIVE",
                "phoneNumber": f"+3749911000{chef_id}",
                "deliveryPrice": 500,
                "freeDeliveryFrom": 5000,
                "deliveryMethods": ["DELIVERY", "TAKEAWAY"],
                "dishes": dishes,
            }

    def _new_dish(self, chef_id: int, dish_id: int, name: str) -> dict[str, Any]:
        # The second dish of every chef has additions (used by the additions / layout tests).
        additions = (
            [
                {
                    "id": dish_id * 10 + 1,
                    "nameEn": "Extra cheese",
                    "nameHy": "Extra cheese",
                    "nameRu": "Extra cheese",
                    "price": 300,
                },
                {
                    "id": dish_id * 10 + 2,
                    "nameEn": "Spicy sauce",
                    "nameHy": "Spicy sauce",
                    "nameRu": "Spicy sauce",
                    "price": 200,
                },
            ]
            if name == DISH_NAMES[1]
            else []
        )
        return {
            "id": dish_id,
            "nameEn": name,
            "nameHy": name,
            "nameRu": name,
            "descriptionEn": f"{name} cooked fresh.",
            "price": 2500,
            "url": _image(name, "#c0392b"),
            "portionEn": "350 g",
            "portionHy": "350 g",
            "portionRu": "350 g",
            "status": "ACTIVE",
            "minimumOrderCount": 1,
            "priorityIndex": dish_id,
            "chefId": chef_id,
            "dishTagDto": self.tag,
            "additions": additions,
        }

    # ---- extra endpoints -----------------------------------------------------------------

    def _dispatch(self, method, path, query, body, headers):
        if method == "GET" and path == "/api/dish/tags":
            return 200, [{"priorityIndex": 0, "dishTagDto": self.tag}]

        if path.startswith(("/admin/chef", "/admin/dish")) and not self._is_admin(headers):
            return self._error(401, "Unauthorized")
        if method == "GET" and path == "/admin/chef":
            chefs = [self._admin_chef(c) for c in self.chefs.values()]
            return 200, {"count": len(chefs), "list": chefs}
        if method == "GET" and path == "/admin/dish":
            dishes = list(self.dishes.values())
            return 200, {"count": len(dishes), "list": dishes}
        match = re.fullmatch(r"/admin/(chef|dish)/(\d+)", path)
        if match and method in {"GET", "PUT"}:
            store = self.chefs if match.group(1) == "chef" else self.dishes
            record = store.get(int(match.group(2)))
            if record is None:
                return self._error(404, "Not found")
            if method == "PUT":
                record.update({k: v for k, v in body.items() if k != "id"})
            return 200, self._admin_chef(record) if match.group(1) == "chef" else record

        return super()._dispatch(method, path, query, body, headers)

    @staticmethod
    def _admin_chef(chef: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in chef.items() if key != "dishes"}

    # ---- orders shaped like FullOrderDto --------------------------------------------------

    def _create_order(self, body, customer):
        status, payload = super()._create_order(body, customer)
        if status == 200:
            order = next(o for o in self.orders.values() if o["number"] == payload["number"])
            order["note"] = body.get("note", "")
            order["addressDto"] = body.get("addressDto")
            payload = self._public_order(order)
        return status, payload

    # The base class has this as a staticmethod; it is always called as self._public_order(...),
    # so an instance method (which needs the chef / dish data) works.
    def _public_order(self, order: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        chef = self.chefs.get(order.get("chefId") or 0, {})
        lines = []
        for line in order.get("createOrderDishes", []):
            dish = self.dishes.get(line.get("dishId"), {})
            chosen = {a.get("additionId") for a in line.get("additions") or []}
            additions = [a for a in dish.get("additions", []) if a["id"] in chosen]
            lines.append(
                {
                    "id": dish.get("id"),
                    "nameEn": dish.get("nameEn", "Unknown dish"),
                    "nameHy": dish.get("nameHy", ""),
                    "nameRu": dish.get("nameRu", ""),
                    "price": dish.get("price", 0) + sum(a["price"] for a in additions),
                    "url": dish.get("url", ""),
                    "quantity": line.get("quantity", 1),
                    "additions": additions,
                }
            )
        public = super()._public_order(order)
        public.update(
            {
                "chefName": chef.get("username", ""),
                "note": order.get("note", ""),
                "addressDto": order.get("addressDto"),
                "orderDishList": lines,
                "totalPrice": sum(line["price"] * line["quantity"] for line in lines),
            }
        )
        return public

    # ---- browser bridge -------------------------------------------------------------------

    def handle_route(self, route: Route) -> None:
        """Answers a browser request (intercepted by Playwright) from this mock, with CORS headers."""
        request = route.request
        cors = {
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": request.headers.get("access-control-request-headers", "*"),
        }
        if request.method == "OPTIONS":  # CORS preflight
            route.fulfill(status=204, headers=cors)
            return
        prepared = requests.Request(
            request.method, request.url, headers=request.headers, data=request.post_data_buffer
        ).prepare()
        response = self.send(prepared)
        route.fulfill(
            status=response.status_code,
            headers={**cors, "Content-Type": "application/json"},
            body=response.content,
        )
