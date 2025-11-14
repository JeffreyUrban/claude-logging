#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

# Import our local modules
try:
    from claude_logging import pytermdump
    from claude_logging.ansi2html import generate_html
except ImportError:
    print('Error: Required modules not found. Make sure the claude_logging package is properly installed.')
    sys.exit(1)


def process_single_file(input_file):
    """
    Process a single file with termdump and convert it to HTML.
    Returns the HTML output as a string or None if there was an error.
    """
    # Determine input source
    if input_file == '-':
        input_data = sys.stdin.buffer.read()
    else:
        try:
            with open(input_file, 'rb') as f:
                input_data = f.read()
        except Exception as e:
            print(f'Error reading input file: {e}', file=sys.stderr)
            return None

    # Process with pytermdump
    try:
        processed_data = pytermdump.termdump(input_data)
        processed_text = processed_data.decode('utf-8', errors='replace')
    except Exception as e:
        print(f'Error processing with pytermdump: {e}', file=sys.stderr)
        return None

    # Convert to HTML
    try:
        html_output = generate_html(processed_text)
        return html_output
    except Exception as e:
        print(f'Error converting to HTML: {e}', file=sys.stderr)
        return None


def dump_command(args):
    """
    Process files with termdump and convert them to HTML.
    This command:
    1. Processes each input file
    2. Converts each file to HTML
    3. Writes HTML files with appropriate names
    4. Shows progress to stdout
    """
    # Check if output option is used with multiple files
    if args.output_file and args.output_file != '-' and len(args.input_files) > 1:
        print('Error: -o/--output option cannot be used with multiple input files', file=sys.stderr)
        sys.exit(1)

    # If stdin is used, we can only process one file
    if '-' in args.input_files and len(args.input_files) > 1:
        print("Error: Cannot process stdin ('-') along with other files", file=sys.stderr)
        sys.exit(1)

    # Process each file
    total_files = len(args.input_files)

    for idx, input_file in enumerate(args.input_files, 1):
        # Determine output file
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = get_default_output_path(input_file)

        # Process the file
        html_output = process_single_file(input_file)

        if html_output is None:
            # Error already reported by process_single_file
            continue

        # Write output
        if output_file == '-':
            sys.stdout.write(html_output)
        else:
            try:
                with open(output_file, 'w') as f:
                    f.write(html_output)
                print(f'[{idx}/{total_files}] {output_file}')
            except Exception as e:
                print(f'Error writing output file: {e}', file=sys.stderr)
                continue


def get_default_output_path(input_file):
    """Generate a default output filename in the current directory with .html extension"""
    if input_file == '-':
        return '-'  # Use stdout for stdin input

    input_path = Path(input_file)
    # Use just the filename without directory, and replace extension with .html
    filename = input_path.name
    return str(Path(filename).with_suffix('.html'))


