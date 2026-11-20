# Brief 05: glitchtip-repro
Run: SCRUM-8 · Source: glitchtip
Hypothesis under test: none (exploration)
Window: 2026-11-20T10:35Z – 2026-11-20T10:56Z (repro 10:44:38Z–10:46:00Z ± 10 min; key request POST /api/customer/promo/apply at 10:45:18Z)
Allowed: read only

## Do
1. List issues in backend, web and admin with events (lastSeen) in the window.
2. For each, fetch the latest event and check whether it falls in the window; record title, culprit, request URL, tags, top in-app frames.

## Questions (answer each yes / no / unknown with observations)
1. Is there any GlitchTip event in backend, web or admin inside the window?
2. Does any such event relate to /api/customer/promo/apply, /api/order/delivery-price or the /checkout page?
3. Does any event show an error text about promo, discount or totals?

## Save
artifacts/05-glitchtip-issues.json and artifacts/05-glitchtip-<issue-id>.json for each event in the window.
