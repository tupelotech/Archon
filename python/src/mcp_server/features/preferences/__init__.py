"""
User preferences tools for Archon MCP Server.

This module provides tools for AI agents to access user preferences:
- get_user_preferences: Retrieve all user preferences
- manage_user_preference: Set or delete preferences
"""

from .preferences_tools import register_preferences_tools

__all__ = ["register_preferences_tools"]
