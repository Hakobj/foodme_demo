"""Explore page: chef search (?q= and the header search box), kitchen filter chips, chef cards.

The mock seeds 6 chefs (support/mock_e2e_backend.py). "Argentinean" has the same kitchen as its
name, so the page shows no chip for it (sameLabel): 5 kitchen chips plus "All".
"""

import re

import pytest
from playwright.sync_api import Page, expect

from pages.web import ExplorePage, Header
from support.mock_e2e_backend import CHEF_NAMES

KITCHEN_CHIPS = ["Armenian", "Comfort food", "Desserts", "Italian", "Japanese"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("sakura", ["Sakura Kitchen"]),
        ("ARMENIAN", ["Armenian Traditional"]),
        ("kitchen", ["Alans Kitchen", "Sakura Kitchen"]),
        ("italian", ["Italiano Margarino"]),  # kitchen "Italian", but also the name "Italiano"
        ("  verona  ", ["Chef Verona"]),  # the query is trimmed
        ("japanese", ["Sakura Kitchen"]),  # only the kitchen matches, not the name
    ],
)
def test_search_query_filters_chef_cards(page: Page, query: str, expected: list[str]):
    explore = ExplorePage(page).open(query)

    expect(explore.chef_cards).to_have_count(len(expected))
    for name in expected:
        expect(explore.chef_card(name)).to_be_visible()


def test_search_without_match_offers_clear_filters(page: Page):
    explore = ExplorePage(page).open("no-such-chef")

    expect(explore.no_match_message).to_be_visible()
    expect(explore.chef_cards).to_have_count(0)

    explore.clear_filters_button.click()
    expect(page).to_have_url(re.compile(r"/explore$"))
    expect(explore.chef_cards).to_have_count(len(CHEF_NAMES))


def test_header_search_opens_explore_with_query(page: Page):
    ExplorePage(page).open()

    explore = Header(page).search("Sakura")

    expect(page).to_have_url(re.compile(r"/explore\?q=Sakura$"))
    expect(explore.chef_cards).to_have_count(1)
    expect(Header(page).search_box).to_have_value("Sakura")


def test_empty_header_search_lists_all_chefs(page: Page):
    ExplorePage(page).open("sakura")

    explore = Header(page).search("   ")

    expect(page).to_have_url(re.compile(r"/explore$"))
    expect(explore.chef_cards).to_have_count(len(CHEF_NAMES))


def test_explore_shows_chef_count(page: Page):
    explore = ExplorePage(page).open()
    expect(explore.chef_count_text).to_have_text(f"{len(CHEF_NAMES)} chefs cooking near you")


def test_kitchen_chips_are_sorted_and_skip_kitchens_equal_to_the_chef_name(page: Page):
    explore = ExplorePage(page).open()

    expect(explore.kitchen_chips).to_have_text(["All", *KITCHEN_CHIPS])
    expect(explore.all_kitchens_chip).to_have_attribute("aria-pressed", "true")


@pytest.mark.parametrize(
    ("kitchen", "chef"),
    [
        ("Comfort food", "Alans Kitchen"),
        ("Italian", "Italiano Margarino"),
        ("Desserts", "Chef Verona"),
        ("Armenian", "Armenian Traditional"),
        ("Japanese", "Sakura Kitchen"),
    ],
)
def test_kitchen_chip_shows_only_that_kitchen(page: Page, kitchen: str, chef: str):
    explore = ExplorePage(page).open().filter_by_kitchen(kitchen)

    expect(explore.kitchen_chip(kitchen)).to_have_attribute("aria-pressed", "true")
    expect(explore.all_kitchens_chip).to_have_attribute("aria-pressed", "false")
    expect(explore.chef_cards).to_have_count(1)
    expect(explore.chef_card(chef)).to_be_visible()


def test_clicking_the_active_chip_again_clears_the_filter(page: Page):
    explore = ExplorePage(page).open().filter_by_kitchen("Italian")
    expect(explore.chef_cards).to_have_count(1)

    explore.filter_by_kitchen("Italian")

    expect(explore.kitchen_chip("Italian")).to_have_attribute("aria-pressed", "false")
    expect(explore.chef_cards).to_have_count(len(CHEF_NAMES))


def test_kitchen_chip_and_search_combine(page: Page):
    explore = ExplorePage(page).open("kitchen").filter_by_kitchen("Japanese")

    expect(explore.chef_cards).to_have_count(1)
    expect(explore.chef_card("Sakura Kitchen")).to_be_visible()


def test_chef_cards_show_name_kitchen_and_rating(page: Page):
    explore = ExplorePage(page).open()
    card = explore.chef_card("Italiano Margarino")

    expect(explore.card_name(card)).to_have_text("Italiano Margarino")
    expect(explore.card_metadata(card)).to_contain_text("Italian")
    expect(explore.card_rating(card)).to_be_visible()  # the star icon
    expect(card).to_contain_text("4.5")


def test_chef_card_opens_that_chefs_page(page: Page):
    chef_page = ExplorePage(page).open().open_chef("Chef Verona")

    expect(page).to_have_url(re.compile(r"/chef/3$"))
    expect(chef_page.name_heading).to_have_text("Chef Verona")
