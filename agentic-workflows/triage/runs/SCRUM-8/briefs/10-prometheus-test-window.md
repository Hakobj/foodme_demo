# Brief 10: prometheus-test-window
Run: SCRUM-8 · Source: prometheus
Hypothesis under test: H-1 "the backend applies the percent to subtotal + delivery price" (the brief-06 test applies at 10:50:25Z, 10:50:43Z, 10:51:33Z)
Window: 2026-11-20T10:44:00Z – 2026-11-20T11:05:00Z
Allowed: read only

Note: the earlier Prometheus query (brief 04) may have run before the brief-06 requests were made, or its last sample (10:52:30Z) was the latest data then; this brief queries the same target again now.

## Do
1. Record the UTC time you run the queries.
2. `http_server_requests_seconds_count{uri=~".*promo/apply|.*delivery-price"}` by uri, method, status, outcome over the window, step 30s.
3. `process_start_time_seconds` and `up{app="foodme-backend"}` over the window, step 30s.

## Questions (answer each yes / no / unknown with observations)
1. What is the promo apply counter at 10:50:00Z and at 10:52:30Z (or the latest sample), and when does it change?
2. What is the delivery-price counter at the same times?
3. Are all promo apply requests in the window status 200 / outcome SUCCESS?
4. Did the backend restart in the window (process_start_time_seconds changes)?
5. What is the time of the latest sample returned?

## Save
artifacts/10-prom-http.json, artifacts/10-prom-start.json (with PromQL, range, step and query time).
