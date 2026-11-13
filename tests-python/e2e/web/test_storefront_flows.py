"""Port of apps/web/e2e/storefront-flows.spec.ts."""

from playwright.sync_api import Page, expect

from pages.web import CartPanel, CheckoutPage, ChefPage, HomePage, OrderFailedPage


def test_home_cta_navigates_to_explore_and_header_explore_chefs_works(page: Page):
    explore = HomePage(page).open().click_order_now().wait_loaded()
    expect(explore.heading).to_be_visible()

    HomePage(page).open().header.go_to_explore().wait_loaded()


def test_register_from_header_opens_orders_history(page: Page):
    login = HomePage(page).open().header.go_to_sign_in()

    orders = login.create_account("Header User").wait_loaded()

    expect(orders.heading).to_be_visible()
    expect(orders.empty_message).to_be_visible()


def test_empty_checkout_shows_browse_message(page: Page):
    checkout = CheckoutPage(page).open()
    expect(checkout.empty_cart_message).to_be_visible()


def test_cart_quantity_increase_and_remove_item(cart_with_first_dish: CartPanel):
    cart = cart_with_first_dish

    cart.increase()
    expect(cart.quantity).to_have_text("2")

    cart.remove_item()
    expect(cart.items).to_have_count(0)
    expect(cart.empty_message).to_be_visible()


# FM-BUG-07: decrementing above the minimum must lower the quantity, not remove the item
def test_cart_quantity_decrease_keeps_item_until_minimum_is_reached(cart_with_first_dish: CartPanel):
    cart = cart_with_first_dish
    initial = cart.quantity_value()

    cart.increase()
    expect(cart.quantity).to_have_text(str(initial + 1))

    cart.decrease()
    expect(cart.items).to_have_count(1)
    expect(cart.quantity).to_have_text(str(initial))

    cart.decrease()
    expect(cart.items).to_have_count(0)
    expect(cart.empty_message).to_be_visible()


def test_delivery_shows_address_fields_takeaway_hides_them(cart_with_first_dish: CartPanel):
    checkout = cart_with_first_dish.go_to_checkout()

    expect(checkout.form).to_have_count(0)
    checkout.create_account()

    checkout.choose_delivery()
    expect(checkout.city).to_be_visible()
    expect(checkout.street).to_be_visible()

    checkout.choose_takeaway()
    expect(checkout.city).to_have_count(0)
    expect(checkout.street).to_have_count(0)

    checkout.choose_delivery()
    expect(checkout.city).to_be_visible()


def test_payment_methods_are_selectable_visual_options(cart_with_first_dish: CartPanel):
    checkout = cart_with_first_dish.go_to_checkout()
    checkout.create_account()

    expect(checkout.cash_payment).to_be_checked()
    checkout.bank_card_payment.click()
    expect(checkout.bank_card_payment).to_be_checked()
    checkout.idram_payment.click()
    expect(checkout.idram_payment).to_be_checked()


def test_idram_checkout_still_places_a_cash_order(cart_with_first_dish: CartPanel):
    checkout = cart_with_first_dish.go_to_checkout()

    checkout.create_account("Idram Shopper")
    checkout.idram_payment.click()
    checkout.choose_delivery()
    checkout.fill_receiver("Idram Shopper", "+37493333445", "idram@example.com")
    checkout.fill_address("Yerevan", "Tumanyan", building="10")

    success = checkout.place_order().wait_loaded()
    expect(success.title).to_be_visible()


def test_full_delivery_checkout_shows_order_number_and_track_link(cart_with_first_dish: CartPanel):
    checkout = cart_with_first_dish.go_to_checkout()

    checkout.create_account("Casey Delivery")
    checkout.choose_delivery()
    checkout.fill_receiver("Casey Delivery", "+37493333444", "casey@example.com")
    checkout.fill_address("Yerevan", "Tumanyan", building="10", apartment="5")

    success = checkout.place_order().wait_loaded()
    expect(success.title).to_be_visible()
    expect(success.order_number_text).to_be_visible()
    expect(success.track_order_link).to_be_visible()
    expect(success.back_to_explore_link).to_be_visible()

    tracking = success.track_order()
    order_number = tracking.order_number

    orders = tracking.go_to_all_orders()
    expect(orders.order(order_number)).to_be_visible()


def test_chef_page_from_home_popular_section(page: Page):
    chef_page = HomePage(page).open().open_first_popular_chef()
    expect(chef_page.dish_cards.first).to_be_visible()


def test_missing_chef_does_not_ask_to_clear_another_chefs_cart(page: Page, cart_with_first_dish: CartPanel):
    chef_page = ChefPage(page).open(999999)

    expect(chef_page.not_found_message).to_be_visible()
    expect(chef_page.switch_kitchens_prompt).to_have_count(0)


def test_failed_order_page_renders_recovery_link(page: Page):
    failed = OrderFailedPage(page).open()
    expect(failed.heading).to_be_visible()
    expect(failed.back_to_explore_link).to_be_visible()
