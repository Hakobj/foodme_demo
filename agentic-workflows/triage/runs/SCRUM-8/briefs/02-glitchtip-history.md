# Brief 02: glitchtip-history
Run: SCRUM-8 · Source: glitchtip
Hypothesis under test: none (exploration)
Window: 2026-11-13T00:00Z – 2026-11-20T11:30Z (last 7 days; focus on 2026-11-19T11:48Z – 12:58Z around first_seen 12:18:20Z)
Allowed: read only

## Do
1. List issues in projects backend, web and admin in the window.
2. Look for issues whose title, culprit, request URL or message mentions promo, discount, checkout, cart, orders, or the paths /api/customer/promo/**, /api/cart/**, /api/orders/**.
3. For each matching issue, fetch the latest event and record title, culprit, first/last seen, event count, top in-app frames, request URL, tags.

## Questions (answer each yes / no / unknown with observations)
1. Is there any issue in backend, web or admin matching promo / discount / checkout / cart / orders paths in the window?
2. Is there any event between 2026-11-19T11:48Z and 12:58Z in any project, and what are they?
3. Do any matching events show an exception or error text on the promo apply or order placement request?

## Save
artifacts/02-glitchtip-issues-<project>.json and artifacts/02-glitchtip-<issue-id>.json for each matching issue.
