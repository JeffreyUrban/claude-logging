"""Tests for dump command (HTML conversion) functionality."""

import argparse
from pathlib import Path

import pytest


@pytest.fixture
def sample_log_file(tmp_path):
    """Create a simple sample log file with ANSI codes."""
    log_file = tmp_path / 'test.log'
    log_file.write_text('\x1b[1mBold text\x1b[0m\nNormal text\n\x1b[31mRed text\x1b[0m\n\x1b[32mGreen text\x1b[0m\n')
    return log_file


@pytest.fixture
def real_claude_log():
    """Path to real Claude session log file."""
    fixtures_dir = Path(__file__).parent / 'fixtures'
    log_file = fixtures_dir / 'real-claude-session.log'
    if not log_file.exists():
        pytest.skip(f'Real Claude log fixture not found: {log_file}')
    return log_file


@pytest.mark.unit
class TestDumpCommand:
    """Test dump command (HTML conversion)."""

    def test_converts_log_to_html(self, sample_log_file, tmp_path):
        """Dump command should convert log file to HTML."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'output.html'

        args = argparse.Namespace(input_files=[str(sample_log_file)], output_file=str(output_file))

        dump_command(args)

        # Check HTML file was created
        assert output_file.exists()

        # Check HTML content
        html_content = output_file.read_text()
        assert '<!DOCTYPE html>' in html_content
        assert '<html' in html_content
        assert '</html>' in html_content

    def test_preserves_text_content(self, sample_log_file, tmp_path):
        """HTML output should contain original text content."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'output.html'

        args = argparse.Namespace(input_files=[str(sample_log_file)], output_file=str(output_file))

        dump_command(args)

        html_content = output_file.read_text()

        # Text should be present (ANSI codes stripped)
        assert 'Bold text' in html_content
        assert 'Normal text' in html_content
        assert 'Red text' in html_content
        assert 'Green text' in html_content

    def test_auto_generates_output_filename(self, sample_log_file, tmp_path, monkeypatch):
        """Without -o flag, should generate .html file in current directory."""
        from claude_logging.__main__ import dump_command

        # Change to tmp_path to avoid polluting current directory
        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace(input_files=[str(sample_log_file)], output_file=None)

        dump_command(args)

        # Should create test.html in current directory
        expected_file = tmp_path / 'test.html'
        assert expected_file.exists()

    def test_handles_multiple_files(self, tmp_path, monkeypatch):
        """Should process multiple log files."""
        from claude_logging.__main__ import dump_command

        # Create multiple log files
        log1 = tmp_path / 'log1.log'
        log2 = tmp_path / 'log2.log'
        log1.write_text('Content 1\n')
        log2.write_text('Content 2\n')

        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace(input_files=[str(log1), str(log2)], output_file=None)

        dump_command(args)

        # Should create both HTML files
        assert (tmp_path / 'log1.html').exists()
        assert (tmp_path / 'log2.html').exists()

    def test_rejects_output_flag_with_multiple_files(self, tmp_path):
        """Should reject -o flag when processing multiple files."""
        from claude_logging.__main__ import dump_command

        log1 = tmp_path / 'log1.log'
        log2 = tmp_path / 'log2.log'
        log1.write_text('Content 1\n')
        log2.write_text('Content 2\n')

        args = argparse.Namespace(input_files=[str(log1), str(log2)], output_file='output.html')

        with pytest.raises(SystemExit):
            dump_command(args)


@pytest.mark.unit
class TestProcessSingleFile:
    """Test process_single_file helper."""

    def test_processes_valid_file(self, sample_log_file):
        """Should process file and return HTML."""
        from claude_logging.__main__ import process_single_file

        html = process_single_file(str(sample_log_file))

        assert html is not None
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html
        assert 'Bold text' in html

    def test_handles_nonexistent_file(self, tmp_path):
        """Should return None for nonexistent file."""
        from claude_logging.__main__ import process_single_file

        result = process_single_file(str(tmp_path / 'nonexistent.log'))

        assert result is None


