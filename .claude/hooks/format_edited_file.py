"""PostToolUse (Edit|MultiEdit|Write): auto-format the file Claude just edited.

  apps/web, apps/admin  -> Prettier (app-local install if present, else pinned npx version)
  tests-python/*.py     -> ruff format, else black (skipped if neither is installed)

Formatting failures never block Claude; they are only reported as a system message.
"""
import re
import subprocess
import sys

from hooklib import project_dir, read_input, relative_file, respond

PRETTIER_VERSION = "3.3.3"
WIN = sys.platform == "win32"


def run(cmd: list[str], cwd) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=50, shell=WIN)


def main() -> None:
    payload = read_input()
    rel = relative_file(payload)
    if not rel or re.search(r"(^|/)(node_modules|dist|build)/", rel):
        return
    root = project_dir(payload)

    m = re.match(r"^apps/(web|admin)/(.+\.(?:ts|tsx|js|jsx|mjs|cjs|css|json|html))$", rel)
    if m:
        app_dir = root / "apps" / m[1]
        local = app_dir / "node_modules" / ".bin" / ("prettier.cmd" if WIN else "prettier")
        cmd = [str(local)] if local.exists() else ["npx", "--yes", f"prettier@{PRETTIER_VERSION}"]
        res = run(cmd + ["--write", m[2]], app_dir)
        if res.returncode == 0:
            respond({"systemMessage": f"Formatted {rel} with Prettier"})
        respond({"systemMessage": f"Prettier could not format {rel}: {(res.stderr or res.stdout).strip()[:300]}"})

    if re.match(r"^tests-python/.+\.py$", rel):
        for tool, args in (("ruff", ["format"]), ("black", ["-q"])):
            if run([sys.executable, "-m", tool, "--version"], root).returncode != 0:
                continue
            if run([sys.executable, "-m", tool, *args, rel], root).returncode == 0:
                respond({"systemMessage": f"Formatted {rel} with {tool}"})
            return


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a formatter problem must never break the session
        pass
