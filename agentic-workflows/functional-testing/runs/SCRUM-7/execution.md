# SCRUM-7 execution log

SUT: https://foodme-hakobjulfayan.onrender.com/

## Run plan

- SCRUM-7-TC-01: "Apply is disabled" is a control state, not text. It can be read from the accessibility snapshot (`[disabled]`), but a button styled as disabled without the attribute would be ambiguous.
- SCRUM-7-TC-13: the step "Lower Oshinko Maki to 1 … and return to checkout" may have no quantity control on checkout, so I may have to choose where to change it (cart drawer or chef page). The result also depends on whether the applied code survives navigation (client or server state).
- SCRUM-7-TC-14: places a real order (can't be undone). Part of the expected result is on other pages (the confirmation and the order history). The order note will be `STLC SCRUM-7 SCRUM-7-TC-14`.
- Every case: an applied promo code may be stored on the client or server and leak into the next case. The clean-state check removes any applied code before each case.

## SCRUM-7-TC-01

- Started: 2026-11-19T12:17:05Z
- Tool: playwright-mcp
- Steps: 1 ✓ (signed in as a customer, cart emptied) 2 ✓ (the quick "Add … to cart" button added the dish with all 7 additions at 3,700 AMD, so I removed it and added the plain dish from its detail dialog at 3,000 AMD; see Other observations) 3 ✓ (Delivery was already pressed) 4 ✓ 5 ✓
- Expected (from spec.yaml): The checkout page has a promo code field and an Apply button; Apply is disabled while the field is empty and enabled once SAVE10 is typed
- Observed: textbox "Promo code" (placeholder "Enter code") with button "Apply" [disabled] while empty; after typing SAVE10, button "Apply" with no disabled attribute
- Result: match
- Confidence: sure

## SCRUM-7-TC-02

- Started: 2026-11-19T12:18:20Z
- Tool: playwright-mcp
- Steps: 1 ✓ 2 ✓ (same cart as TC-01: 1 × Chicken curry rice & vegetables, 3,000 AMD, added from the dish dialog) 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): Before the order is placed the page shows a discount of 300 AMD (10% of 3,000) and a new total of 3,200 AMD (3,000 − 300 + 500 delivery)
- Observed: "SAVE10 applied: 10% off" · Subtotal 3,000 AMD · Delivery 500 AMD · "Discount (SAVE10)" "−350 AMD" · Total 3,150 AMD. The 10% is taken from subtotal + delivery (3,500), against Q-1. A retry (remove code, apply again at 12:18:44Z) gave the same values.
- Result: mismatch
- Confidence: sure

## SCRUM-7-TC-03

- Started: 2026-11-19T12:19:18Z
- Tool: playwright-mcp
- Steps: 1 ✓ (promo code removed, cart emptied with Remove item) 2 ✓ (1 × Yassai curry from the dish dialog, 2,900 AMD) 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): The page shows "Add 100 AMD more to use this code"; no discount is applied and the total stays 3,400 AMD (2,900 + 500 delivery)
- Observed: "Add 100 AMD more to use this code" · Subtotal 2,900 AMD · Delivery 500 AMD · no Discount line · Total 3,400 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-04

