"""Page Object Model for the FoodMe UIs.

- `pages.web`   - customer storefront (apps/web)
- `pages.admin` - back office (apps/admin, react-admin hash routing)

Conventions:
- Page objects own locators and user actions. Tests own the assertions about business results.
- An action that moves to another page returns that page's object.
- Locators follow `.claude/rules/web-testing.md` / `admin-testing.md`: role/label first, then the
  shared CSS hooks (`a.cc_card`, `button.dc_card`, `aside.uc-panel`, `.cic_root`, `.fm-qty-grp p`).
- Waiting only through Playwright auto-waiting and `expect`, never `wait_for_timeout`.
"""
