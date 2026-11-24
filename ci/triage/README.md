# Daily triage in CI

`.github/workflows/triage-daily.yml` runs once a day (06:00 UTC, or on demand). It finds the **new** GlitchTip issues in the three projects, BE (`backend`), FE (`web`) and ADM (`admin`). It triages each one with the existing triage pipeline, opens a Jira issue per GlitchTip issue, and posts one Telegram digest.

```
discover (python)            triage (one job per issue, max 2 in parallel)            digest (python)
GlitchTip ─┐                 ┌─ Claude Code, headless: /triage-pipeline GT-<ID>        ┌─ Telegram: one message
           ├─ new issues ──▶ │   CI mode → triage-worker briefs (Playwright as guest,  │   (issues, Jira links,
Jira ──────┘  (dedup)        │   GlitchTip, Loki, Prometheus, code) → hypotheses       │   top root cause)
                             │   → triage-judge → triage.md + ci-result.json           │
                             └─ report.py: Jira issue (also when the triage failed) ──▶ └─ job summary
```

**Split of duties.** The Python steps hold every credential and do every write (Jira, Telegram). The agent only reads (GlitchTip, Grafana, the live site as a guest, the code) and writes files in its run dir. It has no Jira, Telegram or GitHub write tools in CI (`--strict-mcp-config` with `ci/triage/mcp.ci.json`). A prompt injected through an error message or a log line therefore can't file or change anything.

## What counts as "new"

| Rule | Where |
|---|---|
| Unresolved issue in `backend`, `web` or `admin` | `discover.new_issues` |
| `firstSeen` within the look-back window (default 26 h: a late run doesn't miss a day) | `TRIAGE_LOOKBACK_HOURS` |
| Not deliberate noise: the "flaky heartbeat" fake errors and `/api/debug/boom` (see CLAUDE.md) | `config.IGNORE_TITLES`, `IGNORE_CULPRITS` |
| No Jira issue labelled `glitchtip-<issue id>` yet. Jira is the memory between runs, so there's no state file and a re-run never files twice | `Jira.existing_labels` |

The most frequent issues are triaged first, at most `TRIAGE_MAX_ISSUES` (default 5) per run. The rest are filed in Jira **without** an analysis (label `triage-incomplete`), so no issue is lost.

## Per issue

1. `discover.py` writes `agentic-workflows/triage/runs/GT-<SHORT-ID>/`:
   - `problem.yaml` (`mode: "ci"`) holds the problem as GlitchTip reports it.
   - `gates.yaml` auto-approves the problem gate (`by: ci-daily-triage`).
   - `artifacts/00-glitchtip-issue.json` holds the issue and its latest event. Headers, cookies, user data and body are left out.
2. Claude Code runs `/triage-pipeline GT-<SHORT-ID>` following `ci/triage/prompt.md` and the skill's **CI mode** section (`.claude/skills/triage-pipeline/SKILL.md`). There is no AskUserQuestion. The repro is guest-only: no sign-in, no orders. There is a worker/judge budget, and no root-cause gate, because the human reviews in Jira. It always ends with `ci-result.json`.
3. `report.py issue` validates `ci-result.json` and opens the Jira issue in project SCRUM:
   - Type `Task`, summary `[Bug] …`.
   - Labels `bug foodme auto-triage needs-review glitchtip-<id> area-<be|fe|adm>`, plus `triaged rc-<layer>` when the top candidate is `confirmed`/`likely`.
   - The description is the bug template plus the triage result, a GlitchTip link and the CI run link.

   If the triage failed, timed out or was skipped, the issue is still opened from the GlitchTip data, labelled `triage-incomplete`.
4. The run dir (briefs, findings, artifacts, hypotheses, judge verdicts, `triage.md`) is uploaded as the artifact `triage-GT-<SHORT-ID>` (30 days).

Then `report.py digest` sends **one** Telegram message: each new issue with area, Jira link, top root-cause candidate (rating, confidence, layer) and a two-sentence summary, plus what was skipped and the run link.

## Setup

Repository **secrets**: `CLAUDE_CODE_OAUTH_TOKEN` (already used by the other Claude workflows), `GLITCHTIP_TOKEN` (a GlitchTip API token with read access to the organisation), `JIRA_EMAIL`, `JIRA_API_TOKEN` (already used by `claude-jira-insights.yml`), `TELEGRAM_BOT_TOKEN` (from @BotFather), `TELEGRAM_CHAT_ID` (the chat or channel the bot posts to; add the bot to it first).

Optional repository **variables**: `GLITCHTIP_ORGANIZATION` (default `foodme`), `GLITCHTIP_BASE_URL` (default `https://app.glitchtip.com`), `GRAFANA_MCP_URL`, `JIRA_BASE_URL`.

First run: **Actions → Daily triage → Run workflow** with `dry_run: true`. It discovers and triages, prints the Jira payloads and the Telegram text, and writes nothing.

## Local

```bash
pytest tests-python/unit/test_triage_ci.py                     # the scripts, no network
GLITCHTIP_TOKEN=… JIRA_EMAIL=… JIRA_API_TOKEN=… python -m ci.triage.discover --dry-run
python -m ci.triage.report issue --run-dir agentic-workflows/triage/runs/GT-WEB-8 --dry-run
python -m ci.triage.report digest --discover discover.json --reports-dir agentic-workflows/triage/runs --dry-run
```

Interactive triage of the same run dir works too: `/triage-pipeline GT-WEB-8` in a local session continues from where CI stopped.

## Limits

- The live SUT is on Render's free tier: the first request can take about 30 s, and Loki/Prometheus keep at most 48 h of data. An issue first seen two days ago may have no logs left. The run records that as an obstacle.
- Guest-only repro: issues that need a signed-in customer or the admin are analysed from GlitchTip, logs and code, and rarely rated above `possible`.
- The GlitchTip API is Sentry-compatible. The client uses the same two endpoints as `mcp-glitchtip`: `organizations/<org>/issues/` and `issues/<id>/events/latest/`.
