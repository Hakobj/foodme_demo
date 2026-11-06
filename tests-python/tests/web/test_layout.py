"""Port of apps/web/e2e/layout.spec.ts."""

from playwright.sync_api import Page, expect

from pages.web import ChefPage, ExplorePage, HomePage
from support.api import find_dish_with_additions


def test_home_page_structure_and_sections(page: Page):
    home = HomePage(page).open()

    expect(home.hero_heading).to_be_visible()
    expect(home.order_now_link).to_be_visible()

    expect(home.steps_heading).to_be_visible()
    expect(home.step_heading("Find your chef")).to_be_visible()
    expect(home.step_heading("Pick your dishes")).to_be_visible()
    expect(home.step_heading("Fresh at the door")).to_be_visible()

    expect(home.popular_heading).to_be_visible()
    # Seed has 6 ACTIVE chefs; list endpoint drops one on the last page (FM-BUG-02).
    # At least 4 cards: the 4th one must render (auto-waits, unlike a one-shot count()).
    expect(home.popular_chef_cards.nth(3)).to_be_visible(timeout=HomePage.POPULAR_TIMEOUT)

    expect(home.cta_heading).to_be_visible()
    expect(home.browse_chefs_link).to_be_visible()


def test_explore_page_layout(page: Page):
    explore = ExplorePage(page).open()

    expect(explore.heading).to_be_visible()
    expect(explore.chefs_grid).to_be_visible()
    expect(explore.chef_cards.nth(3)).to_be_visible()

    first_card = explore.chef_cards.first
    expect(ExplorePage.card_image(first_card)).to_be_visible()
    expect(ExplorePage.card_name(first_card)).to_be_visible()
    expect(ExplorePage.card_rating(first_card)).to_be_visible()

    card_name = (ExplorePage.card_name(first_card).text_content() or "").strip()
    expect(ExplorePage.card_metadata(first_card)).not_to_have_text(f"{card_name} · 25–40 min")


def test_responsive_layout_check_mobile_view(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    home = HomePage(page).open()

    expect(home.hero_heading).to_be_visible()

    explore = ExplorePage(page).open(query="Argentinean")
    expect(explore.search_box).to_have_count(1)
    expect(explore.search_box).to_have_value("Argentinean")


def test_cart_and_checkout_item_details_stay_aligned(page: Page, api):
    chef_id, dish_name = find_dish_with_additions(api)

    cart = ChefPage(page).open(chef_id).open_dish_by_name(dish_name).select_first_addition().add_to_cart()
    cart.wait_for_items(1)

    cart_name_box = cart.first_item.get_by_text(dish_name, exact=True).bounding_box()
    remove_box = cart.remove_button.bounding_box()
    assert cart_name_box is not None
    assert remove_box is not None
    assert abs(cart_name_box["y"] - remove_box["y"]) <= 6

    checkout = cart.go_to_checkout()
    checkout.create_account()
    quantity_box = checkout.summary_first_quantity.bounding_box()
    additions_box = checkout.summary_first_additions.bounding_box()
    assert quantity_box is not None
    assert additions_box is not None
    assert additions_box["x"] > quantity_box["x"] + 16
