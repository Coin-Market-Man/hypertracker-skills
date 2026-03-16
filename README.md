# HyperTracker AI Skills

AI coding assistant skill files for the [HyperTracker API](https://app.coinmarketman.com/hypertracker/api-dashboard). Drop these into your IDE and start building with cohort analytics, order flow, liquidation risk, and leaderboard data from Hyperliquid.

## Quick Install

### Node / npm

```bash
# Claude Code
npx @coinmarketman/hypertracker-skills --claude

# Cursor
npx @coinmarketman/hypertracker-skills --cursor

# GitHub Copilot
npx @coinmarketman/hypertracker-skills --copilot

# OpenAI Codex / Agents
npx @coinmarketman/hypertracker-skills --agents
```

### Everyone else (Python, Ruby, no Node, etc.) — curl

```bash
# Claude Code
curl -fsSL https://raw.githubusercontent.com/Coin-Market-Man/hypertracker-skills/main/SKILL.md \
  --create-dirs -o ~/.claude/skills/hypertracker-skills/SKILL.md

# Cursor
curl -fsSL https://raw.githubusercontent.com/Coin-Market-Man/hypertracker-skills/main/.cursorrules \
  -o .cursorrules

# GitHub Copilot
curl -fsSL https://raw.githubusercontent.com/Coin-Market-Man/hypertracker-skills/main/copilot-instructions.md \
  --create-dirs -o .github/copilot-instructions.md

# OpenAI Codex / Agents
curl -fsSL https://raw.githubusercontent.com/Coin-Market-Man/hypertracker-skills/main/AGENTS.md \
  -o AGENTS.md
```

### ChatGPT / Gemini / DeepSeek / Qwen — manual
Paste contents of `hypertracker-skill-generic.md` into your system prompt or custom instructions.

## What's Inside

Each file contains the same complete reference:

- Authentication and base URL
- All 24 endpoints with parameters
- 16 behavioral cohort definitions (8 PnL + 8 size)
- Historical data availability constraints
- Response examples for key endpoints
- Code patterns in Python and JavaScript
- 18 ready-to-use prompts (vibe coder, dashboards, signals, backtesting, market regime)
- Rate limits and troubleshooting

## Links

- [Get your API key](https://app.coinmarketman.com/hypertracker/api-dashboard)
- [API Docs](https://docs.coinmarketman.com)



---

— The HyperTracker Team
A Coin Market Manager product

© Coin Market Manager. Licensed under CC BY 4.0.
