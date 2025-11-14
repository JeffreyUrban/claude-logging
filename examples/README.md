# Examples

Example integrations for using claude-logging in your projects.

## JetBrains IDE Run Configuration

**`JetBrains/Claude_Code_Default_Mode.run.xml`** - Run configuration for default mode

Launches Claude Code with logging to `~/.claude/logs` using the original filename pattern.

### Installation

```bash
# Copy to your project's .run directory
mkdir -p .run
cp examples/JetBrains/Claude_Code_Default_Mode.run.xml .run/
```

Restart your IDE or select **File → Reload All from Disk**.

### Usage

1. Select "Claude->Log" from the run configuration dropdown
2. Click Run or use keyboard shortcut
3. Claude will launch with automatic logging enabled
4. Logs are stored in `~/.claude/logs/`

### Customization

Edit the XML file to customize:

```xml
<envs>
  <!-- Add custom log directory -->
  <env name="CLAUDE_LOG_DIR" value="/custom/path/logs" />

  <!-- Add custom filename pattern -->
  <env name="CLAUDE_LOGGING_FILENAME_PATTERN" value="session-{timestamp}.log" />
</envs>
```

## Worktree Examples

See [`worktree/`](worktree/) directory for:
- Shell scripts for worktree-mode logging
- JetBrains run configuration for worktree mode
- Complete integration guide and workflows

**Key difference:** Worktree mode centralizes logs from multiple git worktrees in the main worktree's `logs/` directory, with worktree names in filenames.

## See Also

- [Main README](../README.md) - Full package documentation
- [Worktree Examples](worktree/README.md) - Multi-worktree workflows
