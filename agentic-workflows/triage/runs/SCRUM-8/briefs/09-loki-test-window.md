# Brief 09: loki-test-window
Run: SCRUM-8 · Source: loki
Hypothesis under test: H-1 "the backend applies the percent to subtotal + delivery price" (the brief-06 test applies at 10:50:25Z, 10:50:43Z, 10:51:33Z)
Window: 2026-11-20T10:44:00Z – 2026-11-20T11:05:00Z
Allowed: read only

Note: the earlier Loki query (brief 03) may have run before the brief-06 requests were made; this brief queries the same host again now.

## Do
1. Record the UTC time you run the queries.
2. `{app="foodme-backend"} |~ "promo|delivery-price"` over the window.
3. Count the lines per logger over the window.

## Questions (answer each yes / no / unknown with observations)
1. Are there `promo.applied` lines between 10:50:00Z and 10:52:00Z, and what code, status and discount do they log?
2. Are there HTTP log lines for POST /api/customer/promo/apply between 10:50:00Z and 10:52:00Z, and what request subtotal / deliveryMethod and response discount / deliveryPrice / total do they show?
3. How many POST /api/order/delivery-price lines are in the window?
4. Is any `promo.applied` line in the window logged with `stacked` or `previous` fields?

## Save
artifacts/09-loki-promo.txt (with the LogQL, the range and the query time in a header line).
