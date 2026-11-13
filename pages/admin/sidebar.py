from playwright.sync_api import Locator, Page


class Sidebar:
    """react-admin menu. The "Orders" item appearing is the signal that login finished."""

    def __init__(self, page: Page):
        self.page = page

    def item(self, name: str) -> Locator:
        return self.page.get_by_role("menuitem", name=name)

    def go_to(self, name: str) -> None:
        self.item(name).click()