- Started: 2026-11-19T12:19:58Z
- Tool: playwright-mcp
- Steps: 1 ✓ (cart emptied, no code applied) 2 ✓ (Dragon Roll dialog, quantity 2, "Add to cart · 8,000 AMD") 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): Before the order is placed the page shows a discount of 1,200 AMD (15% of 8,000) and a new total of 6,800 AMD (8,000 − 1,200, delivery free because the 8,000 AMD subtotal is from 5,000 AMD)
- Observed: "TREAT15 applied: 15% off" · Subtotal 8,000 AMD · Delivery Free · "Discount (TREAT15)" "−1,550 AMD" · Total 6,450 AMD. 1,550 AMD isn't 15% of 8,000 (1,200) or of 8,500 (1,275). A retry (remove, apply again at 12:20:35Z) gave the same values.
- Network: POST /api/customer/promo/apply 200 at 2026-11-19T12:20:35Z
- Result: mismatch
- Confidence: unsure: TC-10 shows the server stacks discounts; -1,550 = 1,200 + 350 (the SAVE10 discount from TC-02), so the value may be leftover state, not TREAT15 alone. A human should apply the code on a fresh account/session (or after clearing the server-side promo state) and read the Discount line.
- Human check: mismatch by Hakob Julfayan at 2026-11-19T12:38:02Z: 
- Decision: match by Hakob Julfayan at 2026-11-19T13:02:58Z: automated run 2 (new customer) passed with -1,200 / 6,800; the step 05 value was leftover state (SCRUM-9). No bug.

## SCRUM-7-TC-05

- Started: 2026-11-19T12:20:55Z
- Tool: playwright-mcp
- Steps: 1 ✓ (code removed, cart emptied) 2 ✓ (1 × Chicken katsu curry with vegetables 3,350 AMD + 1 × Pork curry rice & vegetables 3,600 AMD, both from the dish dialog) 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): The page shows "Add 1,050 AMD more to use this code" (8,000 − 6,950); no discount is applied
- Observed: "Add 1,050 AMD more to use this code" · Subtotal 6,950 AMD · Delivery Free · no Discount line · Total 6,950 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-06

- Started: 2026-11-19T12:21:37Z
- Tool: playwright-mcp
- Steps: 1 ✓ (cart emptied, no code applied) 2 ✓ (1 × Chicken Katsu Curry 3,150 + 1 × Yassai curry 2,900 + 1 × Salmon Maki 2,000, all from the dish dialog) 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): The page shows a discount of 1,208 AMD (15% of 8,050 = 1,207.5, rounded half up) and a new total of 6,842 AMD (8,050 − 1,208, delivery free because the 8,050 AMD subtotal is from 5,000 AMD)
- Observed: "TREAT15 applied: 15% off" · Subtotal 8,050 AMD · Delivery Free · "Discount (TREAT15)" "−1,208 AMD" · Total 6,842 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-07

- Started: 2026-11-19T12:22:23Z
- Tool: playwright-mcp
- Steps: 1 ✓ (code removed, 3 items removed with Remove item) 2 ✓ (1 × Chicken curry rice & vegetables, 3,000 AMD, from the dish dialog) 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): The page shows "This code has expired"; no discount is applied and the total stays 3,500 AMD (3,000 + 500 delivery)
- Observed: "This code has expired" · Subtotal 3,000 AMD · Delivery 500 AMD · no Discount line · Total 3,500 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-08

- Started: 2026-11-19T12:22:45Z
- Tool: playwright-mcp
- Steps: 1 ✓ (same clean cart as TC-07, which no code was applied to: 1 × Chicken curry rice & vegetables, 3,000 AMD) 2 ✓ 3 ✓ (Delivery) 4 ✓
- Expected (from spec.yaml): The page shows "Code not found"; no discount is applied and the total stays 3,500 AMD (3,000 + 500 delivery)
- Observed: "Code not found" · Subtotal 3,000 AMD · Delivery 500 AMD · no Discount line · Total 3,500 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-09

