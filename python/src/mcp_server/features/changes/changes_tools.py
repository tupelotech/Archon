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
VALID_CHANGE_TYPES = ["feature", "bugfix", "refactor", "docs", "config", "test"]

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
        change_type: str,
        summary: str,
        project_id: str | None = None,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> str:
        """
        Log a development change for tracking and changelog generation.

        Use this tool to record significant changes made during a coding session.
        Changes are categorized by type and can be linked to projects.

        Args:
            change_type: Category of change. Must be one of:
                - "feature": New functionality added
                - "bugfix": Bug fixes and corrections
                - "refactor": Code restructuring without behavior changes
                - "docs": Documentation updates
                - "config": Configuration changes
                - "test": Test additions or modifications
            summary: Brief description of what changed (required)
            project_id: Optional UUID of the associated Archon project
            session_id: Optional session identifier for grouping related changes
            details: Optional dict with additional metadata (impact, related issues, etc.)
            files_affected: Optional list of file paths that were modified
            commit_sha: Optional git commit SHA if the change was committed

        Returns:
            JSON with success status and created change entry

        Examples:
            log_change("feature", "Added user authentication with JWT tokens")
            log_change("bugfix", "Fixed null pointer in user service", project_id="p-123")
            log_change("refactor", "Extracted payment logic to separate service",
                      files_affected=["src/payment.py", "src/order.py"])
        """
        try:
            # Validate change type
            if change_type not in VALID_CHANGE_TYPES:
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

            request_data = {
                "change_type": change_type,
                "summary": summary,
            }

            if project_id:
                request_data["project_id"] = project_id
            if session_id:
                request_data["session_id"] = session_id
            if details:
                request_data["details"] = details
            if files_affected:
                request_data["files_affected"] = files_affected
            if commit_sha:
                request_data["commit_sha"] = commit_sha

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    urljoin(api_url, "/api/changes"),
                    json=request_data
                )

                if response.status_code == 200:
                    result = response.json()
                    change = result.get("change", {})

                    return json.dumps({
                        "success": True,
                        "change": optimize_change_response(change),
                        "change_id": change.get("id"),
                        "message": "Change logged successfully",
                    })
                else:
                    return MCPErrorFormatter.from_http_error(response, "log change")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "log change", {"change_type": change_type}
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
    async def get_project_changelog(
        ctx: Context,
        project_id: str,
        format: str = "markdown",
    ) -> str:
        """
        Generate a formatted changelog for a project.

        Creates a changelog in Keep a Changelog format, suitable for
        inclusion in release notes or documentation.

        Args:
            project_id: UUID of the project (required)
            format: Output format - "markdown" (default) or "json"

        Returns:
            JSON with changelog content and metadata

        Examples:
            get_project_changelog(project_id="p-123")  # Markdown changelog
            get_project_changelog(project_id="p-123", format="json")  # Raw JSON
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

            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}/changelog"),
                    params={"format": format}
                )

                if response.status_code == 200:
                    result = response.json()
                    return json.dumps({
                        "success": True,
                        "project_id": project_id,
                        "format": format,
                        "changelog": result.get("changelog"),
                        "changes": result.get("changes"),
                        "count": result.get("count", 0),
                    })
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
