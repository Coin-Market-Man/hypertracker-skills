#!/usr/bin/env python3
"""Copy hypertracker-skill-master.md (the single source of truth) into every platform file.

SKILL.md gets the YAML frontmatter that `npx skills` needs; every other file is a verbatim copy.
Run from the repo root after editing the master:  python3 scripts/sync-skill-files.py
Use --check in CI to fail when any copy has drifted from the master (.github/workflows/skill-sync.yml runs it).
Files are always read and written as UTF-8 with LF line endings, on every platform.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "hypertracker-skill-master.md"
FRONTMATTER = """---
name: hypertracker
description: Query HyperTracker's pre-computed analytics layer for Hyperliquid. Use when the user asks about Hyperliquid wallets, cohort positioning (Money Printer, Smart Money, Whales, etc.), order flow, closed trades, fundings, liquidations, leaderboards, builder codes, real-time WebSocket streams (including BBO, L2 and L4 order books), server-side alerts or webhooks, or wants to analyze any address or position on Hyperliquid perps (including HIP-3 markets). Requires a JWT bearer token from the HyperTracker API dashboard.
---

"""
COPIES = ["AGENTS.md", "copilot-instructions.md", ".github/copilot-instructions.md", ".cursorrules", "hypertracker-skill-generic.md"]


def targets():
    body = MASTER.read_text(encoding="utf-8")
    yield ROOT / "SKILL.md", FRONTMATTER + body
    for name in COPIES:
        yield ROOT / name, body


def main():
    check = "--check" in sys.argv
    drift = []
    for path, content in targets():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                drift.append(path.relative_to(ROOT))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print("synced", path.relative_to(ROOT))
    if check:
        if drift:
            print("Out of sync with hypertracker-skill-master.md:", *drift, sep="\n  ")
            sys.exit(1)
        print("All skill files match the master.")


if __name__ == "__main__":
    main()