@pytest.mark.unit
class TestGetDefaultOutputPath:
    """Test get_default_output_path helper."""

    def test_replaces_extension_with_html(self):
        """Should replace .log with .html."""
        from claude_logging.__main__ import get_default_output_path

        result = get_default_output_path('/path/to/file.log')

        assert result == 'file.html'

    def test_uses_filename_only(self):
        """Should strip directory path."""
        from claude_logging.__main__ import get_default_output_path

        result = get_default_output_path('/very/long/path/to/some/file.log')

        assert result == 'file.html'

    def test_handles_stdin(self):
        """Should return '-' for stdin input."""
        from claude_logging.__main__ import get_default_output_path

        result = get_default_output_path('-')

        assert result == '-'


@pytest.mark.integration
class TestRealClaudeSession:
    """Test with real Claude Code session log."""

    def test_processes_real_claude_log(self, real_claude_log, tmp_path):
        """Should successfully process a real Claude session log."""
        from claude_logging.__main__ import process_single_file

        html = process_single_file(str(real_claude_log))

        assert html is not None
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

    def test_real_log_compression(self, real_claude_log, tmp_path):
        """Real Claude logs should compress significantly."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        # Check compression ratio
        raw_size = real_claude_log.stat().st_size
        html_size = output_file.stat().st_size

        # HTML should be significantly smaller (expect >90% reduction)
        compression_ratio = 1 - (html_size / raw_size)
        assert compression_ratio > 0.9, f'Expected >90% compression, got {compression_ratio:.1%}'

    def test_real_log_eliminates_duplicates(self, real_claude_log, tmp_path):
        """Real Claude logs should have massive line reduction."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        # Count lines
        with open(real_claude_log) as f:
            raw_lines = sum(1 for _ in f)

        with open(output_file) as f:
            html_lines = sum(1 for _ in f)

        # HTML should have far fewer lines (expect >95% reduction)
        reduction = 1 - (html_lines / raw_lines)
        assert reduction > 0.9, f'Expected >90% line reduction, got {reduction:.1%}'

    def test_real_log_has_valid_html_structure(self, real_claude_log, tmp_path):
        """Generated HTML should have proper structure."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        html_content = output_file.read_text()

        # Check for essential HTML elements
        assert '<!DOCTYPE html>' in html_content
        assert '<html lang="en">' in html_content
        assert '<head>' in html_content
        assert '<title>Terminal Output</title>' in html_content
        assert '<body' in html_content
        assert '</body>' in html_content
        assert '</html>' in html_content

    def test_real_log_has_line_numbers(self, real_claude_log, tmp_path):
        """Generated HTML should have line numbers with permalinks."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        html_content = output_file.read_text()

        # Check for line number structure
        assert 'class="line"' in html_content
        assert 'class="line-number"' in html_content
        assert 'class="line-content"' in html_content
        assert 'id="L' in html_content  # Line permalinks

    def test_real_log_has_theme_toggle(self, real_claude_log, tmp_path):
        """Generated HTML should have theme toggle functionality."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        html_content = output_file.read_text()

        # Check for theme toggle
        assert 'theme-toggle' in html_content or 'data-theme' in html_content
        assert '--bg-color' in html_content  # CSS variables for theming

    def test_real_log_preserves_formatting(self, real_claude_log, tmp_path):
        """Generated HTML should preserve ANSI formatting."""
        from claude_logging.__main__ import dump_command

        output_file = tmp_path / 'real-session.html'
        args = argparse.Namespace(input_files=[str(real_claude_log)], output_file=str(output_file))

        dump_command(args)

        html_content = output_file.read_text()

        # Check for color classes (ANSI codes converted to CSS)
        assert 'class="c' in html_content or 'class="fg-' in html_content  # Color classes
        assert 'class="bold"' in html_content or 'font-weight: bold' in html_content  # Bold text
