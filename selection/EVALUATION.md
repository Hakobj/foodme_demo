# Evaluating the Selection Based Testing workflow

A test selection makes two promises that pull in opposite directions:

1. **Safety.** If a change breaks something the full e2e suite would catch, the selection runs at least one test that catches it.
2. **Savings.** It runs much less than the full suite.

A selection that always runs everything is perfectly safe and useless. One that runs nothing is free and useless. So both are measured, against a **ground truth**: what the full suite says about the same change. Safety outranks savings: one escaped regression costs more than many minutes of CI.

## Metrics

| Metric | Definition | Target | Why |
|---|---|---|---|
| **Fault detection rate (FDR)** | changes the full suite catches, for which the selection also contains ≥ 1 failing test | **100%** | The main promise. The PR goes red either way. |
| **Test recall** | failing tests in the selection / failing tests in the full run (mean per change) | ≥ 95% | The developer sees the whole blast radius, not one failure. |
| **Escapes** | failing tests that were not selected (sum) | 0 | Every escape is analysed: map gap, rule gap, or flaky. |
| **Selection ratio** | selected tests / all tests (median per change) | ≤ 40% for a single-area change | Savings in test count. |
| **Time saved** | 1 − Σ recorded durations of the selected tests / Σ of all | ≥ 50% mean | Savings in wall time (tests differ: checkout ≈ 6 s, explore ≈ 0.5 s). |
| **Run-all rate** | changes that hit `RUN_ALL` or an unknown file | tracked | Too high means the rules are too coarse. Zero would be suspicious. |
| **Selection overhead** | time of `python -m selection select` | < 30 s | It must not eat the savings. |
| **Map freshness** | age of `impact-map.json`; tests that failed while it was recorded | ≤ 7 days, 0 failed | A stale or partial map is the main source of escapes. |

Precision (selected tests that fail) is **not** a target. Most selected tests pass, and that's correct: they cover the changed code and simply didn't break.

## Methods

### 1. Mutation benchmark (offline, before switching it on)

`python -m selection evaluate` injects each change from `mutations.py` into the working tree. They are small, realistic regressions spread across the storefront, the back office and the page objects, plus selection-only cases (backend, docs, build config). For each change it:

1. computes the selection for exactly that diff,
2. runs the **full** e2e suite as ground truth (failures already present in the unmutated baseline are subtracted),
3. scores FDR, recall, escapes, ratio and time, and restores the file.

A mutant the full suite doesn't kill is reported separately as a **suite gap, not a selector failure**. It shows where the 138 tests are blind, which is useful in its own right. The benchmark is slow by design: one full run per mutation, about 4–5 min each. It runs before adoption, and again after any change to `rules.py` or `impact.py`.

### 2. Shadow mode in CI (online, on every PR)

`selective-e2e.yml` runs the selection **and** the full suite on every PR while `SELECTION_SHADOW` is on. `python -m selection audit` compares them. Failures that pass on a rerun are flaky and not counted. A real failure that wasn't selected is an escape, and the `shadow` job goes red with the test's name. This measures the same metrics on real changes instead of synthetic ones, and it costs nothing in safety: the full run still gates the PR.

**Exit criterion:** 0 escapes over 4 weeks or 30 PRs that ran e2e, whichever comes later, with a median selection ratio ≤ 40%. Then set `SELECTION_SHADOW=false`. The full suite keeps running on every push to `main` (CI workflow) and nightly (impact-map job), so a late escape is still caught within a day. Every escape found later gets a root cause and a rule or map fix, and the benchmark gains a matching mutation.

### 3. History replay (cost trend)

`python -m selection history --commits 30` replays the selection over the last commits on `main`. It has no ground truth, but it shows what real changes would have cost: how many needed no e2e at all (docs, pipelines), how many ran everything, and the median ratio. The nightly job prints it, so a drift is visible: for example, more and more changes falling into run-all.

### 4. What each method can't see

| Blind spot | Why | Mitigation |
|---|---|---|
| Behaviour that only runs on code paths no test executed when the map was built | the map is built from the tests' own runs | `FALLBACK_SUITES` for files no test touched; the AI reviewer may add tests; new tests in a changed file are selected by prefix |
| Changes through data or config, not code (seed data, env vars, feature flags) | not a file the map knows | `RUN_ALL` for config, migrations, build files |
| Backend regressions | the CI e2e suite runs against the mock | endpoint mapping is ready; integration tests cover the backend |
| Flaky tests | a failure without a code cause | rerun filter in the audit; flaky tests are tracked, not counted as escapes |
| Mutants the suite can't kill | suite gap | listed separately; feeds new tests |

## Results (round 1, 2026-11-24)

Generated report: [eval/mutation-report.md](eval/mutation-report.md) (raw data in `eval/mutation-results.json`).
Map and suite: 138 e2e tests, all passing in the unmutated baseline. 16 changes: 13 with ground truth, 3 selection-only.

| Metric | Result | Target | |
|---|---|---|---|
| Fault detection rate | **100%** (11 of 11 killed mutants) | 100% | ✅ |
| Mean test recall | 98% | ≥ 95% | ✅ |
| Escaped failing tests | 1, a **flaky test**, not a map gap (see below) | 0 | ⚠️ → fixed |
| Median selection ratio | 32% | ≤ 40% | ✅ |
| Mean e2e time saved | 53% | ≥ 50% | ✅ |
| Mutants the full suite did not kill | 2 | — | suite gaps |
| Run-all decisions | 1 of 16 (the `package.json` change) | — | as intended |

Per change:
- A change local to one page selects 5–24 tests: the chef edit form (5), the tracking page (10), a checkout message (13), the note field (20), the admin orders list (24).
- Shared code selects 63 (cart and chef page, reached through the explore → chef → cart fixture) or 116 (the price formatter, header and footer, which every storefront page renders).
- A backend service maps to 3 endpoints and 38 tests. Docs select 0. A build file runs all 139.

**Findings and what changed:**

1. **The escape was a flaky test.** `test_dashboard_counts_chefs_dishes_and_orders` failed in 1 of 14 full runs, during a storefront mutation the admin app can't run. It showed `0` orders: the autouse login already rendered the dashboard before the test created its orders, and `/#/` is only a hash change, so react-admin could show its cached count. **Fixed:** the test reloads the page after creating the orders. In shadow mode the rerun filter would have classed it as flaky, not as an escape.
2. **Suite gap: kitchen search.** No search query in the suite matched a kitchen without also matching a chef name ("italian" also matches "Italiano"), so a broken kitchen match survived the full suite. **Fixed:** new case `japanese → Sakura Kitchen`. The suite is now 139 tests.
3. **Suite gap: dashboard revenue.** No test has a rejected or delivered order on the dashboard. This one is left open: a candidate for a new test.
4. **History replay** (40 commits on `main`) first showed 13 run-all decisions, from unknown paths: `workflows/statusline.sh`, the `.claude` symlink, `render.yaml`, and `ci/`. After the rules were tuned: 29 commits need no e2e at all, 8 run everything (dependency, Gradle and DB-migration changes, run-all on purpose), and the rest run a subset.

Round 1 was measured before fixes 1–2 and the rule tuning. The impact map was then rebuilt from 139 passing tests. A re-measurement (`python -m selection evaluate --label round2`) is the next step before relying on the numbers for the fixed cases.

**Decision:** the targets are met, so the selection runs on PRs in **shadow mode** (`selective-e2e.yml`), with the full suite still gating every PR, until the exit criterion above is reached.
