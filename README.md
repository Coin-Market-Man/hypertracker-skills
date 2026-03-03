# HyperTracker AI Skills

AI coding assistant skill files for the [HyperTracker API](https://app.coinmarketman.com/hypertracker/api-dashboard). Drop these into your IDE and start building with cohort analytics, order flow, liquidation risk, and leaderboard data from Hyperliquid.

## Quick Install

### Claude Code
```bash
npx skills add Coin-Market-Man/hypertracker-skills
```

### Cursor
Copy `.cursorrules` to your project root.

### GitHub Copilot
Copy `.github/copilot-instructions.md` to your project's `.github/` directory.

### OpenAI Codex
Copy `AGENTS.md` to your project root.

### ChatGPT / Gemini / DeepSeek / Qwen
Paste the contents of `hypertracker-skill-generic.md` into your system prompt or custom instructions.

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
