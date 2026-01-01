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

## Tool Naming Patterns

MCP tools follow consistent naming:
- `find_[resource]` - Handles list, search, and get single item operations
- `manage_[resource]` - Handles create, update, delete with an "action" parameter

## Tool Implementation

Tools are located in `python/src/mcp_server/features/[feature]/[feature]_tools.py` and registered in each feature's `__init__.py` file.
