#!/usr/bin/env python3
"""
PostToolUse hook for logging file changes to Archon.
Triggers on Write and Edit tool completions.

This hook captures file modifications made by Claude Code and logs them
to the Archon change tracking system for audit and changelog generation.

If a pending prompt exists (from UserPromptSubmit hook) without a task,
this hook creates the task first - ensuring only prompts that cause
actual code changes get tracked as tasks.
"""
import json
import sys
import os
import subprocess
import re
from pathlib import Path
from datetime import datetime

# Configuration
ARCHON_API_URL = os.environ.get('ARCHON_API_URL', 'http://localhost:8181')
LOG_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'change-log.jsonl'
SESSION_STATE_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'state' / 'session-state.json'

# Track changes within session to enable aggregation
SESSION_CHANGES: dict = {}


def get_session_state() -> dict:
    """Read current session state to get task_id for linking changes."""
    if SESSION_STATE_FILE.exists():
        try:
            with open(SESSION_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_session_state(state: dict):
    """Save session state."""
    try:
        SESSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass


def summarize_prompt(prompt: str) -> str:
    """Create a short title from the prompt (first 80 chars of first sentence)."""
    first_line = prompt.strip().split('\n')[0]
    first_sentence = re.split(r'[.!?]', first_line)[0].strip()
    if len(first_sentence) > 80:
        return first_sentence[:77] + '...'
    return first_sentence


def create_task_from_pending_prompt(state: dict, project_id: str) -> str | None:
    """Create a task from pending prompt and return task_id."""
    pending_prompt = state.get('pending_prompt')
    if not pending_prompt:
        return None

    title = summarize_prompt(pending_prompt)
    description = f"**User Prompt:**\n\n{pending_prompt}\n\n---\n*Auto-created by Claude Code on first code change*"

    payload = {
        'project_id': project_id,
        'title': title,
        'description': description,
        'assignee': 'Claude',
        'feature': 'agent-session',
        'priority': 'medium'
    }

    try:
        result = subprocess.run(
            [
                'curl', '-s', '-X', 'POST',
                f'{ARCHON_API_URL}/api/tasks',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(payload),
                '--max-time', '10'
            ],
            capture_output=True,
            timeout=15
        )

        if result.returncode == 0:
            response = json.loads(result.stdout)
            task = response.get('task', {})
            task_id = task.get('id')
            if task_id:
                # Update state: set task_id and clear pending prompt
                state['current_task_id'] = task_id
                state['pending_prompt'] = None
                state['pending_prompt_at'] = None
                state['task_created_at'] = datetime.now().isoformat()
                save_session_state(state)

                log_to_file({
                    'timestamp': datetime.now().isoformat(),
                    'event': 'task_created',
                    'task_id': task_id,
                    'title': title
                })
                return task_id
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        log_to_file({
            'timestamp': datetime.now().isoformat(),
            'event': 'task_creation_failed',
            'error': str(e)
        })

    return None


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

    # Get current session state
    session_state = get_session_state()
    task_id = session_state.get('current_task_id')

    # If there's a pending prompt but no task yet, create the task now
    # This ensures tasks are only created for prompts that result in code changes
    if session_state.get('pending_prompt') and not task_id and project_id:
        if config.get('auto_create_tasks', True):
            task_id = create_task_from_pending_prompt(session_state, project_id)

    payload = {
        'change_type': change_type,
        'summary': summary,
        'files_affected': files,
        'session_id': session_id,
        'details': details or {}
    }

    if project_id:
        payload['project_id'] = project_id

    # Link change to current task if available
    if task_id:
        payload['task_id'] = task_id

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
