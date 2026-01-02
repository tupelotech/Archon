"""
Change Service Module for Archon

This module provides core business logic for change tracking operations
that can be shared between MCP tools and FastAPI endpoints.

Changes track development modifications made during AI-assisted sessions,
enabling changelog generation and audit trails.
"""

from datetime import datetime
from typing import Any, Literal

from src.server.utils import get_supabase_client

from ..config.logfire_config import get_logger

logger = get_logger(__name__)


# Valid change types matching the database enum
ChangeType = Literal["feature", "bugfix", "refactor", "docs", "config", "test"]
VALID_CHANGE_TYPES: list[ChangeType] = ["feature", "bugfix", "refactor", "docs", "config", "test"]


class ChangeService:
    """Service class for change tracking operations"""

    def __init__(self, supabase_client=None):
        """Initialize with optional supabase client"""
        self.supabase_client = supabase_client or get_supabase_client()

    def validate_change_type(self, change_type: str) -> tuple[bool, str]:
        """Validate change type against allowed enum values"""
        if change_type not in VALID_CHANGE_TYPES:
            return (
                False,
                f"Invalid change_type '{change_type}'. Must be one of: {', '.join(VALID_CHANGE_TYPES)}",
            )
        return True, ""

    def create_change(
        self,
        change_type: str,
        summary: str,
        project_id: str | None = None,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a new change entry.

        Args:
            change_type: Category of change (feature, bugfix, refactor, docs, config, test)
            summary: Brief description of what changed
            project_id: Optional reference to associated project
            session_id: Optional session identifier for grouping related changes
            details: Optional JSONB metadata for additional context
            files_affected: Optional list of file paths that were modified
            commit_sha: Optional git commit SHA if committed

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Validate inputs
            if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
                return False, {"error": "Summary is required and must be a non-empty string"}

            # Validate change type
            is_valid, error_msg = self.validate_change_type(change_type)
            if not is_valid:
                return False, {"error": error_msg}

            change_data = {
                "change_type": change_type,
                "summary": summary.strip(),
                "details": details or {},
                "files_affected": files_affected or [],
                "created_at": datetime.now().isoformat(),
            }

            if project_id:
                change_data["project_id"] = project_id

            if session_id:
                change_data["session_id"] = session_id

            if commit_sha:
                change_data["commit_sha"] = commit_sha

            response = self.supabase_client.table("archon_changes").insert(change_data).execute()

            if response.data:
                change = response.data[0]
                logger.info(
                    f"Change created | id={change['id']} | type={change_type} | "
                    f"project_id={project_id} | summary={summary[:50]}..."
                )
                return True, {"change": change}
            else:
                return False, {"error": "Failed to create change entry"}

        except Exception as e:
            logger.error(f"Error creating change: {e}")
            return False, {"error": f"Error creating change: {str(e)}"}

    def get_change(self, change_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Get a specific change by ID.

        Args:
            change_id: UUID of the change entry

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            response = (
                self.supabase_client.table("archon_changes")
                .select("*")
                .eq("id", change_id)
                .execute()
            )

            if response.data:
                change = response.data[0]
                return True, {"change": change}
            else:
                return False, {"error": f"Change with ID {change_id} not found"}

        except Exception as e:
            logger.error(f"Error getting change: {e}")
            return False, {"error": f"Error getting change: {str(e)}"}

    def list_changes(
        self,
        project_id: str | None = None,
        change_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search_query: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[bool, dict[str, Any]]:
        """
        List changes with optional filters.

        Args:
            project_id: Filter by project
            change_type: Filter by change type
            date_from: Filter by start date (ISO format)
            date_to: Filter by end date (ISO format)
            search_query: Search in summary text
            page: Page number for pagination (1-indexed)
            per_page: Number of results per page

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Start with base query
            query = self.supabase_client.table("archon_changes").select("*")

            # Track filters for debugging
            filters_applied = []

            # Apply filters
            if project_id:
                query = query.eq("project_id", project_id)
                filters_applied.append(f"project_id={project_id}")

            if change_type:
                is_valid, error_msg = self.validate_change_type(change_type)
                if not is_valid:
                    return False, {"error": error_msg}
                query = query.eq("change_type", change_type)
                filters_applied.append(f"change_type={change_type}")

            if date_from:
                query = query.gte("created_at", date_from)
                filters_applied.append(f"date_from={date_from}")

            if date_to:
                query = query.lte("created_at", date_to)
                filters_applied.append(f"date_to={date_to}")

            if search_query:
                query = query.ilike("summary", f"%{search_query}%")
                filters_applied.append(f"search={search_query}")

            logger.debug(f"Listing changes with filters: {', '.join(filters_applied) or 'none'}")

            # Order by created_at descending (newest first)
            query = query.order("created_at", desc=True)

            # Execute query to get total count
            count_response = query.execute()
            total_count = len(count_response.data) if count_response.data else 0

            # Apply pagination
            offset = (page - 1) * per_page
            query = (
                self.supabase_client.table("archon_changes")
                .select("*")
            )

            # Re-apply filters for paginated query
            if project_id:
                query = query.eq("project_id", project_id)
            if change_type:
                query = query.eq("change_type", change_type)
            if date_from:
                query = query.gte("created_at", date_from)
            if date_to:
                query = query.lte("created_at", date_to)
            if search_query:
                query = query.ilike("summary", f"%{search_query}%")

            response = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )

            changes = response.data if response.data else []

            return True, {
                "changes": changes,
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": (total_count + per_page - 1) // per_page if total_count > 0 else 0,
                "filters_applied": ", ".join(filters_applied) if filters_applied else "none",
            }

        except Exception as e:
            logger.error(f"Error listing changes: {e}")
            return False, {"error": f"Error listing changes: {str(e)}"}

    def delete_change(self, change_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Delete a change entry.

        Args:
            change_id: UUID of the change to delete

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # First check if change exists
            check_response = (
                self.supabase_client.table("archon_changes")
                .select("id")
                .eq("id", change_id)
                .execute()
            )

            if not check_response.data:
                return False, {"error": f"Change with ID {change_id} not found"}

            # Delete the change
            response = (
                self.supabase_client.table("archon_changes")
                .delete()
                .eq("id", change_id)
                .execute()
            )

            if response.data:
                logger.info(f"Change deleted | id={change_id}")
                return True, {"message": f"Change {change_id} deleted successfully"}
            else:
                return False, {"error": f"Failed to delete change {change_id}"}

        except Exception as e:
            logger.error(f"Error deleting change: {e}")
            return False, {"error": f"Error deleting change: {str(e)}"}

    def get_project_changelog(
        self,
        project_id: str,
        format_type: str = "markdown",
    ) -> tuple[bool, dict[str, Any]]:
        """
        Generate a formatted changelog for a project.

        Args:
            project_id: UUID of the project
            format_type: Output format ("markdown" or "json")

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Get all changes for the project, ordered by date descending
            response = (
                self.supabase_client.table("archon_changes")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at", desc=True)
                .execute()
            )

            changes = response.data if response.data else []

            if format_type == "json":
                return True, {
                    "project_id": project_id,
                    "format": "json",
                    "changes": changes,
                    "count": len(changes),
                }

            # Format as markdown (Keep a Changelog style)
            lines = ["# Changelog", "", "All notable changes to this project.", ""]

            # Group changes by date
            changes_by_date: dict[str, list[dict]] = {}
            for change in changes:
                date_str = change["created_at"][:10]  # Extract YYYY-MM-DD
                if date_str not in changes_by_date:
                    changes_by_date[date_str] = []
                changes_by_date[date_str].append(change)

            # Format each date section
            for date_str in sorted(changes_by_date.keys(), reverse=True):
                lines.append(f"## [{date_str}]")
                lines.append("")

                date_changes = changes_by_date[date_str]

                # Group by type within each date
                by_type: dict[str, list[dict]] = {}
                for change in date_changes:
                    ctype = change["change_type"]
                    if ctype not in by_type:
                        by_type[ctype] = []
                    by_type[ctype].append(change)

                # Output in standard order
                type_labels = {
                    "feature": "Added",
                    "bugfix": "Fixed",
                    "refactor": "Changed",
                    "docs": "Documentation",
                    "config": "Configuration",
                    "test": "Tests",
                }

                for ctype in ["feature", "bugfix", "refactor", "docs", "config", "test"]:
                    if ctype in by_type:
                        lines.append(f"### {type_labels.get(ctype, ctype.title())}")
                        for change in by_type[ctype]:
                            summary = change["summary"]
                            commit = change.get("commit_sha")
                            if commit:
                                lines.append(f"- {summary} ({commit[:7]})")
                            else:
                                lines.append(f"- {summary}")
                        lines.append("")

            markdown = "\n".join(lines)

            return True, {
                "project_id": project_id,
                "format": "markdown",
                "changelog": markdown,
                "count": len(changes),
            }

        except Exception as e:
            logger.error(f"Error generating changelog: {e}")
            return False, {"error": f"Error generating changelog: {str(e)}"}
