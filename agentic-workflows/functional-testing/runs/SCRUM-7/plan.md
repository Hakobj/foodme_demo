# Test plan: SCRUM-7, promo codes at checkout

SUT: https://foodme-hakobjulfayan.onrender.com/ · Requirements: `spec.yaml` (approved 2026-11-19 by Hakob Julfayan)

## 1. Scope

**In scope:** AC-1 to AC-7, plus the expected behaviour settled by the answers to Q-1 to Q-8.

**Out of scope (from spec.yaml):** Free-delivery codes · Chef-specific codes · First-order-only codes.

**Also not tested, with the reason:**
- **The free-delivery threshold when a discount moves the subtotal across 5,000 AMD** (e.g. SAVE10 on 5,200 → 4,680). Q-1 says delivery is added after the discount, but no AC or answer says whether "free from 5,000" is checked before or after it. All test data stays clear of 5,000–5,556 AMD, so no case depends on this. It is listed as an open question in the report.
- **Promo codes through the API alone** (`POST /api/order` with a code). The ACs describe the checkout page. TC-14 checks the placed order through the UI.
- **Admin management of codes.** Codes are launch data, and no AC covers them.
- **Concurrency, performance and localisation (hy/ru).** No AC covers them.

## 2. Approach per AC

| AC | Partitions / boundaries | Technique | Level | Cases planned |
|---|---|---|---|---|
| AC-1 | field + Apply present; empty field → Apply disabled (**Q-7**) | EP | manual 05 + automated 06 | TC-01 |
| AC-2 | valid code, discount on the **items subtotal**, delivery added after (**Q-1**); fractional discount rounded half-up to whole AMD (**Q-2**); placed order keeps the discount (**Q-8**) | EP, BVA (at minimum) | manual + automated | TC-02, TC-04, TC-06, TC-14 |
| AC-3 | SAVE10: below (2,900) / at (3,000); TREAT15: below (6,950) / at (8,000); `{missing amount}` with a thousands separator (**Q-6**) | BVA below / at the minimum | manual + automated | TC-02, TC-03, TC-04, TC-05 |
| AC-3 | applied code, then the cart drops below the minimum → code stays, discount dropped, message shown (**Q-3**) | state transition | manual + automated | TC-13 |
| AC-4 | expired code OLD15 → "This code has expired" | EP | manual + automated | TC-07 |
| AC-5 | unknown code → "Code not found"; lower case + spaces " save10 " accepted (**Q-5**) | EP | manual + automated | TC-08, TC-09 |
| AC-6 | apply SAVE10 → apply TREAT15 replaces it; apply SAVE10 → apply OLD15 keeps SAVE10 (**Q-4**) | state transition | manual + automated | TC-10, TC-11 |
| AC-7 | apply → remove → total back to the original | state transition | manual + automated | TC-12 |

14 cases in total, with no duplicate partitions. "Above the minimum" is covered by TC-06 (8,050 > 8,000) and TC-10/TC-11.

## 3. Test data

Chef **Alans Kitchen** (id 24, `/api/chef/24`): delivery **500 AMD**, free delivery from **5,000 AMD**, methods DELIVERY and TAKEAWAY. All the dishes are ACTIVE with a minimum quantity of 1. Prices come from `GET /api/dish/24/active`.

| Dish (id) | Price (AMD) |
|---|---|
| Oshinko Maki (277) | 1,500 |
| Salmon Maki (274) | 2,000 |
| Yassai curry (246) | 2,900 |
| Chicken curry rice & vegetables (247) | 3,000 |
| Chicken Katsu Curry (248) | 3,150 |
| Chicken katsu curry with vegetables (245) | 3,350 |
| Pork curry rice & vegetables (258) | 3,600 |
| Dragon Roll (288) | 4,000 |

