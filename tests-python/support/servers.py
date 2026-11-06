"""Starts a Vite dev server when it isn't already running (like Playwright's `webServer` +
`reuseExistingServer` in the TS configs)."""

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]


def is_up(url: str) -> bool:
    try:
        return requests.get(url, timeout=2).status_code < 500
    except requests.RequestException:
        return False


def _spawn(command: str, cwd: Path) -> subprocess.Popen:
    # shell=True so Windows resolves npm.cmd. The child gets its own process group/session so
    # stop() can kill the whole tree (shell -> npm -> vite), not just the shell.
    if sys.platform == "win32":
        return subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        command, cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
    )


def ensure_dev_server(url: str, app: str, port: int, timeout: float = 120) -> subprocess.Popen | None:
    """Returns the started process (caller stops it), or None when the server was already up."""
    if is_up(url):
        return None
    app_dir = REPO_ROOT / "apps" / app
    if not (app_dir / "node_modules").exists():
        raise RuntimeError(f"{url} is not running and apps/{app}/node_modules is missing; run `npm ci` in apps/{app}")
    proc = _spawn(f"npm run dev -- --port {port} --strictPort", app_dir)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_up(url):
            return proc
        if proc.poll() is not None:
            raise RuntimeError(f"dev server for apps/{app} exited with code {proc.returncode}")
        time.sleep(1)
    stop(proc)
    raise RuntimeError(f"dev server for apps/{app} did not start on {url} within {timeout}s")


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if sys.platform == "win32":
        # Best effort: the tree may already be gone.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
