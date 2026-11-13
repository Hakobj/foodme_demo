"""PreToolUse (Bash|PowerShell): stop dangerous shell commands.

  deny -> never runs (push to main/master, force push, history/DB destruction, pipe-to-shell...)
  ask  -> the user must confirm (discarding local work, deleting branches...)

Recursive deletes (rm -rf, Remove-Item -Recurse) are handled by block-recursive-delete.js.
"""
import re
import subprocess

from hooklib import project_dir, read_input, respond

PROTECTED = re.compile(r"^(main|master)$")

DENY = [
    (r"\bgit\s+(\S+\s+)*commit\b.*--no-verify|\bgit\s+push\b.*--no-verify", "skipping git hooks (--no-verify)"),
    (r"\bgit\s+branch\s+(-D|-d|--delete)\b.*\b(main|master)\b", "deleting the main/master branch"),
    (r"(?i)\b(drop|truncate)\s+(database|schema|table)\b", "dropping/truncating database objects"),
    (r"\bflyway\b.*\bclean\b|\bflywayClean\b", "wiping the database with Flyway clean"),
    (r"(?i)\b(curl|wget|iwr|Invoke-WebRequest)\b[^|]*\|\s*(sudo\s+)?(sh|bash|zsh|iex|Invoke-Expression)\b",
     "piping a download straight into a shell"),
    (r"(?i)\bmkfs(\.\w+)?\b|\bformat(-volume)?\s+[a-z]:", "formatting a disk"),
    (r"\bdd\s+.*\bof=/dev/", "writing raw to a device"),
    (r"(?i)\b(shutdown|reboot|Stop-Computer|Restart-Computer)\b", "shutting down / rebooting the machine"),
    (r"\bchmod\s+(-R\s+)?777\b", "making files world-writable"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "fork bomb"),
    (r"\bgit\s+config\s+(--global\s+)?(user\.|core\.hooksPath)", "changing git identity/hooks config"),
]

ASK = [
    (r"\bgit\s+reset\s+.*--hard\b", "git reset --hard discards uncommitted work"),
    (r"\bgit\s+clean\s+.*-[a-zA-Z]*f", "git clean -f deletes untracked files"),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "discards all local changes"),
    (r"\bgit\s+branch\s+-D\b", "force-deletes a branch"),
    (r"\bgit\s+stash\s+(drop|clear)\b", "deletes stashed work"),
    (r"\bgit\s+(rebase|filter-branch|filter-repo)\b", "rewrites git history"),
    (r"\bdocker\s+(system\s+prune|volume\s+(rm|prune))\b", "deletes Docker data (e.g. the Postgres volume)"),
]


def current_branch(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def check_push(words: list[str], cwd: str) -> list[str]:
    """Problems with a single `git push ...` segment (words start at 'git')."""
    args = words[words.index("push") + 1:]
    flags = [a for a in args if a.startswith("-")]
    refspecs = [a for a in args if not a.startswith("-")][1:]  # first positional is the remote
    reasons = []

    if any(re.match(r"^(--force|--force-with-lease.*|-f|-[a-zA-Z]*f[a-zA-Z]*)$", f) for f in flags) \
            or any(r.startswith("+") for r in refspecs):
        reasons.append("force push")
    if any(f in ("--delete", "-d") for f in flags) or any(r.startswith(":") for r in refspecs):
        reasons.append("deleting a remote branch")
    if "--mirror" in flags or "--all" in flags:
        reasons.append("pushing all refs")

    def dest(ref: str) -> str:
        return re.sub(r"^refs/heads/", "", ref.lstrip("+").split(":")[-1])

    branch = current_branch(cwd)
    if any(PROTECTED.match(dest(r)) for r in refspecs):
        reasons.append("pushing to main/master (open a PR from a feature branch instead)")
    elif (not refspecs or "HEAD" in refspecs) and PROTECTED.match(branch):
        reasons.append(f"pushing to the protected branch '{branch}' (open a PR from a feature branch instead)")
    return reasons


def decide(decision: str, reason: str) -> None:
    respond({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }})


def main() -> None:
    payload = read_input()
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return
    cwd = payload.get("cwd") or str(project_dir(payload))

    deny: list[str] = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        words = segment.split()
        if "git" in words:
            g = words.index("git")
            if g + 1 < len(words) and words[g + 1] == "push":
                deny += check_push(words[g:], cwd)
    deny += [why for pattern, why in DENY if re.search(pattern, command)]

    if deny:
        reasons = "; ".join(dict.fromkeys(deny))
        decide("deny", f"Blocked by .claude/hooks/block_dangerous_commands.py: {reasons}. "
                       "Ask the user to run it themselves if it is really needed.")

    ask = [why for pattern, why in ASK if re.search(pattern, command)]
    if ask:
        decide("ask", f"Potentially destructive: {'; '.join(ask)}.")


if __name__ == "__main__":
    main()
