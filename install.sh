#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One-liner: curl -fsSL https://raw.githubusercontent.com/jaylooloomi/just-build-it/main/install.sh | bash
set -e
command -v claude >/dev/null || { echo "claude CLI not found. Install Claude Code first."; exit 1; }
claude plugin marketplace add jaylooloomi/just-build-it 2>/dev/null || claude plugin marketplace update jaylooloomi-build
claude plugin install just-build-it@jaylooloomi-build ${SCOPE:+--scope "$SCOPE"}
claude plugin list | grep -A1 just-build-it || true
echo
echo "Installed. Configure once: ~/.claude/settings.json -> \"env\": { \"CLAUDE_CODE_STOP_HOOK_BLOCK_CAP\": \"0\" }"
echo "Then: claude --dangerously-skip-permissions  and type  /just-build-it:go 8 --scope src/<module>"
