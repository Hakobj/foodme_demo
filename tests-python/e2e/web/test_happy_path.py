"""Port of apps/web/e2e/happy-path.spec.ts."""

from playwright.sync_api import Page, expect

from pages.admin import AdminLoginPage
from pages.web import ChefPage, ExplorePage
from support.api import admin_token, create_order_via_api, find_dish_with_additions


def test_explore_chef_add_2_dishes_cart_total_cash_checkout_success(page: Page):
    chef_page = ExplorePage(page).open().open_first_chef()
    expect(chef_page.dish_cards.first).to_be_visible()

    chef_page.add_dish_to_cart(0)
    cart = chef_page.add_dish_to_cart(1)
    expect(cart.items).to_have_count(2)

    checkout = cart.go_to_checkout()
    checkout.create_account("Ann Test")
    checkout.fill_receiver("Ann Test", "+37491234567", "ann@example.com")
    checkout.fill_address("Yerevan", "Abovyan")

    success = checkout.place_order().wait_loaded()
    expect(success.title).to_be_visible()


def test_dish_modal_additions_raise_cart_line_price(page: Page, api):
    chef_id, dish_name = find_dish_with_additions(api)

    modal = ChefPage(page).open(chef_id).open_dish_by_name(dish_name)

    expect(modal.additions_heading).to_be_visible()
    addition, checkmark = modal.first_addition, modal.first_addition_checkmark
    expect(addition).to_have_css("border-radius", "0px")
    box = checkmark.bounding_box()
    assert box is not None
    assert box["width"] == 22
    assert box["height"] == 22
    expect(checkmark).to_have_css("border-radius", "0px")
    expect(checkmark).to_have_css("border-color", "rgb(0, 0, 0)")

    modal.select_first_addition()
    # Retries like expect.poll in the TS spec.
    expect(checkmark).to_have_css("background-color", "rgb(6, 193, 103)")

    cart = modal.add_to_cart()
    expect(cart.items).to_have_count(1)


def test_takeaway_checkout_succeeds_without_address(page: Page, cart_with_first_dish):
    checkout = cart_with_first_dish.go_to_checkout()

    checkout.create_account("Bob Pickup")
    checkout.choose_takeaway()
    checkout.fill_receiver("Bob Pickup", "+37491111222", "bob@example.com")

    success = checkout.place_order().wait_loaded()
    expect(success.title).to_be_visible()


def test_admin_can_login_and_list_orders_after_a_storefront_checkout(page: Page, api, admin_server):
    order = create_order_via_api(
        api, name="Admin Smoke", phone="+37490000000", email="admin-smoke@example.com", note="e2e admin visibility"
    )
    assert order["number"]

    # Admin list is sorted newest first, so the fresh order is on page 0.
    orders = api.admin.orders(admin_token(api), page=0, size=20)
    assert orders.ok, orders.text
    numbers = [o["number"] for o in orders.json()["list"]]
    assert order["number"] in numbers

    # The backend is mocked, so the back office is opened on its own dev server (not <backend>/backoffice).
    login = AdminLoginPage(page).open_at(admin_server)
    expect(login.username).to_be_visible(timeout=15_000)
