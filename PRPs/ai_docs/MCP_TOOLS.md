# MCP Tools Reference

When connected to Claude Code, Cursor, Windsurf, or other MCP-compatible clients, these tools are available:

## Knowledge Base Tools

- `archon:rag_search_knowledge_base` - Search knowledge base for relevant content
- `archon:rag_search_code_examples` - Find code snippets in the knowledge base
- `archon:rag_get_available_sources` - List available knowledge sources
- `archon:rag_list_pages_for_source` - List all pages for a given source (browse documentation structure)
- `archon:rag_read_full_page` - Retrieve full page content by page_id or URL

## Project Management

- `archon:find_projects` - Find all projects, search, or get specific project (by project_id)
- `archon:manage_project` - Manage projects with actions: "create", "update", "delete"

## Task Management

- `archon:find_tasks` - Find tasks with search, filters, or get specific task (by task_id)
- `archon:manage_task` - Manage tasks with actions: "create", "update", "delete"

## Document Management

- `archon:find_documents` - Find documents, search, or get specific document (by document_id)
- `archon:manage_document` - Manage documents with actions: "create", "update", "delete"

## Version Control

- `archon:find_versions` - Find version history or get specific version
- `archon:manage_version` - Manage versions with actions: "create", "restore"

## User Preferences

**IMPORTANT**: AI agents should call `get_user_preferences` at the start of each session to understand user-specific settings.

- `archon:get_user_preferences` - Retrieve all user preferences (document format, agent instructions, etc.)
- `archon:manage_user_preference` - Set or delete preferences with actions: "set", "delete"

Common preferences:
- `DOCUMENT_FORMAT` - Preferred format for documents (e.g., "markdown")
- `AGENT_INSTRUCTIONS` - Custom instructions for AI agents

## Change Tracking

Track development changes made during AI-assisted coding sessions for changelog generation and auditing.

- `archon:log_change` - Record a new change entry (category auto-detected from summary/files)
  - Args: summary (required), change_type (optional - auto-detected), project_id, task_id, session_id, details, files_affected, commit_sha, sub_category
  - Change types: "feature", "bugfix", "refactor", "docs", "config", "test", "style", "perf", "deps", "ci"
  - Note: `task_id` links changes to tasks for grouped changelog view
- `archon:find_changes` - Search and filter changes, or get specific change by ID
  - Args: change_id, project_id, change_type, query, date_from, date_to, page, per_page
- `archon:manage_change` - Update or delete changes
  - Args: action ("update" | "delete"), change_id, project_id, task_id, summary, files_affected, commit_sha, change_type, sub_category
- `archon:get_project_changelog` - Generate formatted changelog for a project
  - Args: project_id (required), format ("markdown" or "json")
- `archon:suggest_category` - Get category suggestion based on file patterns and commit message
  - Args: file_paths, commit_message, tool_context

Example usage:
```
# Log a change - category auto-detected
log_change("Added user authentication with JWT", project_id="p-123")

# Log with explicit category and task link
log_change("Fixed null pointer in user service", change_type="bugfix",
           task_id="t-456", files_affected=["src/user.py"])

# Find all bug fixes for a project
find_changes(project_id="p-123", change_type="bugfix")

# Generate markdown changelog
get_project_changelog(project_id="p-123", format="markdown")
```

## Tool Naming Patterns

MCP tools follow consistent naming:
- `find_[resource]` - Handles list, search, and get single item operations
- `manage_[resource]` - Handles create, update, delete with an "action" parameter

## Tool Implementation

Tools are located in `python/src/mcp_server/features/[feature]/[feature]_tools.py` and registered in each feature's `__init__.py` file.
