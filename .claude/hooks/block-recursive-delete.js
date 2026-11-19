// PreToolUse (Bash|PowerShell): deny recursive force-deletes in any spelling,
// including inside chained commands (`cd x && rm -r -f y`).
const { run, respond } = require("./lib");

run((input) => {
  const command = (input.tool_input && input.tool_input.command) || "";

  function isRecursiveForceRm(segment) {
    const words = segment.trim().split(/\s+/);
    const i = words.findIndex((w) => /^(\/usr)?(\/bin\/)?rm$/.test(w));
    if (i === -1) return false;
    let recursive = false;
    let force = false;
    for (const w of words.slice(i + 1)) {
      if (w === "--") break;
      if (w === "--recursive") recursive = true;
      else if (w === "--force") force = true;
      else if (/^-[a-zA-Z]+$/.test(w)) {
        if (/[rR]/.test(w)) recursive = true;
        if (/f/.test(w)) force = true;
      }
    }
    return recursive && force;
  }

  const segments = command.split(/&&|\|\||;|\||\n|\$\(|`/);
  const reasons = [];
  if (segments.some(isRecursiveForceRm)) reasons.push("rm with recursive + force flags");
  if (/\b(Remove-Item|rm|ri|del|erase|rd|rmdir)\b[^;|\n]*\s-Recurse\b/i.test(command)) reasons.push("PowerShell Remove-Item -Recurse");
  if (/\b(rd|rmdir)\b[^;|\n&]*\s\/s\b/i.test(command)) reasons.push("cmd rd /s");
  if (/\bfind\b[^;|\n]*\s-delete\b/.test(command)) reasons.push("find -delete");

  if (reasons.length) {
    respond({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason:
          `Blocked by .claude/hooks/block-recursive-delete.js (${reasons.join(", ")}). ` +
          "Recursive deletes are not allowed in this project. Delete specific files instead, or ask the user to run it.",
      },
    });
  }
});
