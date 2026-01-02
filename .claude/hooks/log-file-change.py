#!/usr/bin/env python3
"""
PostToolUse hook for logging file changes to Archon.
Triggers on Write and Edit tool completions.

This hook captures file modifications made by Claude Code and logs them
to the Archon change tracking system for audit and changelog generation.
"""
import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
ARCHON_API_URL = os.environ.get('ARCHON_API_URL', 'http://localhost:8181')
LOG_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'change-log.jsonl'

# Track changes within session to enable aggregation
SESSION_CHANGES: dict = {}


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


def determine_change_type(file_path: str) -> str:
    """Infer change type from file path."""
    path_lower = file_path.lower()
    name = Path(file_path).name.lower()

    # Test files
    if 'test' in path_lower or name.endswith(('_test.py', '.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx')):
        return 'test'

    # Documentation
    if name.endswith('.md') or 'readme' in name or 'docs/' in path_lower or 'documentation' in path_lower:
        return 'docs'

    # Configuration files
    config_extensions = ('.json', '.yaml', '.yml', '.toml', '.ini', '.env', '.config.js', '.config.ts')
    config_names = ('config', 'settings', '.eslintrc', '.prettierrc', 'tsconfig', 'package.json', 'pyproject.toml')
    if name.endswith(config_extensions) or any(cfg in name for cfg in config_names):
        return 'config'

    # Default to feature for code changes
    return 'feature'


def log_to_file(change_data: dict):
    """Append change to local log file for debugging."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(change_data) + '\n')
    except IOError:
        pass


def log_to_archon(change_type: str, summary: str, files: list, session_id: str, details: dict = None):
    """Call Archon API to log the change (non-blocking)."""
    config = get_project_config()
    project_id = config.get('project_id')

    if not config.get('auto_log_changes', True):
        return

    payload = {
        'change_type': change_type,
        'summary': summary,
        'files_affected': files,
        'session_id': session_id,
        'details': details or {}
    }

    if project_id:
        payload['project_id'] = project_id

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
        # Log locally for debugging
        log_to_file({
            'timestamp': datetime.now().isoformat(),
            'payload': payload,
            'response': result.stdout.decode()[:200] if result.stdout else None,
            'success': result.returncode == 0
        })
    except (subprocess.TimeoutExpired, Exception) as e:
        log_to_file({
            'timestamp': datetime.now().isoformat(),
            'payload': payload,
            'error': str(e)
        })


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    tool_response = input_data.get('tool_response', {})
    session_id = input_data.get('session_id', '')

    # Only process Write and Edit tools
    if tool_name not in ('Write', 'Edit'):
        sys.exit(0)

    # Check for successful operation
    # Write tool returns success field, Edit tool may not
    if tool_name == 'Write' and not tool_response.get('success', True):
        sys.exit(0)

    file_path = tool_input.get('file_path', '')
    if not file_path:
        sys.exit(0)

    # Skip logging of log files themselves
    if 'change-log.jsonl' in file_path or '.claude/hooks/' in file_path:
        sys.exit(0)

    # Determine change type and create summary
    change_type = determine_change_type(file_path)
    file_name = Path(file_path).name

    if tool_name == 'Write':
        action = 'Created'
    else:
        # For Edit, check if it's a small or large change
        old_string = tool_input.get('old_string', '')
        new_string = tool_input.get('new_string', '')
        if len(new_string) > len(old_string) * 2:
            action = 'Expanded'
        elif len(new_string) < len(old_string) / 2:
            action = 'Reduced'
        else:
            action = 'Modified'

    summary = f"{action} {file_name}"

    # Add details about the change
    details = {
        'tool': tool_name,
        'action': action.lower()
    }

    if tool_name == 'Edit':
        old_len = len(tool_input.get('old_string', ''))
        new_len = len(tool_input.get('new_string', ''))
        details['chars_changed'] = abs(new_len - old_len)

    # Log to Archon (non-blocking)
    log_to_archon(change_type, summary, [file_path], session_id, details)

    # Return success without blocking
    sys.exit(0)


if __name__ == '__main__':
    main()
