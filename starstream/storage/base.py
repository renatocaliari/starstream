"""
Storage package for StarStream.

Provides pluggable storage backends for persistence.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    Implementations:
    - SQLiteBackend: Local SQLite database
    - PostgresBackend: PostgreSQL (plugin separado)
    - PocketBaseBackend: PocketBase (plugin separado)
    - MemoryBackend: In-memory (for testing)

    Example:
        storage = SQLiteBackend("app.db")
        await storage.set("key", {"data": "value"})
        value = await storage.get("key")
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value by key.

        Args:
            key: Storage key
            value: Value to store (must be JSON serializable)
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete value by key.

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Glob-style pattern (e.g., "presence:*", "typing:room:123:*")

        Returns:
            List of matching keys
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all data."""
        pass

    async def close(self):
        """Close connection (optional)."""
        pass
