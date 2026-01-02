"""
Changes API endpoints for Archon

Handles:
- Change tracking CRUD operations
- Change listing with filters
- Project changelog generation
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config.logfire_config import get_logger, logfire
from ..services.change_service import VALID_CHANGE_TYPES, ChangeService

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["changes"])


class CreateChangeRequest(BaseModel):
    change_type: str
    summary: str
    project_id: str | None = None
    session_id: str | None = None
    details: dict[str, Any] | None = None
    files_affected: list[str] | None = None
    commit_sha: str | None = None


class UpdateChangeRequest(BaseModel):
    project_id: str | None = None
    summary: str | None = None
    details: dict[str, Any] | None = None
    files_affected: list[str] | None = None
    commit_sha: str | None = None


@router.get("/changes")
async def list_changes(
    project_id: str | None = None,
    change_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
):
    """
    List all changes with optional filters.

    Args:
        project_id: Filter by project UUID
        change_type: Filter by change type (feature, bugfix, refactor, docs, config, test)
        date_from: Filter by start date (ISO format YYYY-MM-DD)
        date_to: Filter by end date (ISO format YYYY-MM-DD)
        q: Search query for summary text
        page: Page number (1-indexed)
        per_page: Results per page (default 20)
    """
    try:
        logfire.debug(
            f"Listing changes | project_id={project_id} | change_type={change_type} | "
            f"date_from={date_from} | date_to={date_to} | q={q} | page={page}"
        )

        change_service = ChangeService()
        success, result = change_service.list_changes(
            project_id=project_id,
            change_type=change_type,
            date_from=date_from,
            date_to=date_to,
            search_query=q,
            page=page,
            per_page=per_page,
        )

        if not success:
            raise HTTPException(status_code=500, detail=result)

        logfire.debug(
            f"Changes listed | total={result.get('total_count', 0)} | page={page}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to list changes | error={str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/changes")
async def create_change(request: CreateChangeRequest):
    """
    Create a new change entry.

    Args:
        request: Change details including type, summary, and optional metadata
    """
    try:
        # Validate change type
        if request.change_type not in VALID_CHANGE_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid change_type. Must be one of: {', '.join(VALID_CHANGE_TYPES)}"
            )

        if not request.summary or not request.summary.strip():
            raise HTTPException(status_code=422, detail="Summary is required")

        logfire.info(
            f"Creating change | type={request.change_type} | "
            f"project_id={request.project_id} | summary={request.summary[:50]}..."
        )

        change_service = ChangeService()
        success, result = change_service.create_change(
            change_type=request.change_type,
            summary=request.summary,
            project_id=request.project_id,
            session_id=request.session_id,
            details=request.details,
            files_affected=request.files_affected,
            commit_sha=request.commit_sha,
        )

        if not success:
            raise HTTPException(status_code=400, detail=result)

        created_change = result["change"]
        logfire.info(f"Change created | id={created_change['id']}")

        return {"message": "Change created successfully", "change": created_change}

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to create change | error={str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.put("/changes/{change_id}")
async def update_change(change_id: str, request: UpdateChangeRequest):
    """
    Update a change entry.

    Args:
        change_id: UUID of the change to update
        request: Fields to update (project_id, summary, details, files_affected, commit_sha)
    """
    try:
        logfire.info(f"Updating change | id={change_id}")

        change_service = ChangeService()
        success, result = change_service.update_change(
            change_id=change_id,
            project_id=request.project_id,
            summary=request.summary,
            details=request.details,
            files_affected=request.files_affected,
            commit_sha=request.commit_sha,
        )

        if not success:
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail=error_msg)
            else:
                raise HTTPException(status_code=400, detail=error_msg)

        updated_change = result["change"]
        logfire.info(f"Change updated | id={change_id}")

        return {"message": "Change updated successfully", "change": updated_change}

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to update change | error={str(e)} | id={change_id}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/changes/{change_id}")
async def get_change(change_id: str):
    """
    Get a specific change by ID.

    Args:
        change_id: UUID of the change entry
    """
    try:
        logfire.debug(f"Getting change | id={change_id}")

        change_service = ChangeService()
        success, result = change_service.get_change(change_id)

        if not success:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail=result.get("error"))
            else:
                raise HTTPException(status_code=500, detail=result)

        logfire.debug(f"Change retrieved | id={change_id}")

        return result["change"]

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to get change | error={str(e)} | id={change_id}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/changes/{change_id}")
async def delete_change(change_id: str):
    """
    Delete a change entry.

    Args:
        change_id: UUID of the change to delete
    """
    try:
        logfire.info(f"Deleting change | id={change_id}")

        change_service = ChangeService()
        success, result = change_service.delete_change(change_id)

        if not success:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail=result.get("error"))
            else:
                raise HTTPException(status_code=500, detail=result)

        logfire.info(f"Change deleted | id={change_id}")

        return {"message": "Change deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to delete change | error={str(e)} | id={change_id}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/projects/{project_id}/changes")
async def list_project_changes(
    project_id: str,
    change_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    per_page: int = 20,
):
    """
    List all changes for a specific project.

    Args:
        project_id: UUID of the project
        change_type: Filter by change type
        date_from: Filter by start date (ISO format)
        date_to: Filter by end date (ISO format)
        page: Page number (1-indexed)
        per_page: Results per page (default 20)
    """
    try:
        logfire.debug(f"Listing project changes | project_id={project_id}")

        change_service = ChangeService()
        success, result = change_service.list_changes(
            project_id=project_id,
            change_type=change_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

        if not success:
            raise HTTPException(status_code=500, detail=result)

        logfire.debug(
            f"Project changes listed | project_id={project_id} | total={result.get('total_count', 0)}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to list project changes | error={str(e)} | project_id={project_id}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/projects/{project_id}/changelog")
async def get_project_changelog(
    project_id: str,
    format: str = "markdown",
):
    """
    Generate a formatted changelog for a project.

    Args:
        project_id: UUID of the project
        format: Output format ("markdown" or "json")
    """
    try:
        if format not in ["markdown", "json"]:
            raise HTTPException(
                status_code=422,
                detail="Invalid format. Must be 'markdown' or 'json'"
            )

        logfire.info(f"Generating changelog | project_id={project_id} | format={format}")

        change_service = ChangeService()
        success, result = change_service.get_project_changelog(
            project_id=project_id,
            format_type=format,
        )

        if not success:
            raise HTTPException(status_code=500, detail=result)

        logfire.info(
            f"Changelog generated | project_id={project_id} | format={format} | "
            f"changes_count={result.get('count', 0)}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to generate changelog | error={str(e)} | project_id={project_id}")
        raise HTTPException(status_code=500, detail={"error": str(e)})
