"""Benchmark changes for `python -m selection evaluate`. Each one is a small, realistic regression
(find -> replace in one file). Seeded `FM-BUG-NN` code is left alone.

`ground_truth=False` marks changes the mock-backed e2e run cannot fail on (backend code, docs,
build config): they are scored for selection size and the decision only, not for detection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mutation:
    id: str
    file: str
    find: str
    replace: str
    description: str
    ground_truth: bool = True


MUTATIONS = [
    # ---- storefront (apps/web) ------------------------------------------------------------
    Mutation(
        "web-explore-kitchen-search",
        "apps/web/src/pages/Explore/index.tsx",
        "return name.includes(q) || kitchen.toLowerCase().includes(q);",
        "return name.includes(q);",
        "Explore search no longer matches the kitchen",
    ),
    Mutation(
        "web-cart-free-delivery-boundary",
        "apps/web/src/components/sections/user-cart.tsx",
        "(freeDeliveryFrom <= 0 || subtotal < freeDeliveryFrom)",
        "(freeDeliveryFrom <= 0 || subtotal <= freeDeliveryFrom)",
        "Cart charges delivery at exactly the free-delivery threshold",
    ),
    Mutation(
        "web-modal-additions-price",
        "apps/web/src/components/sections/dish-modal.tsx",
        ".reduce((sum, a) => sum + a.price, 0);\n    }\n    return t;",
        ".reduce((sum, a) => sum + 0 * a.price, 0);\n    }\n    return t;",
        "Dish modal ignores addition prices in the live total",
    ),
    Mutation(
        "web-checkout-city-message",
        "apps/web/src/schemas/checkout-schema.ts",
        'message: "City is required"',
        'message: "City required"',
        "Checkout validation message for city changed",
    ),
    Mutation(
        "web-tracking-accepted-copy",
        "apps/web/src/pages/Tracking/index.tsx",
        'title: "Preparing your order"',
        'title: "Cooking your order"',
        "Tracking title for ACCEPTED orders changed",
    ),
    Mutation(
        "web-header-search-trim",
        "apps/web/src/components/layout/header.tsx",
        '.get("q") ?? "").trim();',
        '.get("q") ?? "");',
        "Header search no longer trims the query",
    ),
    Mutation(
        "web-amd-format",
        "apps/web/src/lib/utils.ts",
        'toLocaleString("en-US")',
        'toLocaleString("de-DE")',
        "Prices formatted with the wrong locale (shared helper)",
    ),
    Mutation(
        "web-checkout-note-placeholder",
        "apps/web/src/components/sections/order-delivery-form.tsx",
        'placeholder="Allergies, instructions, gate code..."',
        'placeholder="Notes for the courier"',
        "Checkout note field placeholder changed",
    ),
    Mutation(
        "web-footer-disclaimer",
        "apps/web/src/components/layout/footer.tsx",
        "Chefs, dishes and orders on this site are fictional.",
        "All chefs, dishes and orders here are fictional.",
        "Footer disclaimer text changed (layout shared by every page)",
    ),
    # ---- back office (apps/admin) ---------------------------------------------------------
    Mutation(
        "admin-orderlist-receiver",
        "apps/admin/src/pages/orders/OrderList.jsx",
        '<TextField source="receiverName" label="Receiver" />',
        '<TextField source="receiverEmail" label="Receiver" />',
        "Orders list shows the e-mail in the Receiver column",
    ),
    Mutation(
        "admin-chef-delivery-label",
        "apps/admin/src/pages/chefs/ChefEdit.jsx",
        '<NumberInput source="deliveryPrice" label="Delivery price" />',
        '<NumberInput source="deliveryPrice" label="Delivery fee" />',
        "Chef edit form label renamed",
    ),
    Mutation(
        "admin-dashboard-revenue-rejected",
        "apps/admin/src/pages/Dashboard.jsx",
        ".filter((o) => o.status !== OrderStatus.REJECTED)",
        ".filter((o) => o.status !== OrderStatus.DELIVERED)",
        "Dashboard revenue excludes delivered instead of rejected orders",
    ),
    # ---- test code (page objects) ---------------------------------------------------------
    Mutation(
        "py-cart-panel-locator",
        "pages/web/cart_panel.py",
        'name="Increase quantity")',
        'name="Increase qty")',
        "Cart page object points at a wrong button",
    ),
    # ---- selection-only (the mock-backed e2e run can't fail on these) ---------------------
    Mutation(
        "be-order-service",
        "apps/backend/src/main/java/am/foodme/backend/service/OrderReviewService.java",
        "public class OrderReviewService",
        "public class OrderReviewService /* touched */",
        "Backend service change (order reviews)",
        ground_truth=False,
    ),
    Mutation(
        "docs-readme",
        "README.md",
        "FoodMe",
        "FoodMe (docs)",
        "Docs-only change",
        ground_truth=False,
    ),
    Mutation(
        "build-web-package",
        "apps/web/package.json",
        '"private": true',
        '"private": true ',
        "Storefront build config change",
        ground_truth=False,
    ),
]
