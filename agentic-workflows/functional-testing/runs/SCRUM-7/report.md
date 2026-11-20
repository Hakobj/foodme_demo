# SCRUM-7 test report: Promo codes at checkout

SUT: https://foodme-hakobjulfayan.onrender.com/ · Run date: 2026-11-19 · Tester: Hakob Julfayan (human reviews), Claude Code (agent)

## Summary

**The feature is not ready.** 14 cases were run manually (step 05) and as Playwright tests (step 08). 8 pass and 6 fail, and the manual and automated results agree on every case. The failing cases are SCRUM-7-TC-02, TC-09, TC-10, TC-11, TC-13 and TC-14, so AC-2, AC-3, AC-5 and AC-6 are not met. AC-1, AC-4 and AC-7 pass. Four bugs were filed in Jira and linked to SCRUM-7: SCRUM-8, SCRUM-9, SCRUM-10 and SCRUM-11. Nothing here has been triaged.

## Coverage

| AC | cases | manual (05) | automated (08) |
|---|---|---|---|
| AC-1 Enter a code and press Apply | TC-01 | ✅ | ✅ |
| AC-2 Valid code reduces the subtotal; discount and new total shown | TC-02, TC-04, TC-06, TC-09, TC-14 | ❌ (TC-02, TC-09, TC-14) | ❌ (TC-02, TC-09, TC-14) |
| AC-3 Minimum order; "Add {missing amount} AMD more to use this code" | TC-02, TC-03, TC-04, TC-05, TC-13 | ❌ (TC-02, TC-13) | ❌ (TC-02, TC-13) |
| AC-4 Expired code shows "This code has expired" | TC-07 | ✅ | ✅ |
| AC-5 Unknown code shows "Code not found" | TC-08, TC-09 | ❌ (TC-09) | ❌ (TC-09) |
| AC-6 One code per order; a second code replaces the first | TC-10, TC-11 | ❌ | ❌ |
| AC-7 Removing the code restores the original total | TC-12 | ✅ | ✅ |

## Cases

| case | title | 05 result | confidence | test title | 08 result |
|---|---|---|---|---|---|
| SCRUM-7-TC-01 | Promo code field with Apply on checkout; Apply disabled while the field is empty | match | sure | SCRUM-7-TC-01: Promo code field with Apply on checkout; Apply disabled while the field is empty | passed (re-run) |
| SCRUM-7-TC-02 | SAVE10 at exactly the 3,000 AMD minimum takes 10% off the items subtotal; delivery added after | mismatch | sure | SCRUM-7-TC-02: SAVE10 at exactly the 3,000 AMD minimum takes 10% off the items subtotal; delivery added after | failed |
| SCRUM-7-TC-03 | SAVE10 with a 2,900 AMD subtotal (100 below the minimum) shows the missing amount | match | sure | SCRUM-7-TC-03: SAVE10 with a 2,900 AMD subtotal (100 below the minimum) shows the missing amount | passed |
| SCRUM-7-TC-04 | TREAT15 at exactly the 8,000 AMD minimum takes 15% off | mismatch (checked by Hakob Julfayan); final **match** by decision of Hakob Julfayan | unsure | SCRUM-7-TC-04: TREAT15 at exactly the 8,000 AMD minimum takes 15% off | passed |
| SCRUM-7-TC-05 | TREAT15 with a 6,950 AMD subtotal shows the missing amount with a thousands separator | match | sure | SCRUM-7-TC-05: TREAT15 with a 6,950 AMD subtotal shows the missing amount with a thousands separator | passed (re-run) |
| SCRUM-7-TC-06 | TREAT15 on 8,050 AMD rounds the 1,207.5 AMD discount to 1,208 AMD | match | sure | SCRUM-7-TC-06: TREAT15 on 8,050 AMD rounds the 1,207.5 AMD discount to 1,208 AMD | passed |
| SCRUM-7-TC-07 | Expired code OLD15 is rejected | match | sure | SCRUM-7-TC-07: Expired code OLD15 is rejected | passed (re-run) |
| SCRUM-7-TC-08 | Unknown code NOPE99 is rejected | match | sure | SCRUM-7-TC-08: Unknown code NOPE99 is rejected | passed |
| SCRUM-7-TC-09 | Lower-case code with surrounding spaces (" save10 ") is accepted as SAVE10 | mismatch (checked by Hakob Julfayan) | unsure | SCRUM-7-TC-09: Lower-case code with surrounding spaces (" save10 ") is accepted as SAVE10 | failed |
| SCRUM-7-TC-10 | Applying TREAT15 after SAVE10 replaces it | mismatch | sure | SCRUM-7-TC-10: Applying TREAT15 after SAVE10 replaces it | failed |
| SCRUM-7-TC-11 | An expired second code (OLD15) does not replace an applied SAVE10 | mismatch | sure | SCRUM-7-TC-11: An expired second code (OLD15) does not replace an applied SAVE10 | failed (re-run) |
| SCRUM-7-TC-12 | Removing an applied SAVE10 restores the original total | match | sure | SCRUM-7-TC-12: Removing an applied SAVE10 restores the original total | passed |
| SCRUM-7-TC-13 | Applied SAVE10 stays but loses its discount when the cart drops below 3,000 AMD | mismatch (checked by Hakob Julfayan) | unsure | SCRUM-7-TC-13: Applied SAVE10 stays but loses its discount when the cart drops below 3,000 AMD | failed |
| SCRUM-7-TC-14 | An order placed with SAVE10 is charged the discounted total | mismatch (checked by Hakob Julfayan) | unsure | SCRUM-7-TC-14: An order placed with SAVE10 is charged the discounted total | failed |

