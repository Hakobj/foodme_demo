"""Daily triage CI scripts (ci/triage): new-issue filter, run-dir files, Jira payloads, Telegram digest.
No network: HTTP goes to a fake session."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci.triage import discover, report
from ci.triage.clients import GlitchTip, Jira, _next_link, markdown_to_adf
from ci.triage.config import Settings, run_key
from ci.triage.yamlish import dump_yaml

NOW = datetime.now(timezone.utc)


def iso(delta_hours: float) -> str:
    return (NOW - timedelta(hours=delta_hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def gt_issue(issue_id: str, project: str = "backend", hours_ago: float = 2, title: str = "NullPointerException: x"):
    return {
        "id": issue_id,
        "shortId": f"{project.upper()}-{issue_id}",
        "project": project,
        "title": title,
        "culprit": "POST /api/order",
        "count": "3",
        "firstSeen": iso(hours_ago),
        "lastSeen": iso(0.5),
        "metadata": {},
    }


class FakeResponse:
    def __init__(self, payload, status=200, headers=None):
        self.payload, self.status_code, self.headers = payload, status, headers or {}
        self.ok, self.text = status < 400, json.dumps(payload)

    def json(self):
        return self.payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls, self.headers, self.auth = list(responses), [], {}, None

    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        return self._next("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._next("POST", url, **kwargs)


# ---- discovery ------------------------------------------------------------------------------


def test_new_issues_keeps_recent_issues_of_our_projects_and_drops_noise():
    issues = [
        gt_issue("1"),
        gt_issue("2", project="web"),
        gt_issue("3", hours_ago=60),  # too old
        gt_issue("4", project="other"),  # not BE / FE / ADM
        gt_issue("5", title="IllegalStateException: Simulated failure during menu search reindex"),
        {**gt_issue("6"), "project": {"slug": "admin"}},  # project as an object
    ]
    fresh, noise = discover.new_issues(issues, NOW - timedelta(hours=26))
    assert [i["id"] for i in fresh] == ["1", "2", "6"]
    assert [i["id"] for i in noise] == ["5"]


def test_glitchtip_follows_the_link_cursor():
    page2 = '<https://gt/api/0/organizations/foodme/issues/?cursor=2>; rel="next"; results="true"'
    session = FakeSession([FakeResponse([gt_issue("1")], headers={"Link": page2}), FakeResponse([gt_issue("2")])])
    settings = Settings(glitchtip_url="https://gt", glitchtip_org="foodme", glitchtip_token="t")
    issues = GlitchTip(settings, session).unresolved_issues()  # type: ignore[arg-type]
    assert [i["id"] for i in issues] == ["1", "2"]
    assert session.calls[0][1] == "https://gt/api/0/organizations/foodme/issues/"
    assert session.headers["Authorization"] == "Bearer t"


def test_next_link_stops_when_there_are_no_more_results():
    assert _next_link('<https://x?cursor=1>; rel="next"; results="false"') is None


def test_jira_dedup_query_uses_the_glitchtip_labels():
    session = FakeSession(
        [FakeResponse({"issues": [{"key": "SCRUM-9", "fields": {"labels": ["glitchtip-1", "bug"]}}]})]
    )
    jira = Jira(Settings(jira_url="https://j", jira_project="SCRUM"), session)  # type: ignore[arg-type]
    assert jira.existing_labels(["glitchtip-1", "glitchtip-2"]) == {"glitchtip-1": "SCRUM-9"}
    body = session.calls[0][2]["json"]
    assert body["jql"] == 'project = SCRUM AND labels in ("glitchtip-1", "glitchtip-2")'


def test_event_digest_keeps_request_and_in_app_frames_only():
    event = {
        "eventID": "e1",
        "entries": [
            {"type": "request", "data": {"method": "POST", "url": "https://x/api/order", "headers": [["Cookie", "s"]]}},
            {
                "type": "exception",
                "data": {"values": [{"stacktrace": {"frames": [
                    {"filename": "lib.java", "function": "f", "inApp": False},
                    {"filename": "OrderService.java", "function": "place", "lineNo": 42, "inApp": True},
                ]}}]},
            },
        ],
        "tags": [{"key": "release", "value": "abc"}, {"key": "user.email", "value": "a@b.c"}],
    }  # fmt: skip
    digest = discover.event_digest(event)
    assert digest["request"] == {"method": "POST", "url": "https://x/api/order"}
    assert digest["in_app_frames"] == [{"filename": "OrderService.java", "function": "place", "lineNo": 42}]
    assert digest["tags"] == {"release": "abc"}
    assert "Cookie" not in json.dumps(digest)


def test_write_run_creates_problem_gate_and_artifact(tmp_path: Path):
    issue = gt_issue("7")
    key = discover.write_run(tmp_path, issue, {"request": {"method": "POST", "url": "https://x/api/order"}})
    run = tmp_path / key
    assert key == "GT-BACKEND-7"
    problem = (run / "problem.yaml").read_text(encoding="utf-8")
    assert 'mode: "ci"' in problem
    assert '- "Trigger: POST https://x/api/order"' in problem
    assert "approved: true" in (run / "gates.yaml").read_text(encoding="utf-8")
    artifact = (run / "artifacts" / "00-glitchtip-issue.json").read_text(encoding="utf-8")
    assert artifact.startswith("// GlitchTip issue 7")


def test_run_key_is_filesystem_safe():
    assert run_key("web-3a/x") == "GT-WEB-3A-X"


def test_dump_yaml_nests_and_quotes():
    text = dump_yaml({"a": "x: y", "b": [1, {"c": True}], "d": {}, "e": None})
    assert text == 'a: "x: y"\nb:\n  - 1\n  - c: true\nd: {}\ne: null\n'


# ---- report ----------------------------------------------------------------------------------


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "GT-WEB-3"
    (run / "artifacts").mkdir(parents=True)
    artifact = {"issue": {**gt_issue("3", project="web"), "permalink": "https://gt/i/3"}, "latest_event": {}}
    (run / "artifacts" / "00-glitchtip-issue.json").write_text("// header\n" + json.dumps(artifact), encoding="utf-8")
    return run


def write_result(run: Path, **overrides):
    result = {
        "status": "done",
        "reproduced": True,
        "top": {"id": "H-1", "title": "Cart total ignores additions", "layer": "web", "rating": "likely",
                "confidence": 70, "root_cause": "x"},
        "jira": {"summary": "Checkout: total wrong", "description_md": "## Triage\nBody", "priority": "High",
                 "labels": ["checkout"]},
        "telegram": "Short summary",
    }  # fmt: skip
    result.update(overrides)
    (run / "ci-result.json").write_text(json.dumps(result), encoding="utf-8")


def test_issue_fields_from_a_complete_triage(run_dir: Path):
    write_result(run_dir)
    fields = report.build_issue(run_dir, Settings(run_url="https://gh/run/1"))
    assert fields["summary"] == "[Bug] Checkout: total wrong"
    assert fields["priority"] == "High"
    assert fields["triaged"] is True
    assert {"auto-triage", "needs-review", "glitchtip-3", "area-fe", "rc-web", "triaged", "checkout"} <= set(
        fields["labels"]
    )
    assert "https://gh/run/1" in fields["description_md"]
    assert "https://gt/i/3" in fields["description_md"]


def test_missing_or_broken_result_still_files_the_issue_from_glitchtip(run_dir: Path):
    fields = report.build_issue(run_dir, Settings())
    assert fields["triaged"] is False
    assert "triage-incomplete" in fields["labels"]
    assert fields["summary"] == "[Bug] FE: NullPointerException: x"
    assert "Automated triage did not complete" in fields["description_md"]

    write_result(run_dir, top={"rating": "certain"})
    assert report.build_issue(run_dir, Settings())["problems"]


def test_unlikely_top_candidate_gets_no_root_cause_label(run_dir: Path):
    write_result(run_dir, top={"title": "t", "layer": "backend", "rating": "possible", "confidence": 30})
    assert not any(label.startswith("rc-") for label in report.build_issue(run_dir, Settings())["labels"])


def test_digest_lists_each_issue_with_its_jira_link_and_escapes_html():
    discover_summary = {
        "since": "2026-11-23T06:00:00Z",
        "queued": [
            {"key": "GT-WEB-3", "project": "web", "title": "TypeError: <b>x</b>", "triage": True},
            {"key": "GT-BACKEND-9", "project": "backend", "title": "Boom", "triage": False},
        ],
        "noise_skipped": ["BACKEND-1: Simulated failure"],
        "already_in_jira": {},
    }
    reports: list[dict] = [
        {"run": "GT-WEB-3", "jira_key": "SCRUM-20", "jira_url": "https://j/browse/SCRUM-20",
         "top": {"title": "H", "rating": "likely", "confidence": 70, "layer": "web"}, "telegram": "why"},
        {"run": "GT-BACKEND-9", "jira_key": "SCRUM-21", "jira_url": "https://j/browse/SCRUM-21", "top": None},
    ]  # fmt: skip
    text = report.digest_text(discover_summary, reports, "https://gh/run/1")
    assert '<a href="https://j/browse/SCRUM-20">SCRUM-20</a>' in text
    assert "TypeError: &lt;b&gt;x&lt;/b&gt;" in text
    assert "🟢 H (likely, 70%, layer web)" in text
    assert "over the daily triage limit" in text
    assert "1 known-noise" in text


def test_digest_says_when_nothing_is_new():
    assert "No new issues" in report.digest_text({"since": "x", "queued": []}, [], "")


def test_markdown_to_adf_builds_headings_lists_and_marks():
    doc = markdown_to_adf("## Title\n- **Root cause:** `Order.java`\n\nPlain")
    assert [n["type"] for n in doc["content"]] == ["heading", "bulletList", "paragraph"]
    item = doc["content"][1]["content"][0]["content"][0]["content"]
    assert item[0] == {"type": "text", "text": "Root cause:", "marks": [{"type": "strong"}]}
    assert item[-1] == {"type": "text", "text": "Order.java", "marks": [{"type": "code"}]}
