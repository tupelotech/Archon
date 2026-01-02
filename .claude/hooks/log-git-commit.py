#!/usr/bin/env python3
"""
PostToolUse hook for logging git commits to Archon.
Extracts commit message and SHA from git command output.

This hook captures git commits made by Claude Code and logs them
to the Archon change tracking system with the commit SHA for
linking changelog entries to git history.
"""
import json
import sys
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
ARCHON_API_URL = os.environ.get('ARCHON_API_URL', 'http://localhost:8181')
LOG_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'change-log.jsonl'


def get_project_config() -> dict:
    """Read project configuration from .claude/archon-project.json if exists."""
    project_file = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'archon-project.json'
    if project_file.exists():
        try:
            with open(project_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def parse_commit_output(stdout: str) -> tuple:
    """Extract commit SHA and file count from git commit output."""
    # Match patterns like "[main abc1234]" or "[feature/branch abc1234]"
    sha_match = re.search(r'\[[\w/.-]+ ([a-f0-9]+)\]', stdout)
    sha = sha_match.group(1) if sha_match else None

    # Match "X files changed" or "X file changed"
    files_match = re.search(r'(\d+) files? changed', stdout)
    file_count = int(files_match.group(1)) if files_match else 0

    # Match insertions/deletions
    insertions_match = re.search(r'(\d+) insertions?\(\+\)', stdout)
    deletions_match = re.search(r'(\d+) deletions?\(-\)', stdout)
    insertions = int(insertions_match.group(1)) if insertions_match else 0
    deletions = int(deletions_match.group(1)) if deletions_match else 0

    return sha, file_count, insertions, deletions


def extract_commit_message(command: str) -> str:
    """Extract commit message from git commit command."""
    # Handle various commit message formats:
    # -m "message"
    # -m 'message'
    # -m "$(cat <<'EOF' ... EOF)"

    # First try simple -m "message" or -m 'message'
    simple_match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
    if simple_match:
        return simple_match.group(1)

    # Try heredoc format
    heredoc_match = re.search(r'-m\s+"\$\(cat <<[\'"]?EOF[\'"]?\s*\n(.+?)\n\s*EOF', command, re.DOTALL)
    if heredoc_match:
        # Get first line of heredoc content (the actual message)
        msg = heredoc_match.group(1).strip().split('\n')[0]
        return msg

    # Fallback: look for any -m followed by text
    fallback_match = re.search(r'-m\s+["\']?([^"\'&|;]+)', command)
    if fallback_match:
        return fallback_match.group(1).strip()

    return 'Commit'


def determine_change_type(commit_msg: str) -> str:
    """Infer change type from conventional commit message."""
    msg_lower = commit_msg.lower().strip()

    # Conventional commit prefixes
    if msg_lower.startswith('feat'):
        return 'feature'
    if msg_lower.startswith('fix'):
        return 'bugfix'
    if msg_lower.startswith('refactor'):
        return 'refactor'
    if msg_lower.startswith('doc'):
        return 'docs'
    if msg_lower.startswith('test'):
        return 'test'
    if msg_lower.startswith(('chore', 'config', 'build', 'ci')):
        return 'config'

    # Keyword-based fallback
    if 'fix' in msg_lower or 'bug' in msg_lower:
        return 'bugfix'
    if 'doc' in msg_lower or 'readme' in msg_lower:
        return 'docs'
    if 'test' in msg_lower:
        return 'test'
    if 'refactor' in msg_lower or 'clean' in msg_lower:
        return 'refactor'
    if 'config' in msg_lower or 'setup' in msg_lower:
        return 'config'

    return 'feature'


def log_to_file(change_data: dict):
    """Append change to local log file for debugging."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(change_data) + '\n')
    except IOError:
        pass


def log_to_archon(change_type: str, summary: str, commit_sha: str, session_id: str, details: dict = None):
    """Call Archon API to log the change (non-blocking)."""
    config = get_project_config()
    project_id = config.get('project_id')

    if not config.get('auto_log_changes', True):
        return

    payload = {
        'change_type': change_type,
        'summary': summary,
        'session_id': session_id,
        'details': details or {}
    }

    if project_id:
        payload['project_id'] = project_id
    if commit_sha:
        payload['commit_sha'] = commit_sha

    try:
        result = subprocess.run(
            [
                'curl', '-s', '-X', 'POST',
                f'{ARCHON_API_URL}/api/changes',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(payload),
                '--max-time', '5'
            ],
            capture_output=True,
            timeout=10
        )
        log_to_file({
            'timestamp': datetime.now().isoformat(),
            'type': 'commit',
            'payload': payload,
            'response': result.stdout.decode()[:200] if result.stdout else None,
            'success': result.returncode == 0
        })
    except (subprocess.TimeoutExpired, Exception) as e:
        log_to_file({
            'timestamp': datetime.now().isoformat(),
            'type': 'commit',
            'payload': payload,
            'error': str(e)
        })


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    if tool_name != 'Bash':
        sys.exit(0)

    command = input_data.get('tool_input', {}).get('command', '')

    # Only process git commit commands
    if 'git commit' not in command:
        sys.exit(0)

    # Skip if it's just checking status or other non-commit operations
    if 'git commit' not in command or '--dry-run' in command:
        sys.exit(0)

    tool_response = input_data.get('tool_response', {})

    # Handle different response formats
    if isinstance(tool_response, dict):
        exit_code = tool_response.get('exitCode', tool_response.get('exit_code', 1))
        stdout = tool_response.get('stdout', tool_response.get('output', ''))
    else:
        # Response might be a string
        exit_code = 0  # Assume success if we got here
        stdout = str(tool_response)

    # Only log successful commits
    if exit_code != 0:
        sys.exit(0)

    session_id = input_data.get('session_id', '')

    # Extract commit message from command
    commit_msg = extract_commit_message(command)

    # Parse output for SHA and stats
    sha, file_count, insertions, deletions = parse_commit_output(stdout)

    # Determine change type from commit message
    change_type = determine_change_type(commit_msg)

    # Clean up the summary (remove emoji and trailing metadata)
    summary = commit_msg.split('\n')[0][:200]  # First line, max 200 chars

    # Build details
    details = {
        'files_changed': file_count,
        'insertions': insertions,
        'deletions': deletions,
        'source': 'git_commit'
    }

    # Log to Archon
    log_to_archon(change_type, summary, sha, session_id, details)

    sys.exit(0)


if __name__ == '__main__':
    main()