**Automated run history** (`results.json` holds the final result for each test):
1. Run 1: the default config (fully parallel, 30 s timeout). All 14 tests **timed out in setup** (loading the chef page, sign-up, or opening checkout) before the first assertion. Not an app result.
2. Run 2: `--workers=2 --timeout=90000`, with the human's approval. 5 passed and 9 failed. TC-01, TC-05 and TC-07 failed in setup, because sign-up didn't finish within the 5 s wait in `e2e/auth.ts`. The human chose to re-run them. Kept as `results-run2.json`.
3. Re-runs (`--workers=1`): TC-01, TC-05 and TC-07 passed (`results-rerun-tc01-05-07.json`). TC-11 failed on an assertion, not a timeout (`results-rerun-tc11.json`). These results replace run 2's for those four tests in `results.json`.

## Not triaged

Manual mismatches (05) and automated failures (08), quoted from `execution.md` and `results.json`:

- **SCRUM-7-TC-02**
  - Expected: "Before the order is placed the page shows a discount of 300 AMD (10% of 3,000) and a new total of 3,200 AMD (3,000 − 300 + 500 delivery)".
  - 05 observed: "SAVE10 applied: 10% off" · Subtotal 3,000 AMD · Delivery 500 AMD · "Discount (SAVE10)" "−350 AMD" · Total 3,150 AMD.
  - 08: `expect(locator).toBeVisible() failed · getByRole('complementary').getByText(/^[−-]\s?300 AMD$/)`. The page showed −350 AMD, Total 3,150 AMD.
- **SCRUM-7-TC-04** (overridden)
  - Expected: "a discount of 1,200 AMD … new total of 6,800 AMD".
  - 05 observed: "Discount (TREAT15)" "−1,550 AMD" · Total 6,450 AMD.
  - 08 passed with a new customer. The human set the final result to match: "No mismatch for a new customer … the −1,550 in step 05 was leftover state on the tester account, covered by SCRUM-9."
