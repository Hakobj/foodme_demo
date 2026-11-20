# Brief 04: prometheus
Run: SCRUM-8 · Source: prometheus
Hypothesis under test: none (exploration)
Window: 2026-11-20T10:35Z – 2026-11-20T10:56Z (repro 10:44:38Z–10:46:00Z ± 10 min; key request POST /api/customer/promo/apply at 10:45:18Z, second apply ~10:45:37Z)
Allowed: read only

## Do
1. `up{app="foodme-backend"}` (or the backend job) over the window, step 30s.
2. `http_server_requests_seconds_count` / `_sum` / `_max` by uri, method, status, outcome for `uri=~".*promo.*|.*delivery-price.*|/api/order.*"` over the window.
3. `process_start_time_seconds` (or JVM uptime) in the window, to see when the backend last started.

## Questions (answer each yes / no / unknown with observations)
1. Was the backend scraped (up = 1) during the whole window?
2. Are there requests to the promo apply URI in the window, with what status and outcome?
3. What are the latencies (mean and max) of the promo apply and delivery-price URIs?
4. Are there any 4xx/5xx statuses for those URIs in the window?
5. When did the backend process last start?

## Save
artifacts/04-prom-up.json, artifacts/04-prom-http.json, artifacts/04-prom-start.json (each with PromQL, range and step).
