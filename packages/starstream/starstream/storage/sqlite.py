"""
SQLite Storage Backend

Simple file-based storage using SQLite.
Zero configuration - just provide a filepath.
"""

import sqlite3
import json
import fnmatch
from typing import Any, Optional, List
from .base import StorageBackend


class SQLiteBackend(StorageBackend):
    """
    SQLite-based storage backend.

    Example:
        storage = SQLiteBackend("app.db")
        await storage.set("presence:user_1", {"name": "João"})
        data = await storage.get("presence:user_1")
    """

    def __init__(self, db_path: str = "starstream.db"):
        """
        Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires ON storage(expires_at)
            """)
            conn.commit()

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        with sqlite3.connect(self.db_path) as conn:
            # Clean up expired entries first
            conn.execute("DELETE FROM storage WHERE expires_at < datetime('now')")

            cursor = conn.execute(
                "SELECT value FROM storage WHERE key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))",
                (key,),
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value by key."""
        json_value = json.dumps(value)

        with sqlite3.connect(self.db_path) as conn:
            if ttl:
                conn.execute(
                    """INSERT OR REPLACE INTO storage (key, value, expires_at)
                       VALUES (?, ?, datetime('now', '+' || ? || ' seconds'))""",
                    (key, json_value, ttl),
                )
            else:
                conn.execute(
                    """INSERT OR REPLACE INTO storage (key, value, expires_at)
                       VALUES (?, ?, NULL)""",
                    (key, json_value),
                )
            conn.commit()
        return True

    async def delete(self, key: str) -> bool:
        """Delete value by key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM storage WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        with sqlite3.connect(self.db_path) as conn:
            # Clean up expired entries first
            conn.execute("DELETE FROM storage WHERE expires_at < datetime('now')")

            cursor = conn.execute(
                "SELECT 1 FROM storage WHERE key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))",
                (key,),
            )
            return cursor.fetchone() is not None

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        with sqlite3.connect(self.db_path) as conn:
            # Clean up expired entries first
            conn.execute("DELETE FROM storage WHERE expires_at < datetime('now')")

            cursor = conn.execute(
                "SELECT key FROM storage WHERE expires_at IS NULL OR expires_at > datetime('now')"
            )
            all_keys = [row[0] for row in cursor.fetchall()]

            # Filter by pattern
            return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    async def clear(self) -> bool:
        """Clear all data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM storage")
            conn.commit()
        return True
