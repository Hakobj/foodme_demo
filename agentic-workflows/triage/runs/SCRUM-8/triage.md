# Triage SCRUM-8 — promo discount calculated on subtotal + delivery

Run: `agentic-workflows/triage/runs/SCRUM-8/` · SUT https://foodme-hakobjulfayan.onrender.com/ · judge: round 1 `fail` (fixed), round 2 `unsure`

## 1. Problem

As confirmed in `problem.yaml` (Hakob Julfayan, 2026-11-20T10:43:21Z): for a signed-in customer at checkout with paid delivery, SAVE10 on 1 × Chicken curry rice & vegetables (3,000 AMD) + Delivery 500 AMD gives **−350 AMD / total 3,150 AMD** instead of **−300 AMD / 3,200 AMD**, and the placed order FM-100002 is charged 3,150 AMD.

**Reproduced:** yes, at 2026-11-20T10:45:18Z on a clean account (empty cart, no code): "SAVE10 applied: 10% off ; Subtotal 3,000 AMD ; Delivery 500 AMD ; Discount (SAVE10) −350 AMD ; Total 3,150 AMD" ([01-page-text](artifacts/01-page-text.txt), [01-checkout.png](artifacts/01-checkout.png)). No order was placed in this run.

## 2. Root-cause candidates

| id | candidate | layer | rating | confidence | key evidence (quoted) | artifacts | judge |
|---|---|---|---|---|---|---|---|
| H-1 | Backend promo quote applies the percent to subtotal + delivery price | backend | ✅ confirmed | 95 | `double fullTotal = subtotal + deliveryPrice;` · Takeaway `"discount":300.0,"deliveryPrice":0.0` vs Delivery `"discount":350.0,"deliveryPrice":500.0` · 4,000 + 500 → `discount=450.0` | [06-network](artifacts/06-network.json), [09-loki-promo](artifacts/09-loki-promo.txt), [08-code-promo-apply](artifacts/08-code-promo-apply.txt), [08-code-order-place](artifacts/08-code-order-place.txt) | all PASS |
| H-4 | Deploy / version mismatch | infra | 🟠 unlikely | 3 | live apply response has exactly the 7 DTO fields of ff70db0; backend up since 10:13:01Z, still 350 | [04-prom-start](artifacts/04-prom-start.json), [08-code-promo-apply](artifacts/08-code-promo-apply.txt) | J4 UNSURE |
| H-2 | Leftover per-customer promo state (SCRUM-9) adds 50 | data | ❌ ruled out | 2 | Takeaway gave `discount=300.0`, not 350; no `stacked` field in any `promo.applied` line | [06-network](artifacts/06-network.json), [09-loki-promo](artifacts/09-loki-promo.txt), [08-code-promo-cache](artifacts/08-code-promo-cache.txt) | all PASS |
| H-3 | Storefront sends a wrong subtotal / computes the discount | web | ❌ ruled out | 2 | request `"subtotal":3000`; page shows `discount={appliedPromo?.discount ?? 0}` from the server | [01-network](artifacts/01-network.json), [08-code-web-checkout](artifacts/08-code-web-checkout.txt) | all PASS |
| H-5 | Cold start / timeout / infra error | infra | ❌ ruled out | 1 | all promo/apply 200 SUCCESS; only demo heartbeat WARNs | [04-prom-http](artifacts/04-prom-http.json), [10-prom-http](artifacts/10-prom-http.json), [03-loki-errors](artifacts/03-loki-errors.txt) | all PASS |

**H-1 (✅ 95%).** The storefront sends only `subtotal` and `deliveryMethod` to `POST /api/customer/promo/apply`. `OrderService.applyPromo` looks up the delivery price for the method and calls `PromoService.quote(code, subtotal, deliveryPrice)`, which computes `fullTotal = subtotal + deliveryPrice` (PromoService.java:30) and `discount = Math.round(fullTotal * percent / 100.0)` (:48), at commit ff70db0 (`origin/feature/KAN-27-promo-code`). Order placement (`OrderService.createOrder`, lines 203–217) calls the same `quote` and stores `subtotal - discount + deliveryPrice`, so the placed order gets the same −350. *Prediction:* Takeaway (delivery 0) → −300; Delivery on 3,000 → −350; Delivery on 4,000 → −450; H-2 predicts −350 on Takeaway. *Test (brief 06, confirmed in Loki/Prometheus by 09/10):* −300 / −350 / −450 → **matched**.

**H-4 (🟠 3%).** An old build could serve other rules. Against: the backend restarted at 10:13:01Z and still returns 350, and the response shape matches ff70db0 exactly. The deployed commit itself is not visible from the repo, so this is left at *unlikely* rather than *ruled out* (judge UNSURE, see §5).

**H-2 (❌ 2%).** The per-customer cache in `OrderService` (line 51) adds a previous discount only when the cached code differs (lines 104–107). With only SAVE10 applied and Takeaway giving exactly −300, a leftover amount is contradicted.

**H-3 (❌ 2%).** The request carries `subtotal: 3000`; the page shows the server's discount and computes Total = subtotal − discount + delivery, which equals the server's total.

**H-5 (❌ 1%).** No 4xx/5xx, no errors on the promo path, no restart in the window.

## 3. Evidence by source

