"""Daily triage in CI (.github/workflows/triage-daily.yml).

1. `python -m ci.triage.discover`  GlitchTip -> new issues in backend / web / admin, minus the ones
                                   Jira already has (label `glitchtip-<id>`) -> one run dir each
2. Claude Code (headless)          runs /triage-pipeline in CI mode on each run dir
3. `python -m ci.triage.report`    opens the Jira issue with the triage result, posts to Telegram

Deterministic steps hold the credentials and do every write; the agent only reads and analyses.
"""