- **SCRUM-7-TC-09**
  - Expected: "\"Code not found\" is not shown; the page shows a discount of 300 AMD and a new total of 3,200 AMD, the same as SAVE10".
  - 05 observed: "SAVE10 applied: 10% off" · "Discount (SAVE10)" "−1,558 AMD" · Total 1,942 AMD.
  - 08: `getByText(/^[−-]\s?300 AMD$/)` not found. The page showed no discount line, Total 3,500 AMD.
- **SCRUM-7-TC-10**
  - Expected: "only TREAT15 is applied: the discount is 1,200 AMD (15% of 8,000, not 800 + 1,200) and the new total is 6,800 AMD".
  - 05 observed: "TREAT15 applied: 15% off" · "Discount (TREAT15)" "−2,000 AMD" · Total 6,000 AMD.
  - 08: `getByText(/^[−-]\s?1,200 AMD$/)` not found. The page showed −2,000 AMD, Total 6,000 AMD.
- **SCRUM-7-TC-11**
  - Expected: "The page shows \"This code has expired\"; SAVE10 stays applied with a discount of 800 AMD (10% of 8,000) and a total of 7,200 AMD".
  - 05 observed: "This code has expired" · no "SAVE10 applied" line, no Discount line · Total 8,000 AMD.
  - 08 (re-run): `getByText(/^[−-]\s?800 AMD$/)` not found. The page showed the alert "This code has expired", Subtotal 8,000 AMD, Total 8,000 AMD.
- **SCRUM-7-TC-13**
  - Expected: "SAVE10 is still shown as the entered code, no discount is applied, the page shows \"Add 1,500 AMD more to use this code\" and the total is 2,000 AMD".
  - 05 observed: the Promo code field was empty, with no "SAVE10 applied" line and no "Add 1,500 AMD more to use this code" message · Total 2,000 AMD.
  - 08: `expect(getByLabel('Promo code', { exact: true })).toHaveValue("SAVE10")` failed; it received "".
- **SCRUM-7-TC-14**
  - Expected: "Checkout shows a total of 3,200 AMD before placing; the placed order (confirmation and order history) has a total of 3,200 AMD, not 3,500 AMD".
  - 05 observed: −350 AMD, Total 3,150 AMD before placing. The confirmation for FM-100002 shows no total. The order history shows "FM-100002 · Received · Alans Kitchen · 19 Nov 2026 · 3,150 AMD".
  - 08: `toContainText(/Total\s*3,200 AMD/)` failed; it received "…Discount (SAVE10)−350 AMD…Total3,150 AMD…".

Other observations from step 05 (outside the cases):
- The quick "Add <dish> to cart" button on /chef/24 adds the dish with all of its additions selected (3,700 AMD instead of 3,000 AMD).
- Discounts appeared to build up on the server across applies for the same account.
- The order confirmation page shows no total.

## Still unsure

None. All four cases that were unsure in step 05 (TC-04, TC-09, TC-13, TC-14) were checked by Hakob Julfayan as mismatch. TC-04 was later set to match by the human's decision.

## Questions answered

| Q | answer | by |
|---|---|---|
| Q-1 | Items subtotal only: discount and minimum both use the items subtotal; delivery is added after the discount | Hakob Julfayan |
| Q-2 | Nearest whole AMD: round half up to a whole AMD | Hakob Julfayan |
| Q-3 | Keep code, drop discount: code stays attached, discount removed, "Add {missing amount} AMD more…" message shown | Hakob Julfayan |
| Q-4 | No, first stays: first code stays applied; the error for the second code is shown | Hakob Julfayan |
| Q-5 | Case-insensitive + trim: "save10" and " SAVE10 " both work | Hakob Julfayan |
| Q-6 | Thousands separator: "Add 1,500 AMD more to use this code" | Hakob Julfayan |
| Q-7 | Apply disabled: Apply can't be pressed while the field is empty | Hakob Julfayan |
| Q-8 | Yes, order keeps discount: placed order total equals the discounted total shown at checkout | Hakob Julfayan |

## Review

