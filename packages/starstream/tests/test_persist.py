"""
Tests for persist flag (Convention over Configuration for storage).

RED phase: These tests should FAIL initially.
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestPersistFlag:
    """Test persist flag replaces enable_history with clearer naming."""

    def test_persist_flag_creates_storage(self, mock_app):
        """persist=True should automatically create SQLite storage."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, persist=True)

        assert stream.storage is not None
        assert stream.storage.__class__.__name__ == "SQLiteBackend"

    def test_persist_false_no_storage(self, mock_app):
        """persist=False should not create storage."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, persist=False)

        assert stream.storage is None

    def test_persist_custom_db_path(self, mock_app):
        """persist=True with db_path should use custom path."""
        from starstream import StarStreamPlugin

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom.db")
            stream = StarStreamPlugin(mock_app, persist=True, db_path=custom_path)

            assert stream.storage is not None
            assert stream.storage.db_path == custom_path

    def test_persist_default_db_path(self, mock_app):
        """persist=True without db_path should use starstream.db."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, persist=True)

        assert stream.storage.db_path == "starstream.db"

    def test_custom_storage_overrides_persist(self, mock_app):
        """Custom storage should override persist flag."""
        from starstream import StarStreamPlugin
        from starstream.storage.base import StorageBackend

        class CustomStorage(StorageBackend):
            async def get(self, key):
                pass

            async def set(self, key, value, ttl=None):
                pass

            async def delete(self, key):
                pass

            async def exists(self, key):
                pass

            async def keys(self, pattern="*"):
                pass

            async def clear(self):
                pass

        custom = CustomStorage()
        stream = StarStreamPlugin(mock_app, persist=True, storage=custom)

        assert stream.storage is custom

    def test_backward_compatibility_enable_history(self, mock_app):
        """enable_history=True should work as alias for persist (deprecated)."""
        from starstream import StarStreamPlugin

        # This should still work but might show deprecation warning
        stream = StarStreamPlugin(mock_app, enable_history=True)

        assert stream.storage is not None
