#!/usr/bin/env bash
# Example wrapper script for launching Claude Code with worktree-mode logging
#
# This script demonstrates how to use claude-logging in worktree mode:
# - Logs are centralized in main worktree's logs/ directory
# - Filenames include worktree name: claude-<worktree>-YYYYMMDD-HHMMSS.log
# - Real-time logging with immediate flush (macOS & Linux)
#
# Usage:
#   ./start-claude.sh [claude arguments...]
#
# Environment Variables:
#   CLAUDE_LOG_DIR - Override default log directory (optional)
#
# Examples:
#   ./start-claude.sh                    # Start Claude with logging
#   CLAUDE_LOG_DIR=/tmp/logs ./start-claude.sh  # Custom log directory

set -euo pipefail

# Enable worktree mode
export CLAUDE_LOGGING_WORKTREE_MODE=1

# Launch Claude with logging
# Uses 'python -m claude_logging' to run the package
# If you installed via pip, this will use the installed version
# If you're in development, it will use the local version
python -m claude_logging "$@"