- Started: 2026-11-19T12:22:55Z
- Tool: playwright-mcp
- Steps: 1 ✓ (same clean cart, no code applied) 2 ✓ (1 × Chicken curry rice & vegetables, 3,000 AMD) 3 ✓ (Delivery) 4 ✓ (input value checked as " save10 " with the spaces)
- Expected (from spec.yaml): "Code not found" is not shown; the page shows a discount of 300 AMD and a new total of 3,200 AMD, the same as SAVE10
- Observed: "SAVE10 applied: 10% off" · Subtotal 3,000 AMD · Delivery 500 AMD · "Discount (SAVE10)" "−1,558 AMD" · Total 1,942 AMD. "Code not found" is not shown (that part matches). The discount is wrong, and it also differs from upper-case SAVE10 on the same cart (−350 in TC-02). Same values on a retry (12:23:09Z) and after a page reload (12:23:25Z).
- Result: mismatch
- Confidence: unsure: TC-10 shows the server stacks discounts; -1,558 = 1,208 (TC-06) + 350 (TC-02), so the value may be leftover state rather than what ' save10 ' alone gives. A human should apply the code on a fresh account/session (or after clearing the server-side promo state) and read the Discount line.
- Human check: mismatch by Hakob Julfayan at 2026-11-19T12:38:02Z: 

## SCRUM-7-TC-10

- Started: 2026-11-19T12:23:51Z
- Tool: playwright-mcp
- Steps: 1 ✓ (code removed, cart emptied) 2 ✓ (Dragon Roll dialog, quantity 2, 8,000 AMD) 3 ✓ (Delivery) 4 ✓ (SAVE10: "−800 AMD", Total 7,200 AMD, as the step notes) 5 ✓
- Expected (from spec.yaml): After the second Apply only TREAT15 is applied: the discount is 1,200 AMD (15% of 8,000, not 800 + 1,200) and the new total is 6,800 AMD
- Observed: "TREAT15 applied: 15% off" · Subtotal 8,000 AMD · Delivery Free · "Discount (TREAT15)" "−2,000 AMD" · Total 6,000 AMD. The label shows only TREAT15, but the discount is 800 + 1,200: the two discounts stack. A retry (remove, SAVE10, then TREAT15 at 12:24:35Z) gave the same values.
- Result: mismatch
- Confidence: sure

## SCRUM-7-TC-11

- Started: 2026-11-19T12:25:08Z
- Tool: playwright-mcp
- Steps: 1 ✓ (code removed, page reloaded; the cart from TC-10 already was 2 × Dragon Roll, 8,000 AMD, and no code was shown) 2 ✓ 3 ✓ (Delivery) 4 ✓ (SAVE10 showed "−2,800 AMD", Total 5,200 AMD: 800 + the 2,000 left over from TC-10) 5 ✓
- Expected (from spec.yaml): The page shows "This code has expired"; SAVE10 stays applied with a discount of 800 AMD (10% of 8,000) and a total of 7,200 AMD
- Observed: "This code has expired" · Subtotal 8,000 AMD · Delivery Free · no "SAVE10 applied" line, no Discount line · Total 8,000 AMD. The expired second code removed the applied SAVE10 (against Q-4). Even before OLD15, the SAVE10 discount was −2,800, not 800.
- Result: mismatch
- Confidence: sure

## SCRUM-7-TC-12

