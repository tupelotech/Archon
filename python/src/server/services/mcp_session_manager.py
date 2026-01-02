"""
MCP Session Manager with Redis Persistence

This module provides session management for MCP server connections with Redis
backend for persistence across server restarts.

Note: While this persists Archon's session tracking, FastMCP's internal
streamable-http transport maintains its own in-memory session state that
cannot be externally persisted. This is a known limitation.

See: https://github.com/modelcontextprotocol/python-sdk/issues/880
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Protocol

from ..config.logfire_config import get_logger

logger = get_logger(__name__)


class SessionStore(Protocol):
    """Protocol for session storage backends."""

    def set(self, session_id: str, timestamp: datetime) -> None:
        """Store a session with its timestamp."""
        ...

    def get(self, session_id: str) -> datetime | None:
        """Get the timestamp for a session, or None if not found."""
        ...

    def delete(self, session_id: str) -> None:
        """Delete a session."""
        ...

    def get_all(self) -> dict[str, datetime]:
        """Get all sessions."""
        ...

    def count(self) -> int:
        """Get the count of sessions."""
        ...


class InMemorySessionStore:
    """In-memory session store (default fallback)."""

    def __init__(self):
        self._sessions: dict[str, datetime] = {}

    def set(self, session_id: str, timestamp: datetime) -> None:
        self._sessions[session_id] = timestamp

    def get(self, session_id: str) -> datetime | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get_all(self) -> dict[str, datetime]:
        return dict(self._sessions)

    def count(self) -> int:
        return len(self._sessions)


class RedisSessionStore:
    """Redis-backed session store for persistence across restarts."""

    def __init__(self, redis_url: str, key_prefix: str = "archon:mcp:session:"):
        self._key_prefix = key_prefix
        self._redis_url = redis_url
        self._client = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            import redis

            self._client = redis.from_url(self._redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info(f"Connected to Redis at {self._redis_url}")
        except ImportError:
            logger.warning("redis package not installed, falling back to in-memory storage")
            self._client = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, falling back to in-memory storage")
            self._client = None

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    def set(self, session_id: str, timestamp: datetime) -> None:
        if self._client:
            try:
                self._client.set(self._key(session_id), timestamp.isoformat())
            except Exception as e:
                logger.error(f"Failed to set session in Redis: {e}")

    def get(self, session_id: str) -> datetime | None:
        if self._client:
            try:
                value = self._client.get(self._key(session_id))
                if value:
                    return datetime.fromisoformat(value)
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")
        return None

    def delete(self, session_id: str) -> None:
        if self._client:
            try:
                self._client.delete(self._key(session_id))
            except Exception as e:
                logger.error(f"Failed to delete session from Redis: {e}")

    def get_all(self) -> dict[str, datetime]:
        sessions = {}
        if self._client:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._client.scan(cursor, match=f"{self._key_prefix}*", count=100)
                    for key in keys:
                        session_id = key.removeprefix(self._key_prefix)
                        value = self._client.get(key)
                        if value:
                            sessions[session_id] = datetime.fromisoformat(value)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Failed to get all sessions from Redis: {e}")
        return sessions

    def count(self) -> int:
        if self._client:
            try:
                cursor = 0
                count = 0
                while True:
                    cursor, keys = self._client.scan(cursor, match=f"{self._key_prefix}*", count=100)
                    count += len(keys)
                    if cursor == 0:
                        break
                return count
            except Exception as e:
                logger.error(f"Failed to count sessions in Redis: {e}")
        return 0


class SessionManager:
    """
    MCP session manager with pluggable storage backend.

    Uses Redis when available for persistence across restarts,
    falls back to in-memory storage.
    """

    def __init__(self, timeout: int = 3600, store: SessionStore | None = None):
        """
        Initialize session manager.

        Args:
            timeout: Session expiration time in seconds (default: 1 hour)
            store: Optional session store (defaults to Redis if available, else in-memory)
        """
        self.timeout = timeout

        if store:
            self._store = store
        else:
            # Try Redis first, fallback to in-memory
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                redis_store = RedisSessionStore(redis_url)
                if redis_store._client:
                    self._store = redis_store
                    logger.info("Using Redis for session storage")
                else:
                    self._store = InMemorySessionStore()
                    logger.info("Using in-memory session storage (Redis unavailable)")
            else:
                self._store = InMemorySessionStore()
                logger.info("Using in-memory session storage (REDIS_URL not set)")

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self._store.set(session_id, datetime.now())
        logger.info(f"Created new session: {session_id}")
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """Validate a session ID and update last seen time."""
        last_seen = self._store.get(session_id)
        if last_seen is None:
            return False

        if datetime.now() - last_seen > timedelta(seconds=self.timeout):
            # Session expired, remove it
            self._store.delete(session_id)
            logger.info(f"Session {session_id} expired and removed")
            return False

        # Update last seen time
        self._store.set(session_id, datetime.now())
        return True

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        now = datetime.now()
        expired = []

        for session_id, last_seen in self._store.get_all().items():
            if now - last_seen > timedelta(seconds=self.timeout):
                expired.append(session_id)

        for session_id in expired:
            self._store.delete(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        # Clean up expired sessions first
        self.cleanup_expired_sessions()
        return self._store.count()


# Backward compatibility alias
SimplifiedSessionManager = SessionManager

# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
