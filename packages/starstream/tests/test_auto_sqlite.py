"""Test auto-SQLite storage when enable_history=True"""

import pytest
import tempfile
import os
from unittest.mock import Mock
from starstream.plugin import StarStreamPlugin


def test_auto_sqlite_created_when_enable_history_true():
    """Test that SQLite storage is auto-created when enable_history=True"""
    mock_app = Mock()

    # Should NOT raise - auto-creates SQLite
    plugin = StarStreamPlugin(mock_app, enable_history=True)

    # Verify storage was created
    assert plugin.storage is not None
    assert hasattr(plugin.storage, "db_path")

    # Cleanup
    if os.path.exists(plugin.storage.db_path):
        os.remove(plugin.storage.db_path)


def test_auto_sqlite_with_custom_db_path():
    """Test auto-SQLite with custom database path"""
    mock_app = Mock()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        custom_path = f.name

    try:
        plugin = StarStreamPlugin(mock_app, enable_history=True, db_path=custom_path)

        assert plugin.storage is not None
        assert plugin.storage.db_path == custom_path
    finally:
        if os.path.exists(custom_path):
            os.remove(custom_path)


def test_no_storage_when_enable_history_false():
    """Test that no storage is created when enable_history=False"""
    mock_app = Mock()

    plugin = StarStreamPlugin(mock_app, enable_history=False)

    # Should be None when history disabled
    assert plugin.storage is None


def test_custom_storage_overrides_auto_creation():
    """Test that custom storage parameter overrides auto-creation"""
    from starstream.storage.sqlite import SQLiteBackend

    mock_app = Mock()
    custom_storage = SQLiteBackend("custom.db")

    plugin = StarStreamPlugin(mock_app, enable_history=True, storage=custom_storage)

    # Should use custom storage, not auto-created
    assert plugin.storage is custom_storage
    assert plugin.storage.db_path == "custom.db"

    # Cleanup
    if os.path.exists("custom.db"):
        os.remove("custom.db")
