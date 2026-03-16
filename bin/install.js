#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const pkg = path.join(__dirname, '..');
const flag = process.argv[2];

function copy(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`Installed → ${dest}`);
}

switch (flag) {
  case '--claude':
    copy(
      path.join(pkg, 'SKILL.md'),
      path.join(require('os').homedir(), '.claude', 'skills', 'hypertracker-skills', 'SKILL.md')
    );
    break;
  case '--cursor':
    copy(path.join(pkg, '.cursorrules'), path.join(process.cwd(), '.cursorrules'));
    break;
  case '--copilot':
    copy(
      path.join(pkg, '.github', 'copilot-instructions.md'),
      path.join(process.cwd(), '.github', 'copilot-instructions.md')
    );
    break;
  case '--agents':
    copy(path.join(pkg, 'AGENTS.md'), path.join(process.cwd(), 'AGENTS.md'));
    break;
  case '--generic':
    copy(
      path.join(pkg, 'hypertracker-skill-generic.md'),
      path.join(process.cwd(), 'hypertracker-skill-generic.md')
    );
    break;
  default:
    console.log(`Usage: npx @coinmarketman/hypertracker-skills <flag>

Flags:
  --claude    Install to ~/.claude/skills/hypertracker-skills/SKILL.md
  --cursor    Copy .cursorrules to current directory
  --copilot   Copy copilot-instructions.md to .github/ in current directory
  --agents    Copy AGENTS.md to current directory
  --generic   Copy hypertracker-skill-generic.md to current directory
`);
}
