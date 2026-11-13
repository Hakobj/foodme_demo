"""Port of apps/web/e2e/flake-cart-persistence.spec.ts."""

from playwright.sync_api import Page, expect

from pages.web import ExplorePage


def test_cart_item_survives_a_page_reload_right_after_add_to_cart(page: Page):
    chef_page = ExplorePage(page).open().open_first_chef()

    expect(chef_page.dish_cards.first).to_be_visible()
    modal = chef_page.open_dish(0)
    expect(modal.add_to_cart_button).to_be_visible()
    cart = modal.add_to_cart()

    # FM-FLAKE-05 FIX: Wait for cart panel to update before reloading
    expect(cart.items).to_have_count(1)

    chef_page.reload()

    expect(cart.items).to_have_count(1)
