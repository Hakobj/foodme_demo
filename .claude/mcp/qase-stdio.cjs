// Launches the Qase MCP server through `agentsecrets env` (which injects QASE_API_TOKEN),
// unless QASE_API_TOKEN is already set (e.g. passed from the "env" block in .mcp.json).
// agentsecrets prints "Injecting N secret: ..." to stdout, which corrupts the MCP
// JSON-RPC stream, so only lines that look like JSON messages are forwarded.
const { spawn } = require('child_process');
const readline = require('readline');

const server = 'npx -y @qase/mcp-server@3.0.6';
const command = process.env.QASE_API_TOKEN ? server : `agentsecrets env -- ${server}`;

const child = spawn(command, {
  shell: true,
  stdio: ['pipe', 'pipe', 'inherit'],
});

process.stdin.pipe(child.stdin);

readline.createInterface({ input: child.stdout }).on('line', (line) => {
  if (line.trimStart().startsWith('{')) {
    process.stdout.write(line + '\n');
  } else if (line.trim()) {
    process.stderr.write(line + '\n');
  }
});

child.on('exit', (code) => process.exit(code ?? 1));
process.on('SIGTERM', () => child.kill());
process.on('SIGINT', () => child.kill());
