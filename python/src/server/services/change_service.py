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
ChangeType = Literal["feature", "bugfix", "refactor", "docs", "config", "test", "style", "perf", "deps", "ci"]
VALID_CHANGE_TYPES: list[ChangeType] = [
    "feature", "bugfix", "refactor", "docs", "config", "test", "style", "perf", "deps", "ci"
]


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
        task_id: str | None = None,
        session_id: str | None = None,
        details: dict[str, Any] | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
        sub_category: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a new change entry.

        Args:
            change_type: Category of change (feature, bugfix, refactor, docs, config, test, style, perf, deps, ci)
            summary: Brief description of what changed
            project_id: Optional reference to associated project
            task_id: Optional reference to associated task (for changelog grouping)
            session_id: Optional session identifier for grouping related changes
            details: Optional JSONB metadata for additional context (includes auto_detected_type, confidence_score)
            files_affected: Optional list of file paths that were modified
            commit_sha: Optional git commit SHA if committed
            sub_category: Optional sub-category for granular classification

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

            if task_id:
                change_data["task_id"] = task_id

            if session_id:
                change_data["session_id"] = session_id

            if commit_sha:
                change_data["commit_sha"] = commit_sha

            if sub_category:
                change_data["sub_category"] = sub_category

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

    def update_change(
        self,
        change_id: str,
        project_id: str | None = None,
        task_id: str | None = None,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
        files_affected: list[str] | None = None,
        commit_sha: str | None = None,
        change_type: str | None = None,
        sub_category: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Update an existing change entry.

        Args:
            change_id: UUID of the change to update
            project_id: New project association (can set or clear)
            task_id: New task association (can set or clear)
            summary: Updated summary text
            details: Updated metadata
            files_affected: Updated list of files
            commit_sha: Updated commit SHA
            change_type: Updated change type
            sub_category: Updated sub-category

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # First check if change exists
            check_response = (
                self.supabase_client.table("archon_changes")
                .select("*")
                .eq("id", change_id)
                .execute()
            )

            if not check_response.data:
                return False, {"error": f"Change with ID {change_id} not found"}

            # Build update data - only include fields that were provided
            update_data: dict[str, Any] = {}

            if project_id is not None:
                update_data["project_id"] = project_id

            if task_id is not None:
                update_data["task_id"] = task_id

            if summary is not None:
                if not summary.strip():
                    return False, {"error": "Summary cannot be empty"}
                update_data["summary"] = summary.strip()

            if details is not None:
                update_data["details"] = details

            if files_affected is not None:
                update_data["files_affected"] = files_affected

            if commit_sha is not None:
                update_data["commit_sha"] = commit_sha

            if change_type is not None:
                is_valid, error_msg = self.validate_change_type(change_type)
                if not is_valid:
                    return False, {"error": error_msg}
                update_data["change_type"] = change_type

            if sub_category is not None:
                update_data["sub_category"] = sub_category

            if not update_data:
                return False, {"error": "No fields to update"}

            response = (
                self.supabase_client.table("archon_changes")
                .update(update_data)
                .eq("id", change_id)
                .execute()
            )

            if response.data:
                change = response.data[0]
                logger.info(f"Change updated | id={change_id} | fields={list(update_data.keys())}")
                return True, {"change": change}
            else:
                return False, {"error": f"Failed to update change {change_id}"}

        except Exception as e:
            logger.error(f"Error updating change: {e}")
            return False, {"error": f"Error updating change: {str(e)}"}

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
        group_by: str = "date",
    ) -> tuple[bool, dict[str, Any]]:
        """
        Generate a formatted changelog for a project.

        Args:
            project_id: UUID of the project
            format_type: Output format ("markdown" or "json")
            group_by: Grouping strategy ("date" or "task")

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

            # For task grouping, fetch task details
            tasks_map: dict[str, dict] = {}
            if group_by == "task":
                task_ids = list(set(c.get("task_id") for c in changes if c.get("task_id")))
                if task_ids:
                    tasks_response = (
                        self.supabase_client.table("archon_tasks")
                        .select("id, title, status, feature")
                        .in_("id", task_ids)
                        .execute()
                    )
                    if tasks_response.data:
                        tasks_map = {t["id"]: t for t in tasks_response.data}

            if format_type == "json":
                # For JSON format with task grouping, structure by task
                if group_by == "task":
                    grouped: dict[str, Any] = {"tasks": [], "unlinked": []}
                    by_task: dict[str, list[dict]] = {}

                    for change in changes:
                        task_id = change.get("task_id")
                        if task_id:
                            if task_id not in by_task:
                                by_task[task_id] = []
                            by_task[task_id].append(change)
                        else:
                            grouped["unlinked"].append(change)

                    for task_id, task_changes in by_task.items():
                        task_info = tasks_map.get(task_id, {"id": task_id, "title": "Unknown Task"})
                        # Collect all files affected across all changes for this task
                        all_files = []
                        for c in task_changes:
                            all_files.extend(c.get("files_affected", []))

                        grouped["tasks"].append({
                            "task": task_info,
                            "changes": task_changes,
                            "files_affected": list(set(all_files)),
                            "change_count": len(task_changes),
                        })

                    return True, {
                        "project_id": project_id,
                        "format": "json",
                        "group_by": "task",
                        "grouped": grouped,
                        "count": len(changes),
                    }

                return True, {
                    "project_id": project_id,
                    "format": "json",
                    "group_by": "date",
                    "changes": changes,
                    "count": len(changes),
                }

            # Format as markdown
            lines = ["# Changelog", "", "All notable changes to this project.", ""]

            if group_by == "task":
                # Group by task
                by_task: dict[str, list[dict]] = {}
                unlinked: list[dict] = []

                for change in changes:
                    task_id = change.get("task_id")
                    if task_id:
                        if task_id not in by_task:
                            by_task[task_id] = []
                        by_task[task_id].append(change)
                    else:
                        unlinked.append(change)

                # Output tasks (sorted by most recent change)
                task_order = sorted(
                    by_task.keys(),
                    key=lambda tid: max(c["created_at"] for c in by_task[tid]),
                    reverse=True
                )

                for task_id in task_order:
                    task_changes = by_task[task_id]
                    task_info = tasks_map.get(task_id, {})
                    task_title = task_info.get("title", "Unknown Task")
                    task_status = task_info.get("status", "")

                    # Get all files affected
                    all_files = []
                    for c in task_changes:
                        all_files.extend(c.get("files_affected", []))
                    unique_files = list(set(all_files))

                    lines.append(f"## {task_title}")
                    if task_status:
                        lines.append(f"**Status:** {task_status}")
                    lines.append(f"**Changes:** {len(task_changes)} | **Files:** {len(unique_files)}")
                    lines.append("")

                    # List changes under this task
                    for change in task_changes:
                        summary = change["summary"]
                        ctype = change.get("change_type", "")
                        lines.append(f"- [{ctype}] {summary}")
                    lines.append("")

                    # List files
                    if unique_files:
                        lines.append("<details><summary>Files affected</summary>")
                        lines.append("")
                        for f in sorted(unique_files):
                            lines.append(f"- `{f}`")
                        lines.append("")
                        lines.append("</details>")
                        lines.append("")

                # Output unlinked changes
                if unlinked:
                    lines.append("## Other Changes")
                    lines.append("")
                    for change in unlinked:
                        summary = change["summary"]
                        ctype = change.get("change_type", "")
                        lines.append(f"- [{ctype}] {summary}")
                    lines.append("")

            else:
                # Original date-based grouping
                changes_by_date: dict[str, list[dict]] = {}
                for change in changes:
                    date_str = change["created_at"][:10]
                    if date_str not in changes_by_date:
                        changes_by_date[date_str] = []
                    changes_by_date[date_str].append(change)

                type_labels = {
                    "feature": "Added",
                    "bugfix": "Fixed",
                    "refactor": "Changed",
                    "docs": "Documentation",
                    "config": "Configuration",
                    "test": "Tests",
                    "style": "Style",
                    "perf": "Performance",
                    "deps": "Dependencies",
                    "ci": "CI/CD",
                }

                for date_str in sorted(changes_by_date.keys(), reverse=True):
                    lines.append(f"## [{date_str}]")
                    lines.append("")

                    date_changes = changes_by_date[date_str]
                    by_type: dict[str, list[dict]] = {}
                    for change in date_changes:
                        ctype = change["change_type"]
                        if ctype not in by_type:
                            by_type[ctype] = []
                        by_type[ctype].append(change)

                    for ctype in VALID_CHANGE_TYPES:
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
                "group_by": group_by,
                "changelog": markdown,
                "count": len(changes),
            }

        except Exception as e:
            logger.error(f"Error generating changelog: {e}")
            return False, {"error": f"Error generating changelog: {str(e)}"}

    def get_stats(
        self,
        project_id: str | None = None,
        days: int = 30,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Get change statistics for dashboard and analytics.

        Args:
            project_id: Optional filter by project
            days: Number of days to include in trends (default 30)

        Returns:
            Tuple of (success, result_dict) with:
            - by_type: Count of changes per type
            - by_week: Count of changes per week
            - by_project: Count of changes per project (if no project_id filter)
            - total: Total change count
        """
        try:
            from datetime import timedelta

            # Calculate date range
            now = datetime.now()
            start_date = (now - timedelta(days=days)).isoformat()

            # Base query with date filter
            query = (
                self.supabase_client.table("archon_changes")
                .select("id, change_type, project_id, created_at")
                .gte("created_at", start_date)
            )

            if project_id:
                query = query.eq("project_id", project_id)

            response = query.order("created_at", desc=True).execute()
            changes = response.data if response.data else []

            # Calculate by_type
            by_type: dict[str, int] = {}
            for change_type in VALID_CHANGE_TYPES:
                by_type[change_type] = 0

            for change in changes:
                ctype = change.get("change_type")
                if ctype in by_type:
                    by_type[ctype] += 1

            # Calculate by_week
            by_week: list[dict[str, Any]] = []
            week_counts: dict[str, int] = {}

            for change in changes:
                change_date = datetime.fromisoformat(change["created_at"].replace("Z", "+00:00"))
                # Get Monday of that week
                week_start = change_date - timedelta(days=change_date.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                week_counts[week_key] = week_counts.get(week_key, 0) + 1

            # Sort weeks and format
            for week_key in sorted(week_counts.keys()):
                by_week.append({
                    "week": week_key,
                    "count": week_counts[week_key],
                })

            # Calculate by_project (only if not filtering by project)
            by_project: list[dict[str, Any]] = []
            if not project_id:
                project_counts: dict[str, int] = {}
                for change in changes:
                    pid = change.get("project_id")
                    if pid:
                        project_counts[pid] = project_counts.get(pid, 0) + 1
                    else:
                        project_counts["unassigned"] = project_counts.get("unassigned", 0) + 1

                # Sort by count descending
                for pid, count in sorted(project_counts.items(), key=lambda x: x[1], reverse=True):
                    by_project.append({
                        "project_id": pid if pid != "unassigned" else None,
                        "count": count,
                    })

            # Calculate recent trend (last 7 days vs previous 7 days)
            seven_days_ago = now - timedelta(days=7)
            fourteen_days_ago = now - timedelta(days=14)

            current_week = 0
            previous_week = 0

            for change in changes:
                change_date = datetime.fromisoformat(change["created_at"].replace("Z", "+00:00"))
                # Make comparison timezone-naive
                change_date_naive = change_date.replace(tzinfo=None)
                if change_date_naive >= seven_days_ago:
                    current_week += 1
                elif change_date_naive >= fourteen_days_ago:
                    previous_week += 1

            percent_change = (
                100 if previous_week == 0 and current_week > 0
                else 0 if previous_week == 0
                else round(((current_week - previous_week) / previous_week) * 100)
            )

            result = {
                "by_type": by_type,
                "by_week": by_week,
                "by_project": by_project,
                "total": len(changes),
                "trend": {
                    "current_week": current_week,
                    "previous_week": previous_week,
                    "percent_change": percent_change,
                },
                "days": days,
            }

            logger.debug(f"Stats calculated | total={len(changes)} | days={days}")
            return True, result

        except Exception as e:
            logger.error(f"Error getting change stats: {e}")
            return False, {"error": f"Error getting change stats: {str(e)}"}
