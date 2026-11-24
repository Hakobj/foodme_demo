"""Selection Based Testing: selector rules, backend endpoint mapping, junit parsing, pytest filtering."""

import time
from pathlib import Path

import pytest

from selection.backend import BackendIndex, normalize_path
from selection.evaluate import aggregate, junit_results
from selection.pytest_plugin import filter_items
from selection.selector import Change, Selector

WEB = "tests-python/e2e/web/"
ADMIN = "tests-python/e2e/admin/"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
SMOKE = f"{ADMIN}test_admin_flows.py::TestAdminAuth::test_logs_in_with_seeded_credentials[chromium]"


def make_map(**tests) -> dict:
    return {"meta": {"generated_at": NOW, "commit": "abc"}, "tests": tests}


@pytest.fixture
def selector() -> Selector:
    return Selector(
        make_map(
            **{
                f"{WEB}test_explore.py::test_search[chromium]": {
                    "files": ["apps/web/src/pages/Explore/index.tsx", "pages/web/explore_page.py"],
                    "endpoints": ["GET /api/chef/active"],
                    "duration": 2.0,
                    "outcome": "passed",
                },
                f"{WEB}test_checkout.py::test_place[chromium]": {
                    "files": ["apps/web/src/pages/Checkout/index.tsx", "apps/web/src/lib/utils.ts"],
                    "endpoints": ["POST /api/order", "POST /api/order/delivery-price"],
                    "duration": 6.0,
                    "outcome": "passed",
                },
                f"{ADMIN}test_admin_flows.py::TestAdminAuth::test_logs_in_with_seeded_credentials[chromium]": {
                    "files": ["apps/admin/src/pages/LoginPage.jsx"],
                    "endpoints": ["POST /admin/auth/login"],
                    "duration": 1.0,
                    "outcome": "passed",
                },
                f"{WEB}test_happy_path.py::test_admin_can_login[chromium]": {
                    "files": ["apps/admin/src/*"],  # cross-origin: whole admin app
                    "endpoints": [],
                    "duration": 1.0,
                    "outcome": "passed",
                },
            }
        )
    )


def run(selector: Selector, *paths: str, lines: set[int] | None = None):
    selection = selector.select([Change(p, "M", lines or set()) for p in paths])
    return selection, set(selector.expand(selection))


def test_front_end_change_selects_only_tests_that_ran_the_module(selector):
    selection, tests = run(selector, "apps/web/src/pages/Explore/index.tsx")
    assert selection.mode == "subset"
    assert tests - {SMOKE} == {f"{WEB}test_explore.py::test_search[chromium]"}


def test_admin_change_also_selects_the_cross_origin_wildcard_test(selector):
    _, tests = run(selector, "apps/admin/src/pages/LoginPage.jsx")
    assert f"{WEB}test_happy_path.py::test_admin_can_login[chromium]" in tests
    assert f"{ADMIN}test_admin_flows.py::TestAdminAuth::test_logs_in_with_seeded_credentials[chromium]" in tests


def test_page_object_change_uses_the_python_footprint(selector):
    _, tests = run(selector, "pages/web/explore_page.py")
    assert tests - {SMOKE} == {f"{WEB}test_explore.py::test_search[chromium]"}


@pytest.mark.parametrize("path", ["README.md", "agentic-workflows/triage/runs/X/triage.md", "apps/web/e2e/a.spec.ts"])
def test_ignored_files_select_nothing(selector, path):
    selection, tests = run(selector, path)
    assert selection.mode == "subset"
    assert tests == set()


@pytest.mark.parametrize("path", ["apps/web/package-lock.json", "tests-python/e2e/conftest.py", "selection/rules.py"])
def test_run_all_files(selector, path):
    selection, tests = run(selector, path)
    assert selection.mode == "all"
    assert len(tests) == 4


def test_unknown_file_runs_everything(selector):
    selection, _ = run(selector, "scripts/new-tool.sh")
    assert selection.mode == "all"


def test_new_web_module_not_in_map_falls_back_to_the_web_suite(selector):
    selection, tests = run(selector, "apps/web/src/components/sections/new-banner.tsx")
    assert selection.mode == "subset"
    assert WEB in selection.selected
    assert all(t.startswith(WEB) for t in tests - {SMOKE})


def test_changed_test_file_selects_its_tests_including_new_ones(selector):
    selection, tests = run(selector, f"{WEB}test_checkout.py")
    assert f"{WEB}test_checkout.py::" in selection.selected  # prefix: also new tests not in the map
    assert f"{WEB}test_checkout.py::test_place[chromium]" in tests


def test_smoke_tests_are_added_only_when_something_was_selected(selector):
    selection, _ = run(selector, "apps/web/src/pages/Explore/index.tsx")
    assert "tests-python/e2e/admin/test_admin_flows.py::TestAdminAuth::test_logs_in_with_seeded_credentials" in (
        selection.selected
    )
    docs_only, tests = run(selector, "README.md")
    assert tests == set()
    assert not docs_only.selected


def test_missing_map_runs_everything():
    selection = Selector(None).select([Change("apps/web/src/main.tsx", "M")])
    assert selection.mode == "all"
    assert selection.warnings


def test_stale_map_warns():
    old = Selector({"meta": {"generated_at": "2020-01-01T00:00:00Z"}, "tests": {}})
    assert any("days old" in w for w in old.select([]).warnings)


# ---- backend mapping -------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def backend() -> BackendIndex:
    return BackendIndex(REPO)


