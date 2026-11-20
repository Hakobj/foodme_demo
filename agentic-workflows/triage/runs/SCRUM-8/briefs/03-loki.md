# Brief 03: loki
Run: SCRUM-8 · Source: loki
Hypothesis under test: none (exploration)
Window: 2026-11-20T10:35Z – 2026-11-20T10:56Z (repro 10:44:38Z–10:46:00Z ± 10 min; key request POST /api/customer/promo/apply at 10:45:18Z, second apply ~10:45:37Z)
Allowed: read only

## Do
1. Start from `{app="foodme-backend"}` (check label names/values if that selector is empty) in the window.
2. Filter for the repro paths: `|~ "promo|delivery-price|/api/order"`. Also run the selector with `|~ "ERROR|WARN"` in the window.
3. Look for any line that logs a promo code, percent, discount, base, subtotal, delivery price or total.

## Questions (answer each yes / no / unknown with observations)
1. Are there backend log lines for /api/customer/promo/apply or /api/order/delivery-price in the window, and what do they say?
2. Does any line log values used for the discount (code, percent, subtotal, delivery price, base, discount, total)? Quote them.
3. Are there WARN or ERROR lines in the window, and which loggers/messages?
4. Is there any sign of a restart, deploy or startup (e.g. "Started", "Flyway") in the window?

## Save
artifacts/03-loki-promo.txt, artifacts/03-loki-errors.txt (each with the LogQL and range in a header line).
