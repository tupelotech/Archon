#!/bin/bash
# SessionStart hook - Load project context and recent changes from Archon
#
# This hook runs when a Claude Code session starts or resumes.
# It fetches recent changes from Archon and injects context about
# the project's development history.

set -e

ARCHON_API="${ARCHON_API_URL:-http://localhost:8181}"
PROJECT_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/archon-project.json"
LOG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/session-init.log"

log_message() {
    echo "$(date -Iseconds) - $1" >> "$LOG_FILE" 2>/dev/null || true
}

# Check if project config exists
if [ ! -f "$PROJECT_FILE" ]; then
    log_message "No archon-project.json found, skipping context load"
    exit 0
fi

# Extract project ID
PROJECT_ID=$(python3 -c "import sys,json; print(json.load(open('$PROJECT_FILE')).get('project_id',''))" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    log_message "No project_id in config, skipping context load"
    exit 0
fi

log_message "Loading context for project: $PROJECT_ID"

# Check if Archon API is available
if ! curl -s --max-time 2 "$ARCHON_API/api/health" > /dev/null 2>&1; then
    log_message "Archon API not available at $ARCHON_API"
    exit 0
fi

# Fetch recent changes
RECENT_CHANGES=$(curl -s --max-time 5 "$ARCHON_API/api/projects/$PROJECT_ID/changes?per_page=5" 2>/dev/null)

if [ -z "$RECENT_CHANGES" ]; then
    log_message "No recent changes or API error"
    exit 0
fi

# Parse change count
CHANGE_COUNT=$(echo "$RECENT_CHANGES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null || echo "0")

if [ "$CHANGE_COUNT" = "0" ]; then
    log_message "No changes recorded for project"
    exit 0
fi

# Fetch in-progress tasks
DOING_TASKS=$(curl -s --max-time 5 "$ARCHON_API/api/tasks?project_id=$PROJECT_ID&status=doing" 2>/dev/null)
DOING_COUNT=$(echo "$DOING_TASKS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('tasks', [])))" 2>/dev/null || echo "0")

# Fetch todo tasks
TODO_TASKS=$(curl -s --max-time 5 "$ARCHON_API/api/tasks?project_id=$PROJECT_ID&status=todo&per_page=3" 2>/dev/null)
TODO_COUNT=$(echo "$TODO_TASKS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_count', 0))" 2>/dev/null || echo "0")

log_message "Loaded: $CHANGE_COUNT changes, $DOING_COUNT in-progress tasks, $TODO_COUNT todo tasks"

# Output context for Claude (JSON format that hooks can return)
cat << EOF
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Archon project context loaded: $CHANGE_COUNT recent changes, $DOING_COUNT in-progress tasks, $TODO_COUNT pending tasks. Use find_tasks() and find_changes() MCP tools to view details."
  }
}
EOF

exit 0
