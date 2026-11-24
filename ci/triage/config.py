"""Settings of the daily triage. Secrets come from the environment (GitHub Actions secrets)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# GlitchTip project slug -> the area name used in reports and Jira labels.
PROJECTS = {"backend": "BE", "web": "FE", "admin": "ADM"}

# Deliberate noise in this course project (CLAUDE.md): the "flaky heartbeat" fake errors and the
# /api/debug/boom endpoint. Matching issues are skipped, never triaged.
IGNORE_TITLES = [
    re.compile(r"Simulated failure during", re.I),
    re.compile(r"flaky heartbeat", re.I),
    re.compile(r"FlakyHeartbeat", re.I),
]
IGNORE_CULPRITS = [re.compile(r"FlakyHeartbeatJob"), re.compile(r"/api/debug/boom")]

RUNS_DIR = "agentic-workflows/triage/runs"
SUT = "https://foodme-hakobjulfayan.onrender.com/"


@dataclass
class Settings:
    glitchtip_url: str = field(
        default_factory=lambda: os.environ.get("GLITCHTIP_BASE_URL", "https://app.glitchtip.com")
    )
    glitchtip_org: str = field(default_factory=lambda: os.environ.get("GLITCHTIP_ORGANIZATION", "foodme"))
    glitchtip_token: str = field(default_factory=lambda: os.environ.get("GLITCHTIP_TOKEN", ""))
    jira_url: str = field(
        default_factory=lambda: os.environ.get("JIRA_BASE_URL", "https://julfayanhakob91.atlassian.net").rstrip("/")
    )
    jira_email: str = field(default_factory=lambda: os.environ.get("JIRA_EMAIL", "").strip())
    jira_token: str = field(default_factory=lambda: os.environ.get("JIRA_API_TOKEN", "").strip())
    jira_project: str = field(default_factory=lambda: os.environ.get("JIRA_PROJECT", "SCRUM"))
    telegram_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())
    telegram_chat: str = field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", "").strip())
    lookback_hours: float = field(default_factory=lambda: float(os.environ.get("TRIAGE_LOOKBACK_HOURS", "26")))
    max_issues: int = field(default_factory=lambda: int(os.environ.get("TRIAGE_MAX_ISSUES", "5")))
    run_url: str = field(default_factory=lambda: _run_url())  # noqa: PLW0108 (defined below)


def _run_url() -> str:
    """Link to the current GitHub Actions run (empty outside Actions)."""
    server, repo, run = (os.environ.get(k, "") for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    return f"{server}/{repo}/actions/runs/{run}" if server and repo and run else ""


def run_key(short_id: str) -> str:
    """Run-dir name for a GlitchTip issue: `BACKEND-7` -> `GT-BACKEND-7`."""
    return f"GT-{re.sub(r'[^A-Za-z0-9-]', '-', short_id).upper()}"


def jira_label(issue_id: str) -> str:
    return f"glitchtip-{issue_id}"
