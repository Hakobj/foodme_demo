// PreToolUse (Edit|MultiEdit|Write): ask the user before an edit touches or removes
// a seeded `FM-BUG-NN` / `FM-FLAKE-NN` line (course material, see CLAUDE.md).
const fs = require("fs");
const path = require("path");
const { run, projectDir, relativeFile, respond } = require("./lib");

const MARKER = /FM-(BUG|FLAKE)-\d+/g;
run((input) => {
  const rel = relativeFile(input);
  if (!rel || rel.startsWith(".claude/") || rel.startsWith(".agents/") || /\.md$/i.test(rel)) return;

  const ti = input.tool_input || {};
  const touched = new Set();
  const collect = (text) => (String(text || "").match(MARKER) || []).forEach((m) => touched.add(m));

  if (input.tool_name === "Write") {
    let before = "";
    try {
      before = fs.readFileSync(path.join(projectDir(input), rel), "utf8");
    } catch {
      return; // new file
    }
    const after = String(ti.content || "");
    // Markers whose line changed or disappeared.
    before.split(/\r?\n/).filter((l) => /FM-(BUG|FLAKE)-\d+/.test(l) && !after.includes(l.trim())).forEach(collect);
  } else {
    const edits = ti.edits || [{ old_string: ti.old_string }];
    edits.forEach((e) => collect(e.old_string));
  }

  if (touched.size) {
    respond({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "ask",
        permissionDecisionReason:
          `This edit touches seeded course material (${[...touched].join(", ")}) in ${rel}. ` +
          "Only change it if the task names that bug/flake, and keep the marker with `FIX: <reason>`.",
      },
    });
  }
});