def claude_command(args):
    """
    Execute the claude command and log the session.
    This is the default mode that:
    1. Creates a log directory if needed
    2. Generates a unique log filename based on worktree and timestamp
    3. Uses script command to record the session
    4. Passes all command line arguments to the claude command
    """
    # Check if worktree mode is enabled (opt-in for backward compatibility)
    worktree_mode = os.environ.get('CLAUDE_LOGGING_WORKTREE_MODE', '').lower() in ('1', 'true', 'yes')

    # Determine log directory
    log_dir = os.environ.get('CLAUDE_LOG_DIR')

    if not log_dir:
        if worktree_mode:
            # Worktree mode: Try to find main worktree using git
            try:
                result = subprocess.run(['git', 'worktree', 'list'], capture_output=True, text=True, check=True)
                # First line is main worktree
                main_worktree = result.stdout.split('\n')[0].split()[0]
                log_dir = os.path.join(main_worktree, 'logs')
            except (subprocess.CalledProcessError, IndexError):
                # Fall back to default if not in git repo
                log_dir = os.path.expanduser('~/.claude/logs')
        else:
            # Default mode: use ~/.claude/logs
            log_dir = os.path.expanduser('~/.claude/logs')

    os.makedirs(log_dir, exist_ok=True)

    # Generate log filename
    # Check for custom filename pattern
    filename_pattern = os.environ.get('CLAUDE_LOGGING_FILENAME_PATTERN')

    if filename_pattern:
        # Custom pattern with placeholder support
        # Available placeholders: {worktree}, {repo}, {timestamp}, {date}, {time}, {datetime}
        worktree_name = os.path.basename(os.getcwd())
        repo_name = os.path.basename(os.getcwd())
        now = datetime.datetime.now()
        timestamp = now.strftime('%Y%m%d-%H%M%S')
        date = now.strftime('%Y%m%d')
        time = now.strftime('%H%M%S')
        datetime_str = now.strftime('%Y%m%d-%H%M%S')

        # Format the filename with available variables
        filename = filename_pattern.format(
            worktree=worktree_name, repo=repo_name, timestamp=timestamp, date=date, time=time, datetime=datetime_str
        )
        log_file = os.path.join(log_dir, filename)
    elif worktree_mode:
        # Worktree mode: claude-<worktree>-YYYYMMDD-HHMMSS.log
        worktree_name = os.path.basename(os.getcwd())
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        log_file = os.path.join(log_dir, f'claude-{worktree_name}-{timestamp}.log')
    else:
        # Default mode: {repo}.{date}.{n}.log (original behavior)
        repo_name = os.path.basename(os.getcwd())
        date = datetime.date.today().isoformat()
        n = 0
        while True:
            log_file = os.path.join(log_dir, f'{repo_name}.{date}.{n}.log')
            if not os.path.exists(log_file):
                break
            n += 1

    # Combine all remaining args into command string
    claude_args = args.claude_args if hasattr(args, 'claude_args') else []

    # Print session info
    if worktree_mode:
        print('🤖 Starting Claude Code with session logging')
        print(f'📁 Worktree: {os.path.basename(os.getcwd())}')
        print(f'📝 Log file: {log_file}')
        print('')

    try:
        # Build the claude command including all arguments
        claude_cmd = ['claude'] + claude_args

        # Use script to record the session
        # macOS and Linux have different syntax
        import platform

        system = platform.system()

        if system == 'Darwin':  # macOS
            # macOS syntax: script -q -F file command
            cmd = ['script', '-q', '-F', log_file] + claude_cmd
        else:  # Linux
            # Linux syntax: script --flush --quiet --return --command "cmd" file
            cmd = ['script', '--flush', '--quiet', '--return', '--command', ' '.join(claude_cmd), log_file]

        # Execute command
        subprocess.run(cmd)

        if worktree_mode:
            print('')
            print('✅ Session ended')
            print(f'📝 Log saved: {log_file}')
            print(f'💡 Convert to HTML: python -m claude_logging dump {log_file}')
    except Exception as e:
        print(f'Error executing claude command: {e}', file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the claude-logging CLI"""
    # Check if first arg is 'dump' to decide which mode to run
    if len(sys.argv) > 1 and sys.argv[1] == 'dump':
        # 'dump' subcommand mode
        parser = argparse.ArgumentParser(description='Claude logging utilities')
        subparsers = parser.add_subparsers(dest='command')

        # 'dump' subcommand
        dump_parser = subparsers.add_parser(
            'dump', help='Process files with terminal escape sequences and convert to HTML'
        )
        dump_parser.add_argument('input_files', nargs='+', help='Input files (use "-" for stdin)')
        dump_parser.add_argument(
            '-o', '--output', dest='output_file', help='Output file (only valid for single input file)'
        )

        # Parse the arguments
        args = parser.parse_args()

        # If no output file is specified, it will be determined for each input file
        dump_command(args)
    else:
        # Default mode: Run claude with logging
        # Don't use argparse since we want to pass all args directly to claude
        claude_args = sys.argv[1:]
        args = argparse.Namespace(claude_args=claude_args)
        claude_command(args)


if __name__ == '__main__':
    main()
