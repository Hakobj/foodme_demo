// Shared helpers for the project's Claude Code hooks.
const path = require("path");

// Reads the hook payload from stdin asynchronously (sync reads of a pipe can hit EAGAIN on Windows)
// and calls main(input).
function run(main) {
  let data = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (data += chunk));
  process.stdin.on("end", () => {
    let input = {};
    try {
      input = JSON.parse(data || "{}");
    } catch {}
    main(input);
  });
}

function projectDir(input) {
  return path.resolve(process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd());
}

// Path of the edited file relative to the project, with forward slashes, or null if outside it.
function relativeFile(input) {
  const file = input.tool_input && (input.tool_input.file_path || input.tool_input.notebook_path);
  if (!file) return null;
  const rel = path.relative(projectDir(input), path.resolve(file)).split(path.sep).join("/");
  return rel.startsWith("..") || path.isAbsolute(rel) ? null : rel;
}

function respond(obj) {
  process.stdout.write(JSON.stringify(obj));
  process.exit(0);
}

module.exports = { run, projectDir, relativeFile, respond };
