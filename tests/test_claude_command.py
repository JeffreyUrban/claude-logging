"""Tests for claude_command functionality with worktree mode and custom options."""

import argparse
import subprocess
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo = tmp_path / 'test-repo'
    repo.mkdir()

    # Initialize git repo
    subprocess.run(['git', 'init'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo, check=True, capture_output=True)

    # Create initial commit
    (repo / 'README.md').write_text('# Test')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo, check=True, capture_output=True)

    return repo


@pytest.fixture
def temp_worktree(temp_git_repo, tmp_path):
    """Create a temporary git worktree."""
    worktree_path = tmp_path / 'test-worktree'

    # Create worktree with a new branch (avoids "already checked out" error)
    # The -b flag creates a new branch for the worktree
    subprocess.run(
        ['git', 'worktree', 'add', '-b', 'test-branch', str(worktree_path), 'HEAD'],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    yield worktree_path

    # Cleanup
    subprocess.run(['git', 'worktree', 'remove', str(worktree_path)], cwd=temp_git_repo, capture_output=True)


@pytest.fixture
def mock_script_command():
    """Mock subprocess.run to avoid actually running script command."""
    # Save original subprocess.run before patching
    original_run = subprocess.run

    with patch('subprocess.run') as mock_run:
        # Make git commands work but mock script command
        def side_effect(*args, **kwargs):
            # Allow git commands to execute normally using original function
            if args[0][0] == 'git':
                return original_run(*args, **kwargs)
            # Mock script/claude commands
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result

        mock_run.side_effect = side_effect
        yield mock_run


def extract_log_file_from_command(call_args):
    """Extract log file path from script command arguments.

    macOS: ['script', '-q', '-F', log_file, ...]  -> index 3
    Linux: ['script', '--flush', '--quiet', '--return', '--command', cmd, log_file]  -> index -1
    """
    import platform

    if platform.system() == 'Darwin':
        # macOS: log file is at index 3
        return call_args[3]
    else:
        # Linux: log file is last argument
        return call_args[-1]


@pytest.mark.unit
class TestDefaultMode:
    """Test original claude-logging behavior (backward compatibility)."""

    def test_uses_home_directory_by_default(self, temp_git_repo, mock_script_command, monkeypatch):
        """Original mode stores logs in ~/.claude/logs."""
        from claude_logging.__main__ import claude_command

        monkeypatch.chdir(temp_git_repo)

        # Ensure worktree mode is NOT enabled
        monkeypatch.delenv('CLAUDE_LOGGING_WORKTREE_MODE', raising=False)
        monkeypatch.delenv('CLAUDE_LOG_DIR', raising=False)

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        # Check that script command was called
        assert mock_script_command.called
        call_args = mock_script_command.call_args[0][0]

        # Log file should be in ~/.claude/logs
        log_file = extract_log_file_from_command(call_args)
        assert '/.claude/logs/' in log_file
        assert log_file.endswith('.log')

    def test_uses_incremental_naming(self, temp_git_repo, mock_script_command, monkeypatch, tmp_path):
        """Original mode uses {repo}.{date}.{n}.log format."""
        from claude_logging.__main__ import claude_command

        # Use temp directory for testing
        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))
        monkeypatch.delenv('CLAUDE_LOGGING_WORKTREE_MODE', raising=False)
        monkeypatch.chdir(temp_git_repo)

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use format: test-repo.YYYY-MM-DD.0.log
        assert 'test-repo.' in log_file
        assert '.0.log' in log_file


@pytest.mark.unit
class TestWorktreeMode:
    """Test worktree mode functionality."""

    def test_finds_main_worktree(self, temp_worktree, temp_git_repo, mock_script_command, monkeypatch):
        """Worktree mode should find main worktree and use its logs/ directory."""
        from claude_logging.__main__ import claude_command

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', '1')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use main worktree's logs/ directory
        assert str(temp_git_repo / 'logs') in log_file

    def test_uses_worktree_name_in_filename(self, temp_worktree, mock_script_command, monkeypatch):
        """Worktree mode should include worktree name in filename."""
        from claude_logging.__main__ import claude_command

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', '1')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use format: claude-{worktree}-YYYYMMDD-HHMMSS.log
        assert 'claude-test-worktree-' in log_file
        assert '.log' in log_file

    def test_timestamp_format(self, temp_worktree, mock_script_command, monkeypatch):
        """Worktree mode should use YYYYMMDD-HHMMSS timestamp format."""
        from claude_logging.__main__ import claude_command

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', '1')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Extract filename and check format
        import re

        match = re.search(r'claude-test-worktree-(\d{8}-\d{6})\.log', log_file)
        assert match is not None, f'Filename does not match expected pattern: {log_file}'

    @pytest.mark.parametrize('env_value', ['1', 'true', 'yes', 'TRUE', 'Yes'])
    def test_accepts_various_true_values(self, temp_worktree, mock_script_command, monkeypatch, env_value):
        """Worktree mode should accept various truthy values."""
        from claude_logging.__main__ import claude_command

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', env_value)

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use worktree mode naming
        assert 'claude-test-worktree-' in log_file