- **Playwright:** repro at 10:45:18Z (−350) and the discriminating test 10:50:25–10:51:33Z (−300 / −350 / −450), with request and response bodies. [findings/01-repro.json](findings/01-repro.json), [findings/06-test-base.json](findings/06-test-base.json)
- **Loki:** `promo.applied code=SAVE10 status=APPLIED discount=350.0` at 10:45:18Z; 300.0 / 350.0 / 450.0 at 10:50:25Z / 10:50:43Z / 10:51:31Z with matching HTTP bodies; no ERROR; no `stacked`. [findings/03-loki.json](findings/03-loki.json), [findings/09-loki-test-window.json](findings/09-loki-test-window.json)
- **Prometheus:** up = 1 throughout; promo/apply all 200 SUCCESS; counter 1 → 4 across the test; process start 10:13:01Z, no restart. [findings/04-prometheus.json](findings/04-prometheus.json), [findings/10-prometheus-test-window.json](findings/10-prometheus-test-window.json)
- **GlitchTip:** no event on the promo or order requests, 7-day history and repro window; only demo heartbeat jobs and storefront background-task errors. [findings/02-glitchtip-history.json](findings/02-glitchtip-history.json), [findings/05-glitchtip-repro.json](findings/05-glitchtip-repro.json)
- **Code:** working tree (`feature/task2-triage-pipeline`) has no promo code ([findings/07-code-promo.json](findings/07-code-promo.json)); read at ff70db0 via `git show` ([findings/08-code-promo-branch.json](findings/08-code-promo-branch.json)).

## 4. Unexplained

None. Side observations, explained:
- The re-apply at ~10:45:37Z sent no request: the storefront caches the promo query for 30 s on key `[promo, code, chefId, subtotal, deliveryMethod]` (code reading, not run).
- Briefs 03/04 showed one apply through 10:52:30Z: they were queried before the test in brief 06 ran; the re-query (09/10) shows all three test applies.
- GlitchTip BACKEND-6 (`POST /api/order` not-null violation on `order_dish_addition`, env `local`, 2026-11-19T11:43:50Z) is a different problem.

**Not checked / open:** the deployed commit on Render (assumed ff70db0 from matching behaviour, response shape and log format); no new order was placed, so the 3,150 AMD order rests on FM-100002 from the SCRUM-7 run plus the `createOrder` code.

## 5. Judge

| round | verdict | non-PASS checks |
|---|---|---|
| 01 | fail | **A1 FAIL** (analysis): Loki/Prometheus showed none of the brief-06 applies, not listed. → Fixed by re-querying (briefs 09, 10). **H-1 J4 UNSURE**: same gap. → Resolved (round 2 PASS). |
| 02 | unsure | **H-4 J4 UNSURE**: test result `contradicted` but rated `unlikely`; kept at *unlikely* because the deployed commit can't be verified. |

## 6. Proposed Jira update

Labels to add: `triaged`, `rc-backend` (keep `bug`, `checkout`, `foodme`, `promo-codes`).

```markdown
## Triage result — confirmed (95%)
**Root cause:** `PromoService.quote` computes the promo discount as percent × (subtotal + delivery price) instead of percent × items subtotal. The same method is used by `POST /api/customer/promo/apply` and by order placement, so both the checkout summary and the placed order get the inflated discount.
**Layer:** backend · **Where:** `apps/backend/src/main/java/am/foodme/backend/service/PromoService.java:30` (`double fullTotal = subtotal + deliveryPrice;`) and `:48` (`double discount = Math.round(fullTotal * promo.getPercent() / 100.0);`) at commit ff70db0 (feature/KAN-27-promo-code); called from `OrderService.applyPromo` and `OrderService.createOrder`.
**Mechanism:** the storefront sends only `subtotal` and `deliveryMethod`; the backend looks up the delivery price (500), adds it to the subtotal and takes 10% of 3,500 = 350; the response is `discount 350, total 3150`, and `createOrder` stores `subtotal − discount + delivery` = 3,150.
**How it was tested:** same 3,000 AMD cart with Takeaway (delivery 0) → −300; with Delivery (500) → −350; 4,000 AMD cart with Delivery → −450 (10% of 4,500). A leftover-discount explanation (SCRUM-9) predicted −350 on Takeaway → contradicted.
**Evidence:**
- Playwright 2026-11-20T10:45:18Z: "Discount (SAVE10) −350 AMD ; Total 3,150 AMD"; response `"discount":350.0,"deliveryPrice":500.0,"total":3150.0`
- Loki 10:50:25Z: `promo.applied code=SAVE10 status=APPLIED discount=300.0` (TAKEAWAY, `"deliveryPrice":0.0`)
- Loki 10:50:43Z: `discount=350.0` (DELIVERY 3000); 10:51:31Z: `discount=450.0` (DELIVERY 4000)
- Prometheus: all `/api/customer/promo/apply` 200 SUCCESS, no restart since 10:13:01Z
- GlitchTip: no error on the promo or order requests
**Other candidates:** H-2 leftover promo state (SCRUM-9) — ruled out; H-3 storefront sends/computes wrong values — ruled out; H-4 deploy mismatch — unlikely; H-5 cold start/timeout — ruled out
**Not checked / open:** the deployed commit on Render isn't visible from the repo (behaviour, response shape and logs match ff70db0); no new order was placed in triage, the 3,150 AMD charge is from FM-100002 (SCRUM-7 run).
_Triage run: agentic-workflows/triage/runs/SCRUM-8/ · judge unsure (1 UNSURE on H-4 rating, 0 FAIL)_
```
