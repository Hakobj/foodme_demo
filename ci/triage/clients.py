"""Minimal HTTP clients: GlitchTip (Sentry-compatible API), Jira Cloud REST v3, Telegram Bot API."""

from __future__ import annotations

import re
from typing import Any

import requests

from ci.triage.config import Settings

TIMEOUT = 30


class GlitchTip:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.base = settings.glitchtip_url.rstrip("/") + "/api/0"
        self.org = settings.glitchtip_org
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {settings.glitchtip_token}"

    def unresolved_issues(self, max_pages: int = 5) -> list[dict[str, Any]]:
        """All unresolved issues of the organisation (newest first), following the Link cursor."""
        url: str | None = f"{self.base}/organizations/{self.org}/issues/"
        params: dict[str, Any] | None = {"query": "is:unresolved", "limit": 100, "sort": "date"}
        issues: list[dict[str, Any]] = []
        for _ in range(max_pages):
            if url is None:
                break
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            issues.extend(response.json())
            url, params = _next_link(response.headers.get("Link", "")), None
        return issues

    def latest_event(self, issue_id: str) -> dict[str, Any]:
        response = self.session.get(f"{self.base}/issues/{issue_id}/events/latest/", timeout=TIMEOUT)
        return response.json() if response.ok else {}


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        if 'rel="next"' in part and 'results="true"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


def project_slug(issue: dict[str, Any]) -> str:
    project = issue.get("project")
    if isinstance(project, dict):
        return str(project.get("slug") or project.get("name") or "")
    return str(project or "")


class Jira:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.base = settings.jira_url
        self.project = settings.jira_project
        self.session = session or requests.Session()
        self.session.auth = (settings.jira_email, settings.jira_token)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def check_login(self) -> str:
        response = self.session.get(f"{self.base}/rest/api/3/myself", timeout=TIMEOUT)
        response.raise_for_status()
        return str(response.json().get("displayName", ""))

    def existing_labels(self, labels: list[str]) -> dict[str, str]:
        """label -> issue key, for the labels that some issue in the project already has."""
        if not labels:
            return {}
        quoted = ", ".join(f'"{label}"' for label in labels)
        body = {
            "jql": f"project = {self.project} AND labels in ({quoted})",
            "fields": ["labels"],
            "maxResults": 100,
        }
        response = self.session.post(f"{self.base}/rest/api/3/search/jql", json=body, timeout=TIMEOUT)
        response.raise_for_status()
        found: dict[str, str] = {}
        for issue in response.json().get("issues", []):
            for label in issue.get("fields", {}).get("labels", []):
                if label in labels:
                    found[label] = issue["key"]
        return found

    def create_issue(self, summary: str, description_md: str, labels: list[str], priority: str) -> str:
        fields: dict[str, Any] = {
            "project": {"key": self.project},
            "issuetype": {"name": "Task"},  # SCRUM has no Bug type: bugs are Tasks labelled `bug`
            "summary": summary[:250],
            "description": markdown_to_adf(description_md),
            "labels": labels,
        }
        if priority:
            fields["priority"] = {"name": priority}
        response = self.session.post(f"{self.base}/rest/api/3/issue", json={"fields": fields}, timeout=TIMEOUT)
        if response.status_code == 400 and "priority" in response.text:
            fields.pop("priority")  # some team-managed projects hide the priority field
            response = self.session.post(f"{self.base}/rest/api/3/issue", json={"fields": fields}, timeout=TIMEOUT)
        response.raise_for_status()
        return str(response.json()["key"])

    def browse_url(self, key: str) -> str:
        return f"{self.base}/browse/{key}"


class Telegram:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.token = settings.telegram_token
        self.chat = settings.telegram_chat
        self.session = session or requests.Session()

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat)

    def send(self, html: str) -> None:
        response = self.session.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.chat, "text": html[:4000], "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
        response.raise_for_status()


# ---- markdown -> Atlassian Document Format (headings, paragraphs, bullets, code, bold) ----------


def _inline(text: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for index, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        for code_index, chunk in enumerate(re.split(r"`([^`]+)`", part)):
            if not chunk:
                continue
            node: dict[str, Any] = {"type": "text", "text": chunk}
            marks = ([{"type": "strong"}] if index % 2 else []) + ([{"type": "code"}] if code_index % 2 else [])
            if marks:
                node["marks"] = marks
            nodes.append(node)
    return nodes or [{"type": "text", "text": " "}]


def markdown_to_adf(markdown: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    bullets: list[dict[str, Any]] = []
    code: list[str] | None = None

    def flush_bullets() -> None:
        if bullets:
            content.append({"type": "bulletList", "content": list(bullets)})
            bullets.clear()

    for line in markdown.splitlines():
        if line.startswith("```"):
            if code is None:
                flush_bullets()
                code = []
            else:
                content.append({"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(code) or " "}]})
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", line)
        bullet = re.match(r"^\s*[-*]\s+(.*)", line)
        if heading:
            flush_bullets()
            level = len(heading.group(1))
            content.append({"type": "heading", "attrs": {"level": level}, "content": _inline(heading.group(2))})
        elif bullet:
            paragraph = {"type": "paragraph", "content": _inline(bullet.group(1))}
            bullets.append({"type": "listItem", "content": [paragraph]})
        elif line.strip():
            flush_bullets()
            content.append({"type": "paragraph", "content": _inline(line.strip())})
        else:
            flush_bullets()
    flush_bullets()
    if code is not None:
        content.append({"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(code) or " "}]})
    return {"type": "doc", "version": 1, "content": content}
