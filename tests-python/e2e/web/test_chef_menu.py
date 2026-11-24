"""Chef page: details hero, menu sections, quick add, and the one-chef-per-cart rule.

Mock data: every chef has 3 dishes ("House Special", "Signature Plate", "Chef's Salad") at 2,500 AMD,
350 g, tag "Main"; delivery 500 AMD, free from 5,000 AMD; DELIVERY and TAKEAWAY.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.web import ChefPage
from support.mock_e2e_backend import CHEF_NAMES, DISH_NAMES, KITCHENS


@pytest.mark.parametrize("chef_id", range(1, len(CHEF_NAMES) + 1))
def test_each_chef_page_shows_its_name_and_full_menu(page: Page, chef_id: int):
    chef_page = ChefPage(page).open(chef_id)

    expect(chef_page.name_heading).to_have_text(CHEF_NAMES[chef_id - 1])
    expect(chef_page.dish_cards).to_have_count(len(DISH_NAMES))
    for dish in DISH_NAMES:
        expect(chef_page.dish_card(dish)).to_be_visible()


def test_chef_hero_shows_kitchen_delivery_terms_takeaway_and_phone(page: Page):
    chef_page = ChefPage(page).open(2)

    expect(chef_page.hero).to_contain_text(KITCHENS[1])
    expect(chef_page.delivery_info).to_have_text("500 AMD delivery · free from 5,000 AMD")
    expect(chef_page.takeaway_badge).to_be_visible()
    expect(chef_page.phone_link).to_have_attribute("href", "tel:+37499110002")


def test_kitchen_equal_to_chef_name_is_not_repeated(page: Page):
    chef_page = ChefPage(page).open(CHEF_NAMES.index("Argentinean") + 1)

    expect(chef_page.name_heading).to_have_text("Argentinean")
    expect(chef_page.hero.get_by_text("Argentinean", exact=True)).to_have_count(1)


def test_dish_card_shows_price_portion_and_description(page: Page):
    card = ChefPage(page).open(1).dish_card("House Special")

    expect(card).to_contain_text("2,500 AMD")
    expect(card).to_contain_text("350 g")
    expect(card).to_contain_text("House Special cooked fresh.")


def test_dishes_are_grouped_under_their_tag(page: Page):
    chef_page = ChefPage(page).open(1)
    expect(chef_page.menu_section("Main")).to_be_visible()
    expect(chef_page.menu_section("Other")).to_have_count(0)


def test_empty_cart_panel_on_chef_page(page: Page):
    cart = ChefPage(page).open(1).cart
    expect(cart.root.get_by_text("Your cart is empty")).to_be_visible()
    expect(cart.checkout_link).to_have_count(0)


def test_quick_add_puts_dish_in_cart_without_opening_the_modal(page: Page):
    chef_page = ChefPage(page).open(1)

    cart = chef_page.quick_add("Chef's Salad").wait_for_items(1)

    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(cart.item("Chef's Salad")).to_be_visible()
    expect(cart.quantity).to_have_text("1")


def test_quick_adding_the_same_dish_twice_raises_its_quantity(page: Page):
    chef_page = ChefPage(page).open(1)

    chef_page.quick_add("House Special").wait_for_items(1)
    cart = chef_page.quick_add("House Special")

    expect(cart.quantity).to_have_text("2")
    expect(cart.items).to_have_count(1)


def test_adding_from_another_chef_asks_to_switch_and_keep_cart_keeps_it(page: Page):
    ChefPage(page).open(1).quick_add("House Special").wait_for_items(1)

    other = ChefPage(page).open(2)
    expect(other.cart.foreign_cart_message).to_be_visible()
    other.quick_add("House Special")

    expect(other.switch_kitchens_prompt).to_be_visible()
    other.keep_cart_button.click()
    expect(other.switch_kitchens_prompt).to_have_count(0)
    expect(other.cart.items).to_have_count(0)
    expect(other.cart.go_to_current_cart_link).to_be_visible()


def test_clear_and_continue_replaces_the_other_chefs_cart(page: Page):
    ChefPage(page).open(1).quick_add("House Special").wait_for_items(1)

    other = ChefPage(page).open(2)
    other.quick_add("Signature Plate")
    other.clear_and_continue_button.click()

    other.cart.wait_for_items(1)
    expect(other.cart.item("Signature Plate")).to_be_visible()
    expect(ChefPage(page).open(1).cart.foreign_cart_message).to_be_visible()
