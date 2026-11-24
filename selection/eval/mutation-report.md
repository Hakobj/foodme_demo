# Selection evaluation: mutation benchmark

Commit `61d978466e` · impact map from `61d978466e` · 2026-11-24T12:15:44Z
Baseline (unmutated) full run: 138 e2e tests, 0 failing before any mutation.

| Metric | Value | Target |
|---|---|---|
| Fault detection rate (killed mutants caught by the selection) | 100% (11/11) | 100% |
| Mean test recall (failing tests that were selected) | 98% | ≥ 95% |
| Escaped failing tests | 1 | 0 |
| Median selection ratio (tests run / all) | 32% | ≤ 40% |
| Mean e2e time saved | 53% | ≥ 50% |
| Mutants the full suite did not kill | 2 | (suite gap, not selector) |
| Run-all decisions | 1 of 16 | |

| Mutation | Decision | Selected | Failing (full run) | Caught | Recall |
|---|---|---|---|---|---|
| `web-explore-kitchen-search` | impact map | 49/138 | 0 | — | — |
| `web-cart-free-delivery-boundary` | impact map | 63/138 | 1 | ✅ | 100% |
| `web-modal-additions-price` | impact map | 63/138 | 5 | ✅ | 80% |
| `web-checkout-city-message` | impact map | 13/138 | 1 | ✅ | 100% |
| `web-tracking-accepted-copy` | impact map | 10/138 | 1 | ✅ | 100% |
| `web-header-search-trim` | impact map | 116/138 | 1 | ✅ | 100% |
| `web-amd-format` | impact map | 116/138 | 17 | ✅ | 100% |
| `web-checkout-note-placeholder` | impact map | 20/138 | 1 | ✅ | 100% |
| `web-footer-disclaimer` | impact map | 116/138 | 1 | ✅ | 100% |
| `admin-orderlist-receiver` | impact map | 24/138 | 1 | ✅ | 100% |
| `admin-chef-delivery-label` | impact map | 5/138 | 2 | ✅ | 100% |
| `admin-dashboard-revenue-rejected` | impact map | 22/138 | 0 | — | — |
| `py-cart-panel-locator` | impact map | 63/138 | 5 | ✅ | 100% |
| `be-order-service` | backend: 3 endpoint(s) | 38/138 | (selection only) | | |
| `docs-readme` | ignored | 0/138 | (selection only) | | |
| `build-web-package` | run all | 138/138 | (selection only) | | |

## Escapes

- `web-modal-additions-price`: `tests-python/e2e/admin/test_admin_catalog.py::test_dashboard_counts_chefs_dishes_and_orders[chromium]`
