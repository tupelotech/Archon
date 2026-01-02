"""
Consolidated change tracking tools for Archon MCP Server.

Provides tools for logging and querying development changes made during
AI-assisted coding sessions.
"""

import json
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from mcp.server.fastmcp import Context, FastMCP

from src.mcp_server.utils.error_handling import MCPErrorFormatter
from src.mcp_server.utils.timeout_config import get_default_timeout
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)

# Valid change types
VALID_CHANGE_TYPES = ["feature", "bugfix", "refactor", "docs", "config", "test", "style", "perf", "deps", "ci"]

# Optimization constants
MAX_SUMMARY_LENGTH = 500
DEFAULT_PAGE_SIZE = 10


def truncate_text(text: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
    """Truncate text to maximum length with ellipsis."""
    if text and len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def optimize_change_response(change: dict) -> dict:
    """Optimize change object for MCP response."""
    change = change.copy()

    # Truncate summary if needed
    if "summary" in change and change["summary"]:
        change["summary"] = truncate_text(change["summary"])

    return change


def register_changes_tools(mcp: FastMCP):
    """Register change tracking tools with the MCP server."""

    @mcp.tool()
    async def log_change(
        ctx: Context,
        summary: str,
        change_type: str | None = None,
        project_id: str | None = None,
        task_id: str | None = None,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
        sub_category: str | None = None,
    ) -> str:
        """
        Log a development change for tracking and changelog generation.

        Use this tool to record significant changes made during a coding session.
        The category is automatically detected from the summary and files - you
        don't need to specify change_type unless you want to override.

        Args:
            summary: Brief description of what changed (required)
            change_type: Optional category override. If not provided, auto-detected.
                Valid types: feature, bugfix, refactor, docs, config, test, style, perf, deps, ci
            project_id: Optional UUID of the associated Archon project
            task_id: Optional UUID of the associated task (for changelog grouping by task)
            session_id: Optional session identifier for grouping related changes
            details: Optional dict with additional metadata (impact, related issues, etc.)
            files_affected: Optional list of file paths that were modified (improves auto-detection)
            commit_sha: Optional git commit SHA if the change was committed
            sub_category: Optional sub-category for granular classification (e.g., "ui", "api", "database")

        Returns:
            JSON with success status and created change entry (includes auto-detected category)

        Examples:
            log_change("Added user authentication with JWT tokens")  # Auto-detects "feature"
            log_change("Fixed null pointer in user service")  # Auto-detects "bugfix"
            log_change("Extracted payment logic", files_affected=["src/payment.py"])
            log_change("Updated README", change_type="docs")  # Explicit override
            log_change("Implemented login form", task_id="task-uuid")  # Link to task
        """
        try:
            # Validate change type if provided
            if change_type and change_type not in VALID_CHANGE_TYPES:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message=f"Invalid change_type '{change_type}'",
                    suggestion=f"Must be one of: {', '.join(VALID_CHANGE_TYPES)}"
                )

            if not summary or not summary.strip():
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="Summary is required",
                    suggestion="Provide a brief description of the change"
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            request_data: dict[str, Any] = {
                "summary": summary,
            }

            # Only include change_type if explicitly provided (otherwise API auto-detects)
            if change_type:
                request_data["change_type"] = change_type
            if project_id:
                request_data["project_id"] = project_id
            if task_id:
                request_data["task_id"] = task_id
            if session_id:
                request_data["session_id"] = session_id
            if details:
                request_data["details"] = details
            if files_affected:
                request_data["files_affected"] = files_affected
            if commit_sha:
                request_data["commit_sha"] = commit_sha
            if sub_category:
                request_data["sub_category"] = sub_category

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    urljoin(api_url, "/api/changes"),
                    json=request_data
                )

                if response.status_code == 200:
                    result = response.json()
                    change = result.get("change", {})

                    # Include detection info in response
                    response_data = {
                        "success": True,
                        "change": optimize_change_response(change),
                        "change_id": change.get("id"),
                        "message": "Change logged successfully",
                    }

                    # Add auto-detection info if applicable
                    change_details = change.get("details", {})
                    if change_details.get("auto_detected"):
                        response_data["auto_detected"] = True
                        response_data["detected_type"] = change.get("change_type")
                        response_data["confidence"] = change_details.get("detection_confidence")

                    return json.dumps(response_data)
                else:
                    return MCPErrorFormatter.from_http_error(response, "log change")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "log change", {"summary": summary[:50] if summary else None}
            )
        except Exception as e:
            logger.error(f"Error logging change: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "log change")

    @mcp.tool()
    async def find_changes(
        ctx: Context,
        change_id: str | None = None,
        project_id: str | None = None,
        change_type: str | None = None,
        query: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> str:
        """
        Find and search changes (consolidated: list + search + get).

        Args:
            change_id: Get specific change by ID (returns full details)
            project_id: Filter by project UUID
            change_type: Filter by type (feature, bugfix, refactor, docs, config, test)
            query: Search in summary text
            date_from: Filter by start date (YYYY-MM-DD)
            date_to: Filter by end date (YYYY-MM-DD)
            page: Page number for pagination (1-indexed)
            per_page: Items per page (default: 10)

        Returns:
            JSON array of changes or single change (optimized payloads for lists)

        Examples:
            find_changes()  # All changes
            find_changes(change_id="c-123")  # Get specific change
            find_changes(project_id="p-123")  # Changes for a project
            find_changes(change_type="bugfix")  # All bug fixes
            find_changes(query="authentication")  # Search changes
        """
        try:
            api_url = get_api_url()
            timeout = get_default_timeout()

            # Single change get mode
            if change_id:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        urljoin(api_url, f"/api/changes/{change_id}")
                    )

                    if response.status_code == 200:
                        change = response.json()
                        return json.dumps({"success": True, "change": change})
                    elif response.status_code == 404:
                        return MCPErrorFormatter.format_error(
                            error_type="not_found",
                            message=f"Change {change_id} not found",
                            suggestion="Verify the change ID is correct",
                            http_status=404,
                        )
                    else:
                        return MCPErrorFormatter.from_http_error(response, "get change")

            # List mode with filters
            params: dict[str, Any] = {
                "page": page,
                "per_page": per_page,
            }

            if project_id:
                params["project_id"] = project_id
            if change_type:
                if change_type not in VALID_CHANGE_TYPES:
                    return MCPErrorFormatter.format_error(
                        error_type="validation_error",
                        message=f"Invalid change_type '{change_type}'",
                        suggestion=f"Must be one of: {', '.join(VALID_CHANGE_TYPES)}"
                    )
                params["change_type"] = change_type
            if query:
                params["q"] = query
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    urljoin(api_url, "/api/changes"),
                    params=params
                )
                response.raise_for_status()

                result = response.json()

                changes = result.get("changes", [])
                total_count = result.get("total_count", len(changes))

                # Optimize change responses
                optimized_changes = [optimize_change_response(c) for c in changes]

                return json.dumps({
                    "success": True,
                    "changes": optimized_changes,
                    "total_count": total_count,
                    "count": len(optimized_changes),
                    "page": page,
                    "per_page": per_page,
                })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "find changes", {"project_id": project_id, "change_type": change_type}
            )
        except Exception as e:
            logger.error(f"Error finding changes: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "find changes")

    @mcp.tool()
    async def manage_change(
        ctx: Context,
        action: str,
        change_id: str | None = None,
        project_id: str | None = None,
        task_id: str | None = None,
        summary: str | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
        change_type: str | None = None,
        sub_category: str | None = None,
    ) -> str:
        """
        Manage changes (update or delete).

        Use log_change() for creating new changes.

        Args:
            action: "update" | "delete"
            change_id: Change UUID (required for both actions)
            project_id: New project association (for update)
            task_id: New task association (for update - enables changelog grouping)
            summary: Updated summary text (for update)
            files_affected: Updated list of files (for update)
            commit_sha: Updated commit SHA (for update)
            change_type: Updated change type (for update)
            sub_category: Updated sub-category (for update)

        Returns:
            JSON with success status and updated/deleted change info

        Examples:
            manage_change("update", change_id="c-123", project_id="p-456")
            manage_change("update", change_id="c-123", task_id="t-789")  # Link to task
            manage_change("update", change_id="c-123", summary="Updated description")
            manage_change("update", change_id="c-123", change_type="bugfix", sub_category="ui")
            manage_change("delete", change_id="c-123")
        """
        try:
            if action not in ["update", "delete"]:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message=f"Invalid action '{action}'",
                    suggestion="Must be 'update' or 'delete'"
                )

            if not change_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="change_id is required",
                    suggestion="Provide the UUID of the change to manage"
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                if action == "delete":
                    response = await client.delete(
                        urljoin(api_url, f"/api/changes/{change_id}")
                    )

                    if response.status_code == 200:
                        return json.dumps({
                            "success": True,
                            "message": f"Change {change_id} deleted successfully",
                        })
                    elif response.status_code == 404:
                        return MCPErrorFormatter.format_error(
                            error_type="not_found",
                            message=f"Change {change_id} not found",
                            http_status=404,
                        )
                    else:
                        return MCPErrorFormatter.from_http_error(response, "delete change")

                else:  # update
                    update_data: dict[str, Any] = {}

                    if project_id is not None:
                        update_data["project_id"] = project_id
                    if task_id is not None:
                        update_data["task_id"] = task_id
                    if summary is not None:
                        update_data["summary"] = summary
                    if files_affected is not None:
                        update_data["files_affected"] = files_affected
                    if commit_sha is not None:
                        update_data["commit_sha"] = commit_sha
                    if change_type is not None:
                        if change_type not in VALID_CHANGE_TYPES:
                            return MCPErrorFormatter.format_error(
                                error_type="validation_error",
                                message=f"Invalid change_type '{change_type}'",
                                suggestion=f"Must be one of: {', '.join(VALID_CHANGE_TYPES)}"
                            )
                        update_data["change_type"] = change_type
                    if sub_category is not None:
                        update_data["sub_category"] = sub_category

                    if not update_data:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="No fields to update",
                            suggestion="Provide at least one field to update"
                        )

                    response = await client.put(
                        urljoin(api_url, f"/api/changes/{change_id}"),
                        json=update_data
                    )

                    if response.status_code == 200:
                        result = response.json()
                        change = result.get("change", {})
                        return json.dumps({
                            "success": True,
                            "change": optimize_change_response(change),
                            "message": "Change updated successfully",
                        })
                    elif response.status_code == 404:
                        return MCPErrorFormatter.format_error(
                            error_type="not_found",
                            message=f"Change {change_id} not found",
                            http_status=404,
                        )
                    else:
                        return MCPErrorFormatter.from_http_error(response, "update change")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, f"{action} change", {"change_id": change_id}
            )
        except Exception as e:
            logger.error(f"Error managing change: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, f"{action} change")

    @mcp.tool()
    async def get_project_changelog(
        ctx: Context,
        project_id: str,
        format: str = "markdown",
        group_by: str = "date",
    ) -> str:
        """
        Generate a formatted changelog for a project.

        Creates a changelog in Keep a Changelog format, suitable for
        inclusion in release notes or documentation.

        Args:
            project_id: UUID of the project (required)
            format: Output format - "markdown" (default) or "json"
            group_by: Grouping strategy - "date" (default) or "task"
                      Use "task" to see changes grouped by linked tasks

        Returns:
            JSON with changelog content and metadata

        Examples:
            get_project_changelog(project_id="p-123")  # Markdown changelog by date
            get_project_changelog(project_id="p-123", format="json")  # Raw JSON
            get_project_changelog(project_id="p-123", group_by="task")  # Group by task
        """
        try:
            if not project_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="project_id is required",
                    suggestion="Provide the UUID of the project"
                )

            if format not in ["markdown", "json"]:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message=f"Invalid format '{format}'",
                    suggestion="Must be 'markdown' or 'json'"
                )

            if group_by not in ["date", "task"]:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message=f"Invalid group_by '{group_by}'",
                    suggestion="Must be 'date' or 'task'"
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}/changelog"),
                    params={"format": format, "group_by": group_by}
                )

                if response.status_code == 200:
                    result = response.json()
                    response_data = {
                        "success": True,
                        "project_id": project_id,
                        "format": format,
                        "group_by": group_by,
                        "count": result.get("count", 0),
                    }

                    # Include either changelog (markdown) or grouped/changes (json)
                    if result.get("changelog"):
                        response_data["changelog"] = result.get("changelog")
                    if result.get("grouped"):
                        response_data["grouped"] = result.get("grouped")
                    if result.get("changes"):
                        response_data["changes"] = result.get("changes")

                    return json.dumps(response_data)
                elif response.status_code == 404:
                    return MCPErrorFormatter.format_error(
                        error_type="not_found",
                        message=f"Project {project_id} not found",
                        suggestion="Verify the project ID is correct",
                        http_status=404,
                    )
                else:
                    return MCPErrorFormatter.from_http_error(response, "get changelog")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "get changelog", {"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Error getting changelog: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "get changelog")

    @mcp.tool()
    async def suggest_category(
        ctx: Context,
        file_paths: list[str] | None = None,
        commit_message: str | None = None,
        tool_context: dict[str, Any] | None = None,
    ) -> str:
        """
        Suggest a category for a change based on file patterns and commit message.

        Analyzes file paths, commit message, and tool context to suggest
        the most appropriate change category with a confidence score.

        Args:
            file_paths: List of file paths that were modified
            commit_message: The commit message or change summary
            tool_context: Optional context from the tool being used (e.g., {"tool_name": "test"})

        Returns:
            JSON with suggested category, sub_category, confidence score, and reasoning

        Examples:
            suggest_category(file_paths=["tests/test_auth.py"])  # Suggests "test"
            suggest_category(commit_message="fix: resolve null pointer bug")  # Suggests "bugfix"
            suggest_category(file_paths=["src/components/Button.tsx"], commit_message="feat: add button")
        """
        try:
            if not file_paths and not commit_message and not tool_context:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="At least one input is required",
                    suggestion="Provide file_paths, commit_message, or tool_context"
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            request_data: dict[str, Any] = {}
            if file_paths:
                request_data["file_paths"] = file_paths
            if commit_message:
                request_data["commit_message"] = commit_message
            if tool_context:
                request_data["tool_context"] = tool_context

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    urljoin(api_url, "/api/changes/suggest-category"),
                    json=request_data
                )

                if response.status_code == 200:
                    result = response.json()
                    return json.dumps({
                        "success": True,
                        "category": result.get("category"),
                        "sub_category": result.get("sub_category"),
                        "confidence": result.get("confidence"),
                        "reasoning": result.get("reasoning"),
                        "signals": result.get("signals", []),
                    })
                else:
                    return MCPErrorFormatter.from_http_error(response, "suggest category")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(e, "suggest category")
        except Exception as e:
            logger.error(f"Error suggesting category: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "suggest category")
