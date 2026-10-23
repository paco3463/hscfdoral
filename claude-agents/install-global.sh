#!/usr/bin/env bash
# Makes the "hscf-doral" agent available in Claude Code from ANY folder (like SSH DELUXE).
# Run once on each computer:  bash claude-agents/install-global.sh
set -e
cd "$(dirname "$0")"
mkdir -p "$HOME/.claude/agents"
cp global/hscf-doral.md "$HOME/.claude/agents/hscf-doral.md"
echo "Installed hscf-doral into ~/.claude/agents. Restart Claude Code, then type /agents to see it."
