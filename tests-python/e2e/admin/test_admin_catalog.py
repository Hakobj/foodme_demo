"""Back office: dashboard counters, chef / dish lists and edit forms, order details and actions.

The mock seeds 6 chefs with 3 dishes each (support/mock_e2e_backend.py). Edits are saved with
PUT /admin/chef|dish/{id}, so they show up in the storefront API right away.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.admin import AdminLoginPage, ChefEditPage, ChefsListPage, DashboardPage, DishEditPage, OrdersListPage
from support.api import create_order_via_api
from support.mock_e2e_backend import CHEF_NAMES, DISH_NAMES


@pytest.fixture(autouse=True)
def signed_in_admin(page: Page) -> None:
    AdminLoginPage(page).login_as_admin()


def test_dashboard_counts_chefs_dishes_and_orders(page: Page, api):
    create_order_via_api(api)
    create_order_via_api(api, name="Second Buyer", email="second-buyer@example.com")

    # The autouse login already rendered the dashboard (0 orders) and "/#/" is only a hash change,
    # so react-admin could show its cached counts: reload to fetch them after the orders exist.
    dashboard = DashboardPage(page).open().reload()

    expect(dashboard.stat("Chefs")).to_have_text(str(len(CHEF_NAMES)), timeout=dashboard.LOAD_TIMEOUT)
    expect(dashboard.stat("Dishes")).to_have_text(str(len(CHEF_NAMES) * len(DISH_NAMES)))
    expect(dashboard.stat("Total orders")).to_have_text("2")
    expect(dashboard.stat("Recent revenue")).to_contain_text("5,000")


def test_chefs_list_shows_every_seeded_chef(page: Page):
    chefs = ChefsListPage(page).open()

    expect(chefs.rows).to_have_count(len(CHEF_NAMES), timeout=chefs.LIST_TIMEOUT)
    for name in CHEF_NAMES:
        expect(chefs.rows.filter(has_text=name)).to_have_count(1)


def test_chef_edit_form_is_prefilled(page: Page):
    chef = ChefEditPage(page).open_record(2)

    expect(chef.field("Username")).to_have_value(CHEF_NAMES[1])
    expect(chef.field("Phone")).to_have_value("+37499110002")
    expect(chef.field("Delivery price")).to_have_value("500")
    expect(chef.field("Free delivery from")).to_have_value("5000")


def test_saving_chef_delivery_price_updates_the_storefront_api(page: Page, api):
    ChefEditPage(page).open_record(1).fill("Delivery price", "700").save()

    assert api.chefs.by_id(1).json()["deliveryPrice"] == 700


def test_dish_edit_form_is_prefilled_and_chef_id_is_read_only(page: Page):
    dish = DishEditPage(page).open_record(10)

    expect(dish.field("Name")).to_have_value(DISH_NAMES[0])
    expect(dish.field("Price")).to_have_value("2500")
    expect(dish.field("Chef ID")).to_be_disabled()


def test_saving_dish_price_updates_the_chef_menu(page: Page, api):
    DishEditPage(page).open_record(11).fill("Price", "3100").save()

    dishes = api.dishes.active_for_chef(1).json()["dishDtoList"]
    assert next(d for d in dishes if d["id"] == 11)["price"] == 3100


def test_order_show_lists_receiver_payment_and_delivery(page: Page, api):
    order = create_order_via_api(api, name="Show Details", phone="+37490001122", email="show@example.com")

    order_page = OrdersListPage(page).open().refresh().open_order(order["number"])

    expect(order_page.heading(order["number"])).to_be_visible()
    for text in ("Show Details", "+37490001122", "show@example.com", "CASH", "TAKEAWAY"):
        expect(order_page.detail(text)).to_be_visible()


def test_new_order_offers_accept_and_reject_but_not_deliver(page: Page, api):
    order = create_order_via_api(api)

    order_page = OrdersListPage(page).open().refresh().open_order(order["number"])

    expect(order_page.transition_button("ACCEPTED")).to_be_visible()
    expect(order_page.transition_button("REJECTED")).to_be_visible()
    expect(order_page.transition_button("DELIVERED")).to_have_count(0)


def test_orders_list_shows_chef_receiver_and_status(page: Page, api):
    order = create_order_via_api(api, name="List Columns")

    orders = OrdersListPage(page).open().refresh()

    row = orders.rows.filter(has_text=order["number"])
    expect(row).to_contain_text("List Columns", timeout=15_000)
    expect(row).to_contain_text(order["chefName"])
    expect(row).to_contain_text("NEW")
