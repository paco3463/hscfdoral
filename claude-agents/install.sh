#!/bin/bash
# Installs the HSCF agents and slash commands into .claude/ so Claude Code can use them.
# Run once from anywhere:  bash "claude-agents/install.sh"
set -e
cd "$(dirname "$0")/.."
mkdir -p .claude
cp -R claude-agents/agents claude-agents/skills .claude/
echo "Installed $(ls .claude/agents | wc -l | tr -d ' ') agents and $(ls .claude/skills | wc -l | tr -d ' ') commands into .claude/"
