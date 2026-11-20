# Brief 06: test-base
Run: SCRUM-8 · Source: playwright
Hypothesis under test: H-1 "the discount base is subtotal + delivery price" vs H-2 "leftover promo state adds a fixed amount"
Window: from the start of this brief (record the UTC time of every apply request)
Allowed: read only (apply/remove promo codes, change the delivery method and edit the cart are allowed; do NOT place an order)

## Do
1. The browser is signed in as a customer (if not, stop with an obstacle). Open https://foodme-hakobjulfayan.onrender.com/checkout. Record the current state (items, applied code, discount line), then remove any applied code.
2. Make sure the cart has exactly 1 × "Chicken curry rice & vegetables" from Alans Kitchen (https://foodme-hakobjulfayan.onrender.com/chef/24, dish dialog, no additions, 3,000 AMD). Remove anything else.
3. Case A: at checkout choose Pickup (or whatever non-delivery method the page offers; if there is none, record that and skip to step 5). Apply SAVE10. Record the summary text (Subtotal, Delivery, Discount, Total) and the apply request + response body.
4. Remove the code, choose Delivery, apply SAVE10 again. Record the summary and the apply request + response body.
5. Case B: remove the code. Add a second item so the subtotal is 4,000 AMD with paid delivery (e.g. change to 1 × a 4,000 AMD dish such as "Dragon Roll" from /chef/24 alone; record what you chose and the subtotal). Choose Delivery, apply SAVE10. Record the summary and the apply request + response body.
6. Remove the code and leave the cart as it is.
7. Reload the checkout page between applies if the page does not send a new POST /api/customer/promo/apply; record whether each apply produced a network request.

## Questions (answer each yes / no / unknown with observations)
1. Does the checkout offer a non-delivery method, and with it what Delivery, Discount and Total does SAVE10 give on the 3,000 AMD cart?
2. With Delivery on the 3,000 AMD cart, what Discount and Total does SAVE10 give this time?
3. On the cart from step 5, what are Subtotal, Delivery, Discount and Total with SAVE10?
4. For each apply, what are the request body and the response body of POST /api/customer/promo/apply (discount, deliveryPrice, total)?
5. Did every apply produce its own POST /api/customer/promo/apply request?

## Save
artifacts/06-network.json, artifacts/06-page-text.txt (summary after each apply with UTC time), artifacts/06-pickup.png, artifacts/06-delivery-4000.png.
