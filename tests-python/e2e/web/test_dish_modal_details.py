"""Dish modal: details, quantity, additions and the live price on "Add to cart".

"Signature Plate" (the 2nd dish of every chef) has "Extra cheese" (+300) and "Spicy sauce" (+200).
"""

import pytest
from playwright.sync_api import Page, expect

from pages.web import ChefPage


def open_dish(page: Page, name: str):
    return ChefPage(page).open(1).open_dish_by_name(name)


def test_modal_shows_title_description_and_portion(page: Page):
    modal = open_dish(page, "House Special")

    expect(modal.title).to_have_text("House Special")
    expect(modal.description).to_have_text("House Special cooked fresh.")
    expect(modal.portion).to_have_text("Portion · 350 g")


def test_dish_without_additions_has_no_additions_section(page: Page):
    modal = open_dish(page, "House Special")
    expect(modal.dialog).to_be_visible()
    expect(modal.additions_heading).to_have_count(0)


def test_quantity_starts_at_minimum_and_cannot_go_below_it(page: Page):
    modal = open_dish(page, "House Special")

    expect(modal.quantity).to_have_text("1")
    expect(modal.decrease_button).to_be_disabled()


@pytest.mark.parametrize(("clicks", "total"), [(0, "2,500 AMD"), (1, "5,000 AMD"), (3, "10,000 AMD")])
def test_add_button_price_follows_quantity(page: Page, clicks: int, total: str):
    modal = open_dish(page, "House Special").increase(clicks)

    expect(modal.quantity).to_have_text(str(clicks + 1))
    expect(modal.add_to_cart_button).to_contain_text(total)


@pytest.mark.parametrize(
    ("additions", "total"),
    [(["Extra cheese"], "2,800 AMD"), (["Spicy sauce"], "2,700 AMD"), (["Extra cheese", "Spicy sauce"], "3,000 AMD")],
)
def test_additions_raise_the_price(page: Page, additions: list[str], total: str):
    modal = open_dish(page, "Signature Plate")
    for name in additions:
        modal.toggle_addition(name)
        expect(modal.addition(name)).to_be_checked()

    expect(modal.add_to_cart_button).to_contain_text(total)


def test_unchecking_an_addition_restores_the_price(page: Page):
    modal = open_dish(page, "Signature Plate").toggle_addition("Extra cheese")
    expect(modal.add_to_cart_button).to_contain_text("2,800 AMD")

    modal.toggle_addition("Extra cheese")

    expect(modal.addition("Extra cheese")).not_to_be_checked()
    expect(modal.add_to_cart_button).to_contain_text("2,500 AMD")


def test_chosen_quantity_and_additions_reach_the_cart_line(page: Page):
    modal = open_dish(page, "Signature Plate").toggle_addition("Spicy sauce").increase(2)

    cart = modal.add_to_cart().wait_for_items(1)

    line = cart.item("Signature Plate")
    expect(line).to_contain_text("+ Spicy sauce")
    expect(line).to_contain_text("8,100 AMD")  # 3 x (2,500 + 200)
    expect(line).to_contain_text("2,700 AMD each")
    expect(cart.quantity).to_have_text("3")


def test_same_dish_with_different_additions_makes_separate_cart_lines(page: Page):
    chef_page = ChefPage(page).open(1)
    chef_page.open_dish_by_name("Signature Plate").add_to_cart().wait_for_items(1)
    expect(page.get_by_role("dialog")).to_have_count(0)

    cart = chef_page.open_dish_by_name("Signature Plate").toggle_addition("Extra cheese").add_to_cart()

    cart.wait_for_items(2)


def test_escape_closes_the_modal_without_adding(page: Page):
    chef_page = ChefPage(page).open(1)
    modal = chef_page.open_dish_by_name("House Special")
    expect(modal.dialog).to_be_visible()

    modal.close()

    expect(modal.dialog).to_have_count(0)
    expect(chef_page.cart.items).to_have_count(0)