@pytest.mark.unit
class TestCustomLogDirectory:
    """Test CLAUDE_LOG_DIR override."""

    def test_respects_custom_directory(self, temp_git_repo, mock_script_command, monkeypatch, tmp_path):
        """CLAUDE_LOG_DIR should override default location."""
        from claude_logging.__main__ import claude_command

        custom_dir = tmp_path / 'custom-logs'
        custom_dir.mkdir()

        monkeypatch.chdir(temp_git_repo)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(custom_dir))

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        assert str(custom_dir) in log_file

    def test_works_with_worktree_mode(self, temp_worktree, mock_script_command, monkeypatch, tmp_path):
        """CLAUDE_LOG_DIR should work together with worktree mode."""
        from claude_logging.__main__ import claude_command

        custom_dir = tmp_path / 'custom-logs'
        custom_dir.mkdir()

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', '1')
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(custom_dir))

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use custom directory with worktree naming
        assert str(custom_dir) in log_file
        assert 'claude-test-worktree-' in log_file


@pytest.mark.unit
class TestCustomFilenamePattern:
    """Test CLAUDE_LOGGING_FILENAME_PATTERN functionality."""

    def test_supports_worktree_placeholder(self, temp_worktree, mock_script_command, monkeypatch, tmp_path):
        """Pattern should support {worktree} placeholder."""
        from claude_logging.__main__ import claude_command

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))
        monkeypatch.setenv('CLAUDE_LOGGING_FILENAME_PATTERN', 'session-{worktree}.log')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        assert log_file == str(log_dir / 'session-test-worktree.log')

    def test_supports_timestamp_placeholder(self, temp_git_repo, mock_script_command, monkeypatch, tmp_path):
        """Pattern should support {timestamp} placeholder."""
        from claude_logging.__main__ import claude_command

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()

        monkeypatch.chdir(temp_git_repo)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))
        monkeypatch.setenv('CLAUDE_LOGGING_FILENAME_PATTERN', 'log-{timestamp}.txt')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should have format: log-YYYYMMDD-HHMMSS.txt
        import re

        match = re.search(r'log-(\d{8}-\d{6})\.txt', log_file)
        assert match is not None

    def test_supports_multiple_placeholders(self, temp_worktree, mock_script_command, monkeypatch, tmp_path):
        """Pattern should support multiple placeholders."""
        from claude_logging.__main__ import claude_command

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))
        monkeypatch.setenv('CLAUDE_LOGGING_FILENAME_PATTERN', '{repo}-{date}-{time}.log')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should have format: test-worktree-YYYYMMDD-HHMMSS.log
        import re

        match = re.search(r'test-worktree-(\d{8})-(\d{6})\.log', log_file)
        assert match is not None

    def test_overrides_worktree_mode(self, temp_worktree, mock_script_command, monkeypatch, tmp_path):
        """Custom pattern should take precedence over worktree mode."""
        from claude_logging.__main__ import claude_command

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()

        monkeypatch.chdir(temp_worktree)
        monkeypatch.setenv('CLAUDE_LOGGING_WORKTREE_MODE', '1')
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))
        monkeypatch.setenv('CLAUDE_LOGGING_FILENAME_PATTERN', 'custom-{worktree}.log')

        args = argparse.Namespace(claude_args=[])
        claude_command(args)

        call_args = mock_script_command.call_args[0][0]
        log_file = extract_log_file_from_command(call_args)

        # Should use custom pattern, not worktree mode pattern
        assert log_file == str(log_dir / 'custom-test-worktree.log')


@pytest.mark.unit
class TestPlatformCompatibility:
    """Test macOS vs Linux script command differences."""

    @patch('platform.system')
    def test_macos_script_syntax(self, mock_platform, temp_git_repo, monkeypatch, tmp_path):
        """macOS should use 'script -q -F file command' syntax."""
        from claude_logging.__main__ import claude_command

        mock_platform.return_value = 'Darwin'

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))

        with patch('subprocess.run') as mock_run:
            args = argparse.Namespace(claude_args=[])
            claude_command(args)

            # Check script command format
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'script'
            assert call_args[1] == '-q'
            assert call_args[2] == '-F'
            # Log file should be 4th argument
            assert call_args[3].endswith('.log')
            # Claude command should follow
            assert call_args[4] == 'claude'

    @patch('platform.system')
    def test_linux_script_syntax(self, mock_platform, temp_git_repo, monkeypatch, tmp_path):
        """Linux should use 'script --flush --quiet --return --command "cmd" file' syntax."""
        from claude_logging.__main__ import claude_command

        mock_platform.return_value = 'Linux'

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))

        with patch('subprocess.run') as mock_run:
            args = argparse.Namespace(claude_args=[])
            claude_command(args)

            # Check script command format
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'script'
            assert '--flush' in call_args
            assert '--quiet' in call_args
            assert '--return' in call_args
            assert '--command' in call_args
            # Last argument should be log file
            assert call_args[-1].endswith('.log')


@pytest.mark.unit
class TestArguments:
    """Test passing arguments to claude command."""

    def test_passes_args_to_claude(self, temp_git_repo, monkeypatch, tmp_path):
        """Arguments should be passed through to claude command."""
        from claude_logging.__main__ import claude_command

        log_dir = tmp_path / 'logs'
        log_dir.mkdir()
        monkeypatch.chdir(temp_git_repo)
        monkeypatch.setenv('CLAUDE_LOG_DIR', str(log_dir))

        with patch('subprocess.run') as mock_run:
            args = argparse.Namespace(claude_args=['--help', '--version'])
            claude_command(args)

            call_args = mock_run.call_args[0][0]
            # Should include claude command with args
            assert 'claude' in str(call_args)
            # On macOS, args follow claude in command list
            # On Linux, args are in the --command string
            assert '--help' in str(call_args)
            assert '--version' in str(call_args)
