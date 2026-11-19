"""Audit log of everything Claude does in this project.

Registered on SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop.
Appends one JSON line per event to .claude/logs/actions-YYYY-MM-DD.jsonl (git-ignored).
File contents are never logged, only paths/commands/patterns (truncated).
"""
import json
from datetime import datetime, timezone

from hooklib import project_dir, read_input

MAX = 500


def cut(value) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s[:MAX] + "..." if len(s) > MAX else s


def summarize(ti: dict) -> str | None:
    if not isinstance(ti, dict):
        return cut(ti)
    if ti.get("command"):
        return cut(ti["command"])
    if ti.get("file_path") or ti.get("notebook_path"):
        return ti.get("file_path") or ti.get("notebook_path")
    if ti.get("pattern"):
        return cut(ti["pattern"] + (f" in {ti['path']}" if ti.get("path") else ""))
    for key in ("url", "query", "skill", "description"):
        if ti.get(key):
            return cut(ti[key])
    return cut(json.dumps(ti))


def main() -> None:
    payload = read_input()
    event = payload.get("hook_event_name", "unknown")
    now = datetime.now(timezone.utc)
    entry = {
        "ts": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "session": (payload.get("session_id") or "")[:8],
        "event": event,
    }

    if payload.get("tool_name"):
        entry["tool"] = payload["tool_name"]
        entry["input"] = summarize(payload.get("tool_input") or {})
        if payload.get("tool_use_id"):
            entry["id"] = payload["tool_use_id"][-8:]
    if event == "PostToolUse":
        entry["ok"] = True
    elif event == "PostToolUseFailure":
        entry["ok"] = False
        entry["error"] = cut(payload.get("error") or json.dumps(payload.get("tool_response")))
    elif event == "UserPromptSubmit":
        entry["prompt"] = cut(payload.get("prompt"))
    elif event == "SessionStart":
        entry["source"] = payload.get("source")

    log_dir = project_dir(payload) / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"actions-{now:%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # logging must never interfere with the session
        pass