| Case | Cart | Subtotal | Code | Expected discount | Expected subtotal after discount | Delivery* | Expected total / message |
|---|---|---|---|---|---|---|---|
| TC-01 | 1× Chicken curry rice (247) | 3,000 | (empty) | none | none | 500 | Apply disabled |
| TC-02 | 1× 247 | 3,000 | SAVE10 | 3,000 × 10% = **300** | 2,700 | 500 | **3,200** |
| TC-03 | 1× Yassai curry (246) | 2,900 | SAVE10 | none | none | 500 | "Add **100** AMD more to use this code" (3,000 − 2,900) |
| TC-04 | 2× Dragon Roll (288) | 8,000 | TREAT15 | 8,000 × 15% = **1,200** | 6,800 | 0 | **6,800** |
| TC-05 | 1× 245 + 1× 258 | 3,350 + 3,600 = 6,950 | TREAT15 | none | none | 0 | "Add **1,050** AMD more to use this code" (8,000 − 6,950) |
| TC-06 | 1× 248 + 1× 246 + 1× 274 | 3,150 + 2,900 + 2,000 = 8,050 | TREAT15 | 8,050 × 15% = 1,207.5 → **1,208** | 6,842 | 0 | **6,842** |
| TC-07 | 1× 247 | 3,000 | OLD15 | none | none | 500 | "This code has expired", total 3,500 |
| TC-08 | 1× 247 | 3,000 | NOPE99 | none | none | 500 | "Code not found", total 3,500 |
| TC-09 | 1× 247 | 3,000 | `" save10 "` | **300** | 2,700 | 500 | **3,200** (same as TC-02) |
| TC-10 | 2× 288 | 8,000 | SAVE10, then TREAT15 | 800, then **1,200** | 7,200, then 6,800 | 0 | **6,800**, TREAT15 is the only code shown |
| TC-11 | 2× 288 | 8,000 | SAVE10, then OLD15 | **800** stays | 7,200 | 0 | "This code has expired", SAVE10 still applied, **7,200** |
| TC-12 | 1× 247 | 3,000 | SAVE10, then remove | 300, then none | 2,700, then 3,000 | 500 | 3,200, then **3,500** |
| TC-13 | 2× Oshinko Maki (277), then 1× | 3,000, then 1,500 | SAVE10 | 300, then none | 2,700, then none | 500 | 3,200, then code still shown + "Add **1,500** AMD more to use this code", total **2,000** |
| TC-14 | 1× 247, DELIVERY, place order | 3,000 | SAVE10 | **300** | 2,700 | 500 | the confirmation and order history show **3,200** |

\* Delivery is expected to be 500 below 5,000 AMD and 0 from 5,000 AMD, judged on the subtotal **before** the discount. All the data stays out of the ambiguous 5,000–5,556 range (see Scope). If the checkout page shows a different delivery line (e.g. one that depends on the address), the expected total is the discounted subtotal plus the delivery line shown, and the case notes it.

## 4. Environment

- **SUT:** https://foodme-hakobjulfayan.onrender.com/ (storefront, single origin, `/api/**`).
- **Browser for step 05:** Playwright MCP; Claude in Chrome as the fallback.
- **Account:** a customer account that the human signs in to that browser before step 05 (needed for checkout and TC-14). No credentials are stored in the run files.
- **Noise to ignore:** random 200–1,500 ms API latency, a cold start of up to about a minute on Render's free tier, "flaky heartbeat" errors in GlitchTip, and `/api/debug/boom`. None of these is a finding.

## 5. Risks

**A correct app that looks broken:**
- Latency and cold starts: assertions wait for the visible text or total (web-first waits), never fixed sleeps. Warm the SUT before a run.
- A cart left over from earlier runs, or from another chef, changes the subtotal. Every case starts by emptying the cart.
- The delivery line can differ from 500/0 (address, takeaway). Read it and state it in the case.
- Number formatting ("3,200 AMD" vs "3 200 ֏"): compare numeric values, and compare exact text only for the AC messages (Q-6).

**A broken app that looks correct:**
- Asserting the numbers the app shows instead of the computed values above. Expected values come only from this plan's arithmetic and the answers to the questions.
- Checking only the checkout page while the placed order is charged the full price (TC-14 covers this).
- A replacement that looks right but adds both discounts (TC-10 checks that the total is exactly 6,800).
- Seeded bugs (`FM-BUG-NN`) may sit in this flow. Mismatches are reported, not explained away.

## 6. Exit criteria

- Every AC (AC-1 to AC-7) is covered by at least one case: see the table in §2.
- All 14 cases are executed manually (step 05) and automated as Playwright specs (step 06), and the suite is run (step 08).
- Every mismatch from 05 and every failure from 08 is listed in the report as **not triaged**, with a bug candidate in `found_issues.json`.
