"""Shared helpers for the project's Python Claude Code hooks."""
import json
import os
import sys
from pathlib import Path


def read_input() -> dict:
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except (ValueError, OSError):
        return {}


def project_dir(payload: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()).resolve()


def relative_file(payload: dict) -> str | None:
    """Edited file relative to the project with forward slashes, or None if outside it."""
    ti = payload.get("tool_input") or {}
    file = ti.get("file_path") or ti.get("notebook_path")
    if not file:
        return None
    try:
        return Path(file).resolve().relative_to(project_dir(payload)).as_posix()
    except ValueError:
        return None


def respond(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj))
    sys.exit(0)
