# HyperTracker AI Skills

AI coding assistant skill files for the [HyperTracker API](https://app.coinmarketman.com/hypertracker/api-dashboard). Drop these into your IDE and start building with cohort analytics, order flow, liquidation risk, and leaderboard data from Hyperliquid.

## Quick Install

### Node / npm

```bash
# Claude Code
npx skills add Coin-Market-Man/hypertracker-skills

# Cursor
npx @coinmarketman/hypertracker-skills --cursor

# GitHub Copilot
npx @coinmarketman/hypertracker-skills --copilot

# OpenAI Codex / Agents
npx @coinmarketman/hypertracker-skills --agents
```

### No Node/npm? Use curl

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

### ChatGPT / Gemini / DeepSeek / Qwen (manual)
Paste contents of `hypertracker-skill-generic.md` into your system prompt or custom instructions.

## What's Inside

Each file contains the same complete reference:

- Authentication, base URL and the critical rules that prevent silent empty results
- Every REST endpoint with parameters, defaults, limits and response shapes (cohorts, positions, heatmap, order flow, liquidations, leaderboards, wallets, fills, fundings, closed trades, builders, exports, Hyperliquid info proxy)
- Real-time infrastructure: WebSocket streams, server-side alerts (Events API), state webhooks, enterprise options and planned node peering
- 16 behavioral cohort definitions (8 PnL + 8 size)
- Data freshness and historical availability
- Response examples for key endpoints
- Code patterns in Python, JavaScript and shell (pagination, downloads, rate limits, WebSocket, alert setup, webhook signature verification)
- Ready-to-use prompts and end-to-end recipes (vibe coder, dashboards, signals, liquidations, wallet discovery, reverse lookup, backtesting, market regime, alerts)
- Troubleshooting

## Maintaining the skill

`hypertracker-skill-master.md` is the single source of truth. After editing it, run `python3 scripts/sync-skill-files.py` to update every platform file (`SKILL.md` gets the YAML frontmatter, the rest are verbatim copies). `python3 scripts/sync-skill-files.py --check` exits non-zero if any copy has drifted.

## Links

- [Get your API key](https://app.coinmarketman.com/hypertracker/api-dashboard)
- [API Docs](https://docs.coinmarketman.com)
- [HyperTracker Site](https://hypertracker.io)
- [CoinMarketMan Site](https://coinmarketman.com)
- [Discord](https://discord.gg/szZ4X3Z)
- [X](https://x.com/HyperTracker)
- [Telegram](https://t.me/HyperTrackerio)



## Maintained by
HyperTracker Team at CoinMarketMan
