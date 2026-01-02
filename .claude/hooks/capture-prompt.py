#!/usr/bin/env python3
"""
UserPromptSubmit hook for capturing user prompts.

This hook stores substantive user prompts in session state. A task is NOT
created here - it's only created later if the prompt results in code changes.
This ensures only prompts that cause actual file modifications get tracked.
"""
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Configuration
SESSION_STATE_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'state' / 'session-state.json'
LOG_FILE = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / '.claude' / 'prompt-log.jsonl'

# Minimum prompt length to track (filters out "yes", "ok", etc.)
MIN_PROMPT_LENGTH = 20

# Patterns that indicate trivial prompts (even if long enough)
TRIVIAL_PATTERNS = [
    r'^(yes|no|ok|okay|sure|yep|nope|done|thanks|thank you|y|n)[\s.,!?]*$',
    r'^(please )?continue[\s.,!?]*$',
    r'^(go ahead|proceed|confirm|approved?)[\s.,!?]*$',
    r'^(looks good|lgtm|sounds good)[\s.,!?]*$',
]


def log_debug(message: str, data: dict = None):
    """Append to debug log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            entry = {'timestamp': datetime.now().isoformat(), 'message': message}
            if data:
                entry['data'] = data
            f.write(json.dumps(entry) + '\n')
    except IOError:
        pass


def get_session_state() -> dict:
    """Read current session state."""
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
    except IOError as e:
        log_debug(f'Failed to save session state: {e}')


def is_trivial_prompt(prompt: str) -> bool:
    """Check if prompt is too trivial to track."""
    if len(prompt.strip()) < MIN_PROMPT_LENGTH:
        return True

    prompt_lower = prompt.strip().lower()
    for pattern in TRIVIAL_PATTERNS:
        if re.match(pattern, prompt_lower, re.IGNORECASE):
            return True

    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get('prompt', '')
    session_id = input_data.get('session_id', '')

    # Skip trivial prompts
    if is_trivial_prompt(prompt):
        log_debug('Skipping trivial prompt', {'prompt_preview': prompt[:50]})
        sys.exit(0)

    # Get current session state
    state = get_session_state()

    # Store the pending prompt - task will be created on first file change
    state['pending_prompt'] = prompt
    state['pending_prompt_at'] = datetime.now().isoformat()
    state['session_id'] = session_id
    save_session_state(state)

    log_debug('Stored pending prompt', {'prompt_preview': prompt[:80]})

    sys.exit(0)


if __name__ == '__main__':
    main()
