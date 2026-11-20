# Brief 07: code-promo
Run: SCRUM-8 · Source: code
Hypothesis under test: H-1 "the backend computes the promo discount on subtotal + delivery price" (alternative H-2: a previous discount kept per customer is added)
Window: n/a (code at the working tree of this repo)
Allowed: read only

## Do
1. In apps/backend, find the handler for POST /api/customer/promo/apply and follow it to the code that computes `discount`, `deliveryPrice` and `total` in the response (OrderService logs `promo.applied code=... status=... discount=...`).
2. Find what value the percent is multiplied by (the discount base), and how the delivery price for `deliveryMethod` is obtained.
3. Find whether any previous discount / applied promo per customer is read and added to the new discount.
4. Find how the discount is computed when an order is placed (POST /api/order) with a promo code, and whether it uses the same base.
5. In apps/web, find where the checkout shows the Discount and Total lines: does it show the response values or compute them?

## Questions (answer each yes / no / unknown with observations)
1. What expression is the percent applied to in the promo apply code? Quote file, lines and code.
2. Does that expression include the delivery price?
3. Is any stored previous discount added to the new discount? Quote it.
4. Does order placement compute the discount with the same base? Quote it.
5. Does the storefront display the server's discount/total, or compute them itself? Quote it.

## Save
artifacts/07-code-promo-apply.txt, artifacts/07-code-order-place.txt, artifacts/07-code-web-checkout.txt (file paths, line numbers and code excerpts).