def test_normalize_path_unifies_ids_and_path_variables():
    assert (
        normalize_path("/api/dish/10/active") == normalize_path("/api/dish/{chefId}/active") == "/api/dish/{*}/active"
    )
    assert normalize_path("/api/order/number/FM-100001") == "/api/order/number/{*}"


def test_controller_constants_are_resolved(backend):
    endpoints = {h.endpoint for hs in backend.controllers.values() for h in hs}
    assert {
        "GET /api/chef/active",
        "PATCH /admin/order/{*}/status",
        "POST /api/customer/orders/{*}/review",
    } <= endpoints


def test_service_change_reaches_its_controllers(backend):
    endpoints = backend.endpoints_for_change(
        "apps/backend/src/main/java/am/foodme/backend/service/OrderReviewService.java"
    )
    assert "POST /api/customer/orders/{*}/review" in endpoints
    assert "POST /admin/auth/login" not in endpoints


def test_change_inside_one_handler_selects_only_that_endpoint(backend):
    path = "apps/backend/src/main/java/am/foodme/backend/controller/api/OrderController.java"
    handler = next(h for h in backend.controllers[path] if h.endpoint == "GET /api/order/number/{*}")
    assert backend.endpoints_for_change(path, {handler.first_line + 1}) == {"GET /api/order/number/{*}"}


def test_backend_change_selects_tests_by_endpoint(selector):
    _, tests = run(selector, "apps/backend/src/main/java/am/foodme/backend/service/OrderService.java")
    assert tests >= {f"{WEB}test_checkout.py::test_place[chromium]"}
    assert f"{WEB}test_explore.py::test_search[chromium]" not in tests


# ---- evaluation helpers --------------------------------------------------------------------


def test_junit_results_map_to_node_ids(tmp_path):
    junit = tmp_path / "j.xml"
    junit.write_text(
        '<testsuites><testsuite name="pytest">'
        '<testcase classname="tests-python.e2e.web.test_x" name="test_a[chromium]"/>'
        '<testcase classname="tests-python.e2e.admin.test_y.TestAuth" name="test_b[chromium]">'
        '<failure message="boom"/></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert junit_results(junit) == {
        "tests-python/e2e/web/test_x.py::test_a[chromium]": "passed",
        "tests-python/e2e/admin/test_y.py::TestAuth::test_b[chromium]": "failed",
    }


def test_aggregate_scores_detection_recall_and_cost():
    rows: list[dict] = [
        {"ground_truth": True, "killed": True, "detected": True, "recall": 1.0, "escaped": [], "selected": 10,
         "total": 100, "selected_minutes": 1.0, "total_minutes": 10.0, "mode": "subset"},
        {"ground_truth": True, "killed": True, "detected": False, "recall": 0.0, "escaped": ["t"], "selected": 5,
         "total": 100, "selected_minutes": 0.5, "total_minutes": 10.0, "mode": "subset"},
        {"ground_truth": True, "killed": False, "detected": None, "recall": None, "escaped": [], "selected": 0,
         "total": 100, "selected_minutes": 0.0, "total_minutes": 10.0, "mode": "subset"},
    ]  # fmt: skip
    totals = aggregate(rows)
    assert totals["fault_detection_rate"] == 0.5
    assert totals["escaped_tests"] == 1
    assert totals["survived_full_suite"] == 1


class FakeItem:
    def __init__(self, nodeid: str, e2e: bool = True):
        self.nodeid, self._e2e = nodeid, e2e

    def get_closest_marker(self, name):
        return object() if name == "e2e" and self._e2e else None


def test_filter_items_keeps_selected_prefixes_and_non_e2e_tests():
    items = [
        FakeItem(f"{WEB}test_a.py::test_one[chromium]"),
        FakeItem(f"{WEB}test_a.py::test_new[chromium]"),
        FakeItem(f"{WEB}test_b.py::test_two[chromium]"),
        FakeItem("tests-python/unit/test_u.py::test_u", e2e=False),
    ]
    keep, drop = filter_items(items, {"mode": "subset", "selected": [f"{WEB}test_a.py::"]})  # type: ignore[arg-type]
    assert [i.nodeid for i in keep] == [
        f"{WEB}test_a.py::test_one[chromium]",
        f"{WEB}test_a.py::test_new[chromium]",
        "tests-python/unit/test_u.py::test_u",
    ]
    assert [i.nodeid for i in drop] == [f"{WEB}test_b.py::test_two[chromium]"]


def test_ai_additions_are_add_only_and_limited_to_known_tests(selector):
    from selection.selector import merge_additions

    selection = selector.select([Change("apps/web/src/pages/Explore/index.tsx", "M")]).to_json()
    before = set(selection["selected"])
    merged, accepted = merge_additions(
        selector,
        selection,
        [
            {"test": f"{WEB}test_checkout.py::test_place", "reason": "checkout reads the explore filter"},
            {"test": "tests-python/e2e/web/test_nope.py::test_x", "reason": "unknown test"},
            {"test": "rm -rf /", "reason": "garbage"},
            "not a dict",
        ],
    )
    assert [a["test"] for a in accepted] == [f"{WEB}test_checkout.py::test_place"]
    assert before < set(merged["selected"])
    assert merged["reasons"][f"{WEB}test_checkout.py::test_place"] == ["AI reviewer: checkout reads the explore filter"]


def test_suite_conftest_selects_its_whole_suite(selector):
    selection, tests = run(selector, "tests-python/e2e/web/conftest.py")
    assert WEB in selection.selected
    assert {t for t in tests if t.startswith(WEB)} == {n for n in selector.tests if n.startswith(WEB)}
