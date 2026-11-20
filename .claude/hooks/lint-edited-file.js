// PostToolUse (Edit|MultiEdit|Write): lint the edited frontend file and feed errors back to Claude.
// apps/web uses oxlint, apps/admin uses eslint. Skips silently when the app's node_modules aren't installed.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { run, projectDir, relativeFile, respond } = require("./lib");

run((input) => {
  const rel = relativeFile(input);
  const match = rel && rel.match(/^apps\/(web|admin)\/(.+\.(?:ts|tsx|js|jsx|mjs))$/);
  if (!match) return;

  const [, app, fileInApp] = match;
  const appDir = path.join(projectDir(input), "apps", app);
  const linter = app === "web" ? "oxlint" : "eslint";
  const bin = path.join(appDir, "node_modules", ".bin", process.platform === "win32" ? `${linter}.cmd` : linter);
  if (!fs.existsSync(bin)) return;

  const result = spawnSync(bin, [fileInApp], { cwd: appDir, encoding: "utf8", shell: process.platform === "win32", timeout: 50000 });
  if (result.status !== 0 && result.status !== null) {
    const output = `${result.stdout || ""}${result.stderr || ""}`.trim().slice(-4000);
    respond({
      decision: "block",
      reason: `${linter} reported problems in ${rel}:\n${output}\nFix them before continuing.`,
    });
  }
});
