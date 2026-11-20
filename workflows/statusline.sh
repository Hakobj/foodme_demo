#!/usr/bin/env bash
# Claude Code status line: shows the step of an agent-driven pipeline run, but only
# in a session where /feature-testing-pipeline or /triage-pipeline was triggered.
# Other sessions get an empty line. The pipeline skill writes the line to
# runs/<T>/status; this only prints it.
input=$(cat) # session JSON from Claude Code; we need transcript_path

transcript=$(printf '%s' "$input" | grep -o '"transcript_path" *: *"[^"]*"' | head -n 1 | sed 's/.*: *"//; s/"$//')
[ -f "$transcript" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$PWD}/agentic-workflows"

# Triggered by the slash command (user message) or by the Skill tool (assistant tool_use).
# The patterns use unescaped quotes, so text that merely mentions them inside a tool
# result (JSON-escaped there) doesn't count. The pipeline triggered last wins.
last_skill="" last_line=0
for skill in feature-testing-pipeline triage-pipeline; do
  slash="\"content\":\"<command-message>${skill}</command-message>"
  tool="\"name\":\"Skill\",\"input\":{\"skill\":\"${skill}\""
  line=$(grep -nF -e "$slash" -e "$tool" "$transcript" | tail -n 1 | cut -d: -f1)
  if [ -n "$line" ] && [ "$line" -gt "$last_line" ]; then
    last_skill=$skill last_line=$line
  fi
done
[ -n "$last_skill" ] || exit 0

case "$last_skill" in
  feature-testing-pipeline) runs="$root/functional-testing/runs" label="Feature Testing" ;;
  triage-pipeline)          runs="$root/triage/runs"             label="Triage" ;;
esac
slash="\"content\":\"<command-message>${last_skill}</command-message>"

# Prefer the ticket passed to the last slash command in this session.
ticket=$(grep -oE "${slash}[^<]*<command-name>[^<]*</command-name>[^<]*<command-args>[^<]*</command-args>" "$transcript" \
  | tail -n 1 | sed 's/.*<command-args>//; s/<\/command-args>.*//; s/^ *//; s/ *$//')

if [ -n "$ticket" ] && [ -f "$runs/$ticket/status" ]; then
  status="$runs/$ticket/status"
else
  status=$(ls -t "$runs"/*/status 2>/dev/null | head -n 1)
fi

if [ -n "$status" ]; then
  head -n 1 "$status"
else
  echo "$label ${ticket:-} │ starting"
fi
