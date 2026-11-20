// Launches sooperset/mcp-atlassian (https://github.com/sooperset/mcp-atlassian) in Docker
// through `agentsecrets env` (which injects JIRA_API_TOKEN), unless JIRA_API_TOKEN is already set.
// JIRA_URL / JIRA_USERNAME are not secret and come from the "env" block in .mcp.json.
// agentsecrets prints "Injecting N secret: ..." to stdout, which corrupts the MCP
// JSON-RPC stream, so only lines that look like JSON messages are forwarded.
const { spawn } = require('child_process');
const readline = require('readline');

const IMAGE = 'ghcr.io/sooperset/mcp-atlassian:0.24.1';
const passEnv = ['JIRA_URL', 'JIRA_USERNAME', 'JIRA_API_TOKEN', 'JIRA_PROJECTS_FILTER']
  .map((name) => `-e ${name}`)
  .join(' ');

// If JIRA_API_TOKEN is already in the environment (e.g. a Windows user env var), skip AgentSecrets.
const docker = `docker run -i --rm ${passEnv} ${IMAGE}`;
const command = process.env.JIRA_API_TOKEN ? docker : `agentsecrets env -- ${docker}`;

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