- requirements: approved by Hakob Julfayan at 2026-11-19T12:05:30Z
- plan: approved by Hakob Julfayan at 2026-11-19T12:07:42Z
- cases: approved by Hakob Julfayan at 2026-11-19T12:14:51Z, note "judge 04-02 unsure"
- manual_check: approved by Hakob Julfayan at 2026-11-19T12:38:02Z, note "4 unsure, 4 confirmed, 0 still unsure"
- tests: approved by Hakob Julfayan at 2026-11-19T12:43:42Z, note "judge 07-01 unsure"

Judge verdicts:
- `04-01` **fail**: C3 · SCRUM-7-TC-03: the rejection depends on the Q-1 rule, but Q-1 was missing from `expected_source` / `blocked_by`. Fixed before round 2.
- `04-02` **unsure**:
  - C2 · spec: no question asks whether the free-delivery threshold uses the subtotal before or after the discount. No case's expected value depends on it.
  - C5 · SCRUM-7-TC-14: "fill in the delivery details" names no concrete data.
- `07-01` **unsure**:
  - T3 · SCRUM-7-TC-14: `expect(orderNumber).toBeTruthy();` reads the URL once, after a retrying `toHaveURL`.
  - T5 · spec: every test uses `/chef/24` and exact dish names and prices, as the cases require.

## Not tested

- Out of scope: free-delivery codes; chef-specific codes; first-order-only codes.
- Blocked cases: none.

## Found issues

| id | title | cases | status | Jira |
|---|---|---|---|---|
| SCRUM-7-ISSUE-01 | Bug: SAVE10 discount is taken from subtotal + delivery (−350 instead of −300) | SCRUM-7-TC-02 | filed | [SCRUM-8](https://julfayanhakob91.atlassian.net/browse/SCRUM-8) |
| SCRUM-7-ISSUE-02 | Bug: " save10 " gives a wrong discount (−1,558) instead of SAVE10's | SCRUM-7-TC-09 | rejected (not filed) | n/a |
| SCRUM-7-ISSUE-03 | Bug: TREAT15 after SAVE10 stacks both discounts (−2,000) instead of replacing | SCRUM-7-TC-10 | filed | [SCRUM-9](https://julfayanhakob91.atlassian.net/browse/SCRUM-9) |
| SCRUM-7-ISSUE-04 | Bug: expired OLD15 removes the applied SAVE10 instead of keeping it | SCRUM-7-TC-11 | filed | [SCRUM-10](https://julfayanhakob91.atlassian.net/browse/SCRUM-10) |
| SCRUM-7-ISSUE-05 | Bug: applied SAVE10 is dropped when the cart falls below 3,000 AMD, no "Add 1,500 AMD more" message | SCRUM-7-TC-13 | filed | [SCRUM-11](https://julfayanhakob91.atlassian.net/browse/SCRUM-11) |
| SCRUM-7-ISSUE-06 | Bug: order placed with SAVE10 is charged 3,150 AMD instead of 3,200 AMD | SCRUM-7-TC-14 | filed | [SCRUM-8](https://julfayanhakob91.atlassian.net/browse/SCRUM-8) |

All filed bugs are linked to SCRUM-7 ("relates to"). They were filed as Tasks without a sprint. Converting them to Sub-tasks of SCRUM-7 was blocked by the session's permission settings.

## Qase

- Project: **FOODME** (FoodMe), created for this run through the Qase connector at the human's request.
- Suite: "SCRUM-7 Promo codes at checkout" (suite id 1), 14 automated cases tagged `SCRUM-7`, `stlc` (Qase case ids 1–14 = SCRUM-7-TC-01 … TC-14; written back as `qase_id` in `spec.yaml`).
- Run: **"SCRUM-7 STLC 2026-11-19"**, run id **1**, completed: 8 passed / 6 failed / 0 blocked. Failed results carry the Playwright error and the Jira key.
- Link: https://app.qase.io/run/FOODME/dashboard/1
