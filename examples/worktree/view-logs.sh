#!/usr/bin/env bash
# Example utility script for viewing and managing Claude Code worktree logs
#
# This script provides commands to:
# - List all session logs
# - View logs (raw or with ANSI codes stripped)
# - Tail logs in real-time
# - Search across logs
# - Convert logs to clean HTML
#
# Usage:
#   ./view-logs.sh list                              # List all logs
#   ./view-logs.sh view <worktree> [date] [--clean]  # View log for worktree
#   ./view-logs.sh tail [worktree]                   # Tail latest log
#   ./view-logs.sh search <term> [worktree]          # Search logs
#   ./view-logs.sh html <worktree> [date]            # Convert to HTML
#
# Environment Variables:
#   CLAUDE_LOG_DIR - Override log directory (default: main worktree's logs/)

set -euo pipefail

# Find main worktree
# Can be overridden with CLAUDE_LOG_DIR environment variable
if [ -n "${CLAUDE_LOG_DIR:-}" ]; then
    LOG_DIR="$CLAUDE_LOG_DIR"
else
    MAIN_WORKTREE=$(git worktree list 2>/dev/null | head -1 | awk '{print $1}' || echo "$HOME")
    LOG_DIR="$MAIN_WORKTREE/logs"
fi

# Check if logs directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ No logs directory found at: $LOG_DIR"
    echo "💡 Start Claude with logging first (see examples/worktree/start-claude.sh)"
    exit 1
fi

# Function to list all logs
list_logs() {
    echo "📋 Claude Code Session Logs"
    echo "============================"
    echo ""

    if [ ! "$(ls -A "$LOG_DIR")" ]; then
        echo "No logs found"
        return
    fi

    echo "Recent logs (newest first):"
    echo ""

    # List with human-readable details
    ls -lht "$LOG_DIR"/claude-*.log 2>/dev/null | while read -r line; do
        # Extract filename from ls output
        filename=$(echo "$line" | awk '{print $NF}')
        basename_file=$(basename "$filename")

        # Parse filename: claude-<worktree>-YYYYMMDD-HHMMSS.log
        if [[ $basename_file =~ claude-(.+)-([0-9]{8})-([0-9]{6})\.log ]]; then
            worktree="${BASH_REMATCH[1]}"
            date="${BASH_REMATCH[2]}"
            time="${BASH_REMATCH[3]}"

            # Format date and time
            formatted_date="${date:0:4}-${date:4:2}-${date:6:2}"
            formatted_time="${time:0:2}:${time:2:2}:${time:4:2}"

            # Get file size
            size=$(ls -lh "$filename" | awk '{print $5}')

            echo "  📁 $worktree  |  📅 $formatted_date $formatted_time  |  📦 $size"
            echo "     $basename_file"
            echo ""
        fi
    done
}

# Function to view a specific log
view_log() {
    local log_file="$1"

    if [ ! -f "$log_file" ]; then
        echo "❌ Log file not found: $log_file"
        exit 1
    fi

    # Use less with raw control characters for proper formatting
    # -R: output raw control characters (for colors)
    # -X: don't clear screen on exit
    # -F: quit if one screen
    less -RXF "$log_file"
}

# Function to tail the latest log
tail_latest() {
    local worktree="${1:-}"

    if [ -n "$worktree" ]; then
        # Find latest log for specific worktree
        latest=$(ls -t "$LOG_DIR"/claude-${worktree}-*.log 2>/dev/null | head -1)
    else
        # Find latest log overall
        latest=$(ls -t "$LOG_DIR"/claude-*.log 2>/dev/null | head -1)
    fi

    if [ -z "$latest" ]; then
        echo "❌ No logs found"
        exit 1
    fi

    echo "📝 Tailing: $(basename "$latest")"
    echo "================================"
    echo ""
    tail -f "$latest"
}

# Function to search logs
search_logs() {
    local search_term="$1"
    local worktree="${2:-}"

    echo "🔍 Searching logs for: '$search_term'"
    echo "================================"
    echo ""

    if [ -n "$worktree" ]; then
        pattern="claude-${worktree}-*.log"
    else
        pattern="claude-*.log"
    fi

    # Use find with grep to safely handle patterns and filenames with special characters
    find "$LOG_DIR" -name "$pattern" -type f -exec grep -Hn "$search_term" {} + 2>/dev/null || {
        echo "No matches found"
        return
    }
}

