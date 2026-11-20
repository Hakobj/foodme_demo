# Brief 08: code-promo-branch
Run: SCRUM-8 · Source: code
Hypothesis under test: H-1 "the backend computes the promo discount on subtotal + delivery price" (alternative H-2: a previous discount kept per customer is added)
Window: n/a (code at commit ff70db0 = origin/feature/KAN-27-promo-code; the working tree does not contain the promo feature, see findings/07)
Allowed: read only. Read the code with `git show ff70db0:<path>`, `git grep -n <pattern> ff70db0 -- <paths>` and `git diff 7198f9b ff70db0`. Do not check out, switch branches or modify the working tree.

## Do
1. `git grep -niE "promo|discount" ff70db0 -- apps/backend/src/main apps/web/src` to find the files.
2. In the backend, find the handler for POST /api/customer/promo/apply and follow it to the code that computes `discount`, `deliveryPrice` and `total`, and the line that logs `promo.applied code=... status=... discount=...`.
3. Find what value the percent is multiplied by (the discount base) and how the delivery price for `deliveryMethod` is obtained.
4. Find whether any previous discount or applied promo kept per customer (e.g. a cache added in ff70db0 "cache applied promo per customer") is read and added to the new discount.
5. Find how the discount is computed when an order is placed (POST /api/order) with a promo code, and whether it uses the same base.
6. In apps/web at ff70db0, find where the checkout shows the Discount and Total lines: does it show the response values or compute them? Does "Remove" + "Apply" again always send a new request?
7. Compare the apply response DTO's fields with this observed response: `{"code":"SAVE10","status":"APPLIED","percent":10,"missingAmount":null,"discount":350.0,"deliveryPrice":500.0,"total":3150.0}`.

## Questions (answer each yes / no / unknown with observations)
1. What expression is the percent applied to in the promo apply code? Quote file, lines and code.
2. Does that expression include the delivery price?
3. Is any stored previous discount added to the new discount? Quote it.
4. Does order placement compute the discount with the same base? Quote it.
5. Does the storefront display the server's discount/total, or compute them itself? Quote it.
6. Does the apply response DTO have exactly the fields seen in the observed response?
7. Can the storefront re-show an earlier apply result without sending a new request? Quote it.

## Save
artifacts/08-code-promo-apply.txt, artifacts/08-code-promo-cache.txt, artifacts/08-code-order-place.txt, artifacts/08-code-web-checkout.txt (commit, file paths, line numbers and code excerpts).