- Started: 2026-11-19T12:25:43Z
- Tool: playwright-mcp
- Steps: 1 ✓ (cart emptied; TC-11 left no code applied) 2 ✓ (1 × Chicken curry rice & vegetables, 3,000 AMD, from the dish dialog) 3 ✓ (Delivery) 4 ✓ (the step's note says 3,200 AMD; the page showed "−350 AMD", Total 3,150 AMD, the same defect as TC-02) 5 ✓ ("Remove promo code")
- Expected (from spec.yaml): After removing, no discount is shown and the total goes back to the original 3,500 AMD (3,000 + 500 delivery)
- Observed: no "applied" line, no Discount line · Subtotal 3,000 AMD · Delivery 500 AMD · Total 3,500 AMD
- Result: match
- Confidence: sure

## SCRUM-7-TC-13

- Started: 2026-11-19T12:26:15Z
- Tool: playwright-mcp
- Steps: 1 ✓ (cart emptied, no code applied) 2 ✓ (Oshinko Maki dialog, quantity 2, 3,000 AMD) 3 ✓ (Delivery) 4 ✓ (the step's note says 300 / 3,200; the page showed "−350 AMD", Total 3,150 AMD, as in TC-02) 5 ✓ (checkout has no quantity control, so I pressed "Decrease quantity" in the "Your order" sidebar on /chef/24, then opened /checkout)
- Expected (from spec.yaml): SAVE10 is still shown as the entered code, no discount is applied, the page shows "Add 1,500 AMD more to use this code" and the total is 2,000 AMD (1,500 + 500 delivery)
- Observed: Promo code field empty (value ""), no "SAVE10 applied" line, no "Add 1,500 AMD more to use this code" message · Subtotal 1,500 AMD · Delivery 500 AMD · Total 2,000 AMD. The total matches; the kept code and the message don't. Extra check: typing SAVE10 again on this cart does show "Add 1,500 AMD more to use this code".
- Result: mismatch
- Confidence: unsure: I chose how to lower the quantity (sidebar on the chef page plus navigation back to checkout), so I can't tell whether the code was dropped by the cart change or just by leaving the checkout page. A human should apply SAVE10 on a 3,000 AMD cart, change the quantity the way a customer would, and check whether SAVE10 and the "Add 1,500 AMD more…" message are still shown.
- Human check: mismatch by Hakob Julfayan at 2026-11-19T12:38:02Z: 

## SCRUM-7-TC-14

- Started: 2026-11-19T12:27:29Z
- Tool: playwright-mcp
- Steps: 1 ✓ (cart emptied, no code applied) 2 ✓ (1 × Chicken curry rice & vegetables, 3,000 AMD, from the dish dialog) 3 ✓ (Delivery; contact was prefilled from the account; I filled City "Yerevan", Street "Barekamutyan", Building "14", Apartment "37" (the field placeholders) and the note "STLC SCRUM-7 SCRUM-7-TC-14") 4 ✓ 5 ✓ (Place order at 12:27:46Z → /orders/success?number=FM-100002, then /orders)
- Expected (from spec.yaml): Checkout shows a total of 3,200 AMD before placing; the placed order (confirmation and order history) has a total of 3,200 AMD, not 3,500 AMD
- Observed: before placing: "SAVE10 applied: 10% off" · "Discount (SAVE10)" "−350 AMD" · Total 3,150 AMD. Confirmation: "Order placed! Your order number is FM-100002. …" with no total shown. Order history: "FM-100002 · Received · Alans Kitchen · 19 Nov 2026 · 3,150 AMD". The discount is kept on the order (not 3,500), but the amount is 3,150, not 3,200.
- Result: mismatch
- Confidence: unsure: the confirmation page shows no total, so the "confirmation … 3,200 AMD" part can't be read; I chose the delivery address myself. A human should open order FM-100002 (order detail/Track order) and check the charged total.
- Human check: mismatch by Hakob Julfayan at 2026-11-19T12:38:02Z: 

## Other observations

- Quick "Add <dish> to cart" button on /chef/24 adds the dish with all of its additions selected (Chicken curry rice & vegetables went in at 3,700 AMD with "+ Extra sticks, Wasabi, Soy Sauce, Marinated Ginger, Sweet Chile, Unagi sauce, Teriyaki sauce"). The dish dialog starts with none selected (3,000 AMD). This is outside SCRUM-7. I used the dish dialog for every case.
- The promo discount seems to build up on the server across applies: TC-10 gave 800 + 1,200 = −2,000; TC-11's first SAVE10 gave −2,800 (= 800 + 2,000 left over). After the expired-code attempt in TC-11, SAVE10 went back to −350 on 3,000 AMD. This likely explains the odd values in TC-04 (−1,550) and TC-09 (−1,558).
- SAVE10 on a 3,000 AMD subtotal with 500 AMD delivery gives −350 (10% of 3,500), every time it's applied first: TC-02, TC-12, TC-13, TC-14. The discount is taken from subtotal + delivery, against Q-1.
- The order confirmation page (/orders/success) shows no total.
