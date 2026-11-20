# Brief 01: repro
Run: SCRUM-8 · Source: playwright
Hypothesis under test: none (exploration)
Window: 2026-11-20T10:40Z – 2026-11-20T11:30Z (record the actual UTC time of each key request)
Allowed: read only (apply/remove promo codes and edit the cart are allowed; do NOT place an order)

## Do
1. The human has signed in as a customer in the Playwright browser. Open https://foodme-hakobjulfayan.onrender.com/ and confirm the page is signed in (if not, stop with an obstacle).
2. Clean state: open the cart/checkout; if any promo code is shown as applied, remove it; remove every cart item. Record what you found before cleaning (any applied code, any discount line, any items).
3. Open https://foodme-hakobjulfayan.onrender.com/chef/24. Open the dish dialog for "Chicken curry rice & vegetables" (not the quick add button), keep no additions, quantity 1, press "Add to cart · 3,000 AMD".
4. Go to checkout, choose Delivery. Record the summary (Subtotal, Delivery, Total).
5. Type SAVE10 in "Promo code" and press Apply. Record the summary text (applied message, Subtotal, Delivery, Discount line, Total). Take a screenshot of the summary.
6. Remove the code and apply SAVE10 once more; record the summary again.
7. Save the network requests (method, URL, status, and for /api/** the request and response bodies, especially any promo/cart/checkout/pricing call) and the console messages.

## Questions (answer each yes / no / unknown with observations)
1. Before cleaning, was any promo code or discount already present on the account/cart?
2. After applying SAVE10 on the 3,000 AMD + 500 AMD delivery cart, what Discount and Total does the page show?
3. Does any /api/** response for the apply call contain a discount, base, subtotal, delivery or total field, and with what values?
4. Do the request bodies of the apply call send the delivery fee, delivery method or a total to the server, and with what values?
5. Did the second apply (step 6) give the same Discount and Total as the first?
6. Are there console errors or warnings during the steps?

## Save
artifacts/01-network.json, artifacts/01-console.txt, artifacts/01-checkout.png, artifacts/01-page-text.txt (summary text after each key step with UTC time).
