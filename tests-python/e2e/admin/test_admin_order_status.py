"""Back-office order status changes beyond "Mark as ACCEPTED": reject with a reason, deliver.
Runs serially (shared seeded admin)."""

import pytest
from playwright.sync_api import Page, expect

from pages.admin import AdminLoginPage, OrderShowPage, OrdersListPage
from support.api import create_order_via_api


@pytest.fixture
def order_page(page: Page, api) -> tuple[OrderShowPage, str]:
    """Logs in, places a fresh NEW order through the API and opens it in the back office."""
    number = create_order_via_api(api)["number"]
    AdminLoginPage(page).login_as_admin()
    return OrdersListPage(page).open().refresh().open_order(number), number


def test_reject_requires_a_reason(order_page):
    show, _ = order_page

    show.mark_as("REJECTED")
    show.reject_confirm_button.click()

    expect(show.reason_required_warning).to_be_visible()
    expect(show.reject_dialog).to_be_visible()


def test_reject_with_reason_updates_status_and_hides_actions(order_page, api):
    show, number = order_page

    show.reject("Chef is unavailable today")

    expect(show.status_updated_notification).to_be_visible(timeout=show.STATUS_TIMEOUT)
    expect(show.status("REJECTED")).to_be_visible()
    expect(show.transition_button("ACCEPTED")).to_have_count(0)
    assert api.orders.by_number(number).json()["rejectReason"] == "Chef is unavailable today"


def test_accepted_order_can_be_marked_delivered(order_page):
    show, _ = order_page

    show.mark_as("ACCEPTED")
    expect(show.transition_button("DELIVERED")).to_be_visible(timeout=show.STATUS_TIMEOUT)
    show.mark_as("DELIVERED")

    expect(show.status("DELIVERED")).to_be_visible(timeout=show.STATUS_TIMEOUT)
    expect(show.transition_button("REJECTED")).to_have_count(0)
