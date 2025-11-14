# Worktree Mode Examples

Example scripts demonstrating how to use claude-logging in worktree mode for managing multiple Claude Code sessions across git worktrees.

## Scripts

### `start-claude.sh`

Simple wrapper to launch Claude Code with worktree-mode logging enabled.

**What it does:**
- Sets `CLAUDE_LOGGING_WORKTREE_MODE=1`
- Launches `python -m claude_logging`
- Logs are stored in main worktree's `logs/` directory
- Filenames include worktree name: `claude-<worktree>-YYYYMMDD-HHMMSS.log`

**Usage:**
```bash
# From any git worktree
./start-claude.sh

# With custom log directory
CLAUDE_LOG_DIR=/tmp/logs ./start-claude.sh
```

**Integration:**
Copy this script to your project root or add to your PATH for easy access from any worktree.

### `view-logs.sh`

Utility for viewing, searching, and converting worktree logs.

**Commands:**
```bash
# List all session logs
./view-logs.sh list

# View latest log for a worktree
./view-logs.sh view myproject

# View specific date
./view-logs.sh view myproject 20251113

# Strip ANSI codes for easier reading
./view-logs.sh view myproject --clean

# Search across logs
./view-logs.sh search "authentication"
./view-logs.sh search "error" myproject

# Convert to clean HTML (recommended)
./view-logs.sh html myproject
./view-logs.sh html myproject 20251113
```

**Integration:**
Copy this script to your project root or add to your PATH. It automatically finds the main worktree's `logs/` directory.

## Typical Workflow

### 1. Setup

Copy scripts to your project:
```bash
# From your git repository root
cp /path/to/claude-logging/examples/worktree/*.sh .
chmod +x *.sh
```

Or install globally:
```bash
# Make available system-wide
cp /path/to/claude-logging/examples/worktree/*.sh /usr/local/bin/
```

### 2. Start Logging

From any worktree:
```bash
./start-claude.sh
```

This creates a log in the main worktree's `logs/` directory.

### 3. Monitor Sessions

While Claude is running, from another terminal:
```bash
# Tail the active session to stream updates
./view-logs.sh tail myworktree

# Or convert to HTML during session for a clean view, with no further updates
./view-logs.sh html myworktree
open logs/claude-myworktree-*.html
```

### 4. Review and Search

After sessions:
```bash
# List all sessions
./view-logs.sh list

# Search for specific topics
./view-logs.sh search "database migration"

# Convert important sessions to HTML for sharing
./view-logs.sh html myworktree 20251113
```

## Multi-Worktree Scenarios

### Parallel Claude Instances

Run multiple Claude instances across different worktrees:

**Terminal 1 (worktree: feature-auth):**
```bash
cd ~/project-feature-auth
./start-claude.sh
```

**Terminal 2 (worktree: feature-ui):**
```bash
cd ~/project-feature-ui
./start-claude.sh
```

**Terminal 3 (monitoring):**
```bash
cd ~/project  # Main worktree
./view-logs.sh list
# Shows logs from both feature-auth and feature-ui
```

All logs centralized in `~/project/logs/`:
- `claude-feature-auth-20251113-143000.log`
- `claude-feature-ui-20251113-143100.log`

## Environment Variables

### `CLAUDE_LOGGING_WORKTREE_MODE`

Enable worktree mode (automatically set by `start-claude.sh`):
```bash
export CLAUDE_LOGGING_WORKTREE_MODE=1
```

### `CLAUDE_LOG_DIR`

Override default log directory:
```bash
export CLAUDE_LOG_DIR=/custom/path/to/logs
./start-claude.sh
```

Both scripts respect this variable for custom log locations.

## Integration with Your Project

### Option 1: Project-Specific Scripts

Copy and customize the scripts for your project:

```bash
# In your project root
mkdir -p scripts
cp examples/worktree/*.sh scripts/
```

Update paths if needed, add project-specific logic.

### Option 2: Shell Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias claude-worktree='CLAUDE_LOGGING_WORKTREE_MODE=1 python -m claude_logging'
alias claude-logs='/path/to/view-logs.sh'
```

Then use from any worktree:
```bash
claude-worktree          # Start logged session
claude-logs list         # View all logs
claude-logs html main    # Convert latest main worktree log
```

### Option 3: JetBrains IDE Run Configuration

**`JetBrains/Claude_Code_Worktree_Mode.run.xml`** - Run configuration for worktree mode

Launches Claude Code with `CLAUDE_LOGGING_WORKTREE_MODE=1`, storing logs in main worktree's `logs/` directory with worktree names in filenames.

**Installation:**
```bash
# Copy to your project's .run directory
mkdir -p .run
cp examples/worktree/JetBrains/Claude_Code_Worktree_Mode.run.xml .run/
```

You may need to restart your IDE or select **File → Reload All from Disk**.

**Usage:**
1. Select "Claude->Log (Worktree)" from the run configuration dropdown
2. Click Run or use keyboard shortcut
3. Claude will launch with worktree logging enabled
4. Logs appear in main worktree's `logs/` directory

**Customization:**
Edit the XML file to add custom environment variables:

```xml
<envs>
  <env name="CLAUDE_LOGGING_WORKTREE_MODE" value="1" />
  <!-- Override log directory -->
  <env name="CLAUDE_LOG_DIR" value="/custom/path/logs" />
  <!-- Custom filename pattern -->
  <env name="CLAUDE_LOGGING_FILENAME_PATTERN" value="session-{worktree}-{timestamp}.log" />
</envs>
```

### Option 4: Git Hooks

Automatically log Claude sessions as part of your workflow:

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Reminder to review Claude logs before committing
if [ -d "logs" ] && [ "$(ls -A logs/*.log 2>/dev/null)" ]; then
    echo "💡 Claude sessions available for review:"
    ls -t logs/claude-*.log | head -3
fi
```

## Tips

**Real-time monitoring:**
```bash
# Watch for new log entries
watch -n 5 'ls -lht logs/claude-*.log | head -5'
```

**Compress old logs:**
```bash
# Archive logs older than 30 days
find logs/ -name "claude-*.log" -mtime +30 -exec gzip {} \;
```

**Batch HTML conversion:**
```bash
# Convert all logs from a specific worktree
for log in logs/claude-myworktree-*.log; do
    ./view-logs.sh html "$log"
done
```

**Search across all HTML files:**
```bash
# After converting to HTML
grep -r "authentication" logs/*.html
```

## See Also

- [claude-logging README](../../README.md) - Main package documentation
- [Environment Variables](../../README.md#additional-features-this-fork) - Configuration options
- [Testing](../../tests/) - Test suite for worktree functionality
