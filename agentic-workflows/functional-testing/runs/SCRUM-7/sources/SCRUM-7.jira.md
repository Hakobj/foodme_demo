<!-- Verbatim snapshot of the Jira description of SCRUM-7, fetched 2026-11-19 via the Atlassian MCP (getJiraIssue). Not edited. -->
# SCRUM-7: [Feature] Promo codes: apply a promo code at checkout (KAN-27)

## Why

Marketing wants to run simple percentage promotions. Today there is no way for a customer to get a discount at checkout.

## User story

As a customer, I want to apply a promo code at checkout so that I pay less.

## What success looks like

1. On the checkout page, the customer can enter a promo code and press **Apply**.
2. A valid code reduces the subtotal by the code's percentage. The discount and the new total are shown before the order is placed.
3. A code works only if the subtotal is at least the code's minimum order amount. Otherwise the page shows "Add {missing amount} AMD more to use this code".
4. An expired code shows "This code has expired".
5. An unknown code shows "Code not found".
6. One code per order. Applying a second code replaces the first.
7. The customer can remove the applied code, and the total goes back to the original.

## Launch codes

| Code | Discount | Minimum order | Status |
| --- | --- | --- | --- |
| SAVE10 | 10% | 3,000 AMD | valid |
| TREAT15 | 15% | 8,000 AMD | valid |
| OLD15 | 15% | none | expired |

## Not in this release

* Free-delivery codes
* Chef-specific codes
* First-order-only codes

## Breakdown

1. Backend: promo validation and discount calculation
2. Checkout UI: promo field, messages, remove link

## Reference

Original ticket: KAN-27 (copied from `jira/KAN-27.md`). Implementation: https://github.com/Hakobj/foodme_demo/pull/5
