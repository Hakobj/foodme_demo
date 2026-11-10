// Launches the Qase MCP server through `agentsecrets env` (which injects QASE_API_TOKEN).
// agentsecrets prints "Injecting N secret: ..." to stdout, which corrupts the MCP
// JSON-RPC stream, so only lines that look like JSON messages are forwarded.
const { spawn } = require('child_process');
const readline = require('readline');

const child = spawn('agentsecrets env -- npx -y @qase/mcp-server@3.0.6', {
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
