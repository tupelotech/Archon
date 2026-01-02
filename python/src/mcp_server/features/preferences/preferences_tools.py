"""
User preferences tools for Archon MCP Server.

Provides access to user preferences stored in archon_settings.
AI agents should call get_user_preferences at the start of a session
to understand user-specific settings.
"""

import json
import logging
from urllib.parse import urljoin

import httpx

from mcp.server.fastmcp import Context, FastMCP
from src.mcp_server.utils.error_handling import MCPErrorFormatter
from src.mcp_server.utils.timeout_config import get_default_timeout
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)

# Category for user preferences in archon_settings
USER_PREFERENCES_CATEGORY = "user_preferences"


def register_preferences_tools(mcp: FastMCP):
    """Register user preferences tools with the MCP server."""

    @mcp.tool()
    async def get_user_preferences(ctx: Context) -> str:
        """
        Get user preferences for AI agents.

        IMPORTANT: Call this tool at the start of any session to understand
        user-specific settings such as document format preferences,
        coding standards, and agent behavior instructions.

        Returns:
            JSON object with user preferences including:
            - DOCUMENT_FORMAT: Preferred format for documents (e.g., "markdown")
            - AGENT_INSTRUCTIONS: Custom instructions for AI agents
            - Additional user-defined preferences

        Example usage:
            get_user_preferences()  # Returns all user preferences
        """
        try:
            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    urljoin(api_url, f"/api/credentials/categories/{USER_PREFERENCES_CATEGORY}")
                )

                if response.status_code == 200:
                    data = response.json()
                    credentials = data.get("credentials", [])

                    # Format preferences as key-value pairs
                    preferences = {}
                    for cred in credentials:
                        key = cred.get("key", "")
                        value = cred.get("value", "")
                        description = cred.get("description", "")

                        preferences[key] = {
                            "value": value,
                            "description": description
                        }

                    if not preferences:
                        return json.dumps({
                            "success": True,
                            "preferences": {},
                            "message": "No user preferences configured. Use the Archon Settings UI to add preferences."
                        })

                    return json.dumps({
                        "success": True,
                        "preferences": preferences,
                        "message": f"Retrieved {len(preferences)} user preference(s)"
                    })

                elif response.status_code == 404:
                    return json.dumps({
                        "success": True,
                        "preferences": {},
                        "message": "No user preferences configured yet."
                    })
                else:
                    return MCPErrorFormatter.from_http_error(response, "get user preferences")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(e, "get user preferences")
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "get user preferences")

    @mcp.tool()
    async def manage_user_preference(
        ctx: Context,
        action: str,  # "set" | "delete"
        key: str,
        value: str | None = None,
        description: str | None = None,
    ) -> str:
        """
        Manage user preferences (set or delete).

        Args:
            action: "set" to create/update a preference, "delete" to remove
            key: Preference key name (e.g., "DOCUMENT_FORMAT", "AGENT_INSTRUCTIONS")
            value: Preference value (required for "set" action)
            description: Optional description of the preference

        Examples:
            manage_user_preference("set", "DOCUMENT_FORMAT", "markdown", "Preferred document format")
            manage_user_preference("delete", "OLD_PREFERENCE")

        Returns: {success: bool, message: string}
        """
        try:
            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                if action == "set":
                    if not value:
                        return MCPErrorFormatter.format_error(
                            "validation_error",
                            "value required for set action"
                        )

                    # Create or update preference
                    response = await client.post(
                        urljoin(api_url, "/api/credentials"),
                        json={
                            "key": key,
                            "value": value,
                            "is_encrypted": False,
                            "category": USER_PREFERENCES_CATEGORY,
                            "description": description or f"User preference: {key}"
                        }
                    )

                    if response.status_code == 200:
                        return json.dumps({
                            "success": True,
                            "message": f"User preference '{key}' saved successfully"
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "set user preference")

                elif action == "delete":
                    response = await client.delete(
                        urljoin(api_url, f"/api/credentials/{key}")
                    )

                    if response.status_code == 200:
                        return json.dumps({
                            "success": True,
                            "message": f"User preference '{key}' deleted successfully"
                        })
                    elif response.status_code == 404:
                        return MCPErrorFormatter.format_error(
                            "not_found",
                            f"Preference '{key}' not found",
                            http_status=404
                        )
                    else:
                        return MCPErrorFormatter.from_http_error(response, "delete user preference")

                else:
                    return MCPErrorFormatter.format_error(
                        "invalid_action",
                        f"Unknown action: {action}. Use 'set' or 'delete'"
                    )

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(e, f"{action} user preference")
        except Exception as e:
            logger.error(f"Error managing user preference ({action}): {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, f"{action} user preference")
