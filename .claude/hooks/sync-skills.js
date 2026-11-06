// PostToolUse (Edit|MultiEdit|Write): keep .claude/skills/ and .agents/skills/ identical
// by copying the edited skill file to the other folder.
const fs = require("fs");
const path = require("path");
const { run, projectDir, relativeFile, respond } = require("./lib");

run((input) => {
  const rel = relativeFile(input);
  const match = rel && rel.match(/^\.(claude|agents)\/skills\/(.+)$/);
  if (!match) return;

  const [, from, inner] = match;
  const to = from === "claude" ? "agents" : "claude";
  const root = projectDir(input);
  const target = path.join(root, `.${to}`, "skills", inner);

  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(path.join(root, rel), target);
  respond({ systemMessage: `Synced ${rel} -> .${to}/skills/${inner}` });
});
