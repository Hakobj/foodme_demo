"""Port of apps/web/e2e/flake-dish-modal.spec.ts."""

from playwright.sync_api import Page, expect

from pages.web import ExplorePage


def test_dish_modal_opens_and_dish_can_be_added_to_cart(page: Page):
    chef_page = ExplorePage(page).open().open_first_chef()

    expect(chef_page.dish_cards.first).to_be_visible()
    modal = chef_page.open_dish(0)

    # FM-FLAKE-01
    page.wait_for_timeout(300)

    cart = modal.add_to_cart()

    expect(cart.items).to_have_count(1)