# Main command dispatcher
case "${1:-list}" in
    list|ls)
        list_logs
        ;;
    view|cat)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 view <log-file> [--clean]"
            echo "   or: $0 view <worktree> [date] [--clean]"
            echo ""
            echo "Use --clean to strip ANSI escape codes for easier reading"
            exit 1
        fi

        # Check if --clean flag is present in any argument
        clean_mode=false
        for arg in "$@"; do
            if [ "$arg" = "--clean" ]; then
                clean_mode=true
                break
            fi
        done

        # Function to display log (with or without cleaning)
        display_log() {
            local file="$1"
            if [ "$clean_mode" = true ]; then
                # Strip ANSI codes and control characters for easier reading
                # Using sed for ANSI codes, col -b for backspaces (if available)
                if command -v col > /dev/null 2>&1; then
                    sed -E 's/\x1B\[[0-9;?]*[a-zA-Z]//g; s/\x1B\][0-9;]*[^\x07]*\x07//g' "$file" | \
                        col -b | \
                        less -XF
                else
                    # col not available - warn user about limited cleaning
                    echo "⚠️  'col' command not found - backspaces won't be processed" >&2
                    echo "   For best results, use: $0 html $(basename "$file" .log)" >&2
                    echo "" >&2
                    sed -E 's/\x1B\[[0-9;?]*[a-zA-Z]//g; s/\x1B\][0-9;]*[^\x07]*\x07//g' "$file" | \
                        less -XF
                fi
            else
                view_log "$file"
            fi
        }

        if [ -f "$2" ]; then
            display_log "$2"
        elif [ -f "$LOG_DIR/$2" ]; then
            display_log "$LOG_DIR/$2"
        else
            # Try to find by worktree and date
            worktree="$2"
            date="${3:-}"
            if [ -n "$date" ] && [ "$date" != "--clean" ]; then
                # Format date if needed (remove dashes)
                date_clean=$(echo "$date" | tr -d '-')
                matching=$(ls "$LOG_DIR"/claude-${worktree}-${date_clean}-*.log 2>/dev/null | head -1)
                if [ -n "$matching" ]; then
                    display_log "$matching"
                else
                    echo "❌ No log found for worktree '$worktree' on date '$date'"
                    exit 1
                fi
            else
                # Show latest for this worktree
                latest=$(ls -t "$LOG_DIR"/claude-${worktree}-*.log 2>/dev/null | head -1)
                if [ -n "$latest" ]; then
                    display_log "$latest"
                else
                    echo "❌ No logs found for worktree '$worktree'"
                    exit 1
                fi
            fi
        fi
        ;;
    tail)
        tail_latest "${2:-}"
        ;;
    search|grep)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 search <search-term> [worktree]"
            exit 1
        fi
        search_logs "$2" "${3:-}"
        ;;
    html)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 html <log-file>"
            echo "   or: $0 html <worktree> [date]"
            echo ""
            echo "Converts log to clean HTML using claude-logging package"
            echo "Eliminates TUI artifacts and creates readable, styled HTML output"
            exit 1
        fi

        # Find the log file
        if [ -f "$2" ]; then
            log_file="$2"
        elif [ -f "$LOG_DIR/$2" ]; then
            log_file="$LOG_DIR/$2"
        else
            # Try to find by worktree and date
            worktree="$2"
            date="${3:-}"
            if [ -n "$date" ]; then
                # Format date if needed (remove dashes)
                date_clean=$(echo "$date" | tr -d '-')
                matching=$(ls "$LOG_DIR"/claude-${worktree}-${date_clean}-*.log 2>/dev/null | head -1)
                if [ -n "$matching" ]; then
                    log_file="$matching"
                else
                    echo "❌ No log found for worktree '$worktree' on date '$date'"
                    exit 1
                fi
            else
                # Show latest for this worktree
                latest=$(ls -t "$LOG_DIR"/claude-${worktree}-*.log 2>/dev/null | head -1)
                if [ -n "$latest" ]; then
                    log_file="$latest"
                else
                    echo "❌ No logs found for worktree '$worktree'"
                    exit 1
                fi
            fi
        fi

        # Generate HTML filename
        html_file="${log_file%.log}.html"

        echo "🔄 Converting log to HTML..."
        echo "   Input:  $(basename "$log_file")"
        echo "   Output: $(basename "$html_file")"
        echo ""

        # Use claude-logging package to convert
        python -m claude_logging dump "$log_file" -o "$html_file"

        echo ""
        echo "✅ HTML generated: $html_file"
        echo "💡 Open in browser:"
        echo "   open '$html_file'"
        ;;
    help|--help|-h)
        cat <<EOF
Claude Code Log Viewer (Worktree Mode)

Usage:
  $0 list                              List all session logs
  $0 view <worktree> [date] [--clean] View log for worktree (latest or specific date)
  $0 view <log-file> [--clean]        View specific log file
  $0 tail [worktree]                  Tail latest log (all or specific worktree)
  $0 search <term> [worktree]         Search logs for term
  $0 html <worktree> [date]           Convert log to clean HTML (removes TUI artifacts)

Options:
  --clean    Strip ANSI escape codes from log output for easier reading
             (Basic cleanup using sed/col - for best results use 'html' command)

Examples:
  $0 list                         # Show all logs
  $0 view myproject               # View latest log for myproject worktree
  $0 view myproject --clean       # View with ANSI codes stripped (basic)
  $0 html myproject               # Convert to clean HTML (recommended for readability)
  $0 view myproject 20251113      # View myproject log from Nov 13, 2025
  $0 tail                         # Tail latest log
  $0 tail myproject               # Tail latest myproject log
  $0 search "error" myproject     # Search myproject logs for "error"

HTML Conversion:
  The 'html' command uses claude-logging package to clean up TUI artifacts:
  - Eliminates duplicate lines from screen redraws
  - Preserves syntax highlighting and colors
  - Provides clickable line numbers and theme toggling
  - Much cleaner than raw logs or --clean option
  - Uses terminal emulator to replay ANSI sequences and show final screen state

Log Location: $LOG_DIR
Log Format: claude-<worktree>-YYYYMMDD-HHMMSS.log
EOF
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
