"""
Unit tests for Cursor Tracker.
"""

import pytest
import asyncio
from starstream.cursor import CursorTracker, CursorPosition


class TestCursorTracker:
    """Test suite for CursorTracker class."""

    @pytest.fixture
    async def cursors(self):
        """Fresh cursor tracker instance."""
        c = CursorTracker(throttle_updates=50, auto_remove_after=0.5)
        await c.start()
        yield c
        await c.stop()

    @pytest.mark.asyncio
    async def test_update_adds_cursor(self, cursors):
        """Verify update adds cursor."""
        result = await cursors.update("canvas", "user_1", 100, 200)

        assert result is True
        pos = await cursors.get_position("canvas", "user_1")
        assert pos["x"] == 100
        assert pos["y"] == 200

    @pytest.mark.asyncio
    async def test_update_returns_false_when_throttled(self, cursors):
        """Verify update is throttled."""
        await cursors.update("canvas", "user_1", 100, 200)

        # Immediate update should be throttled
        result = await cursors.update("canvas", "user_1", 150, 250)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_allows_after_throttle_period(self, cursors):
        """Verify update allowed after throttle period."""
        await cursors.update("canvas", "user_1", 100, 200)

        # Wait for throttle period
        await asyncio.sleep(0.06)  # 60ms > 50ms throttle

        result = await cursors.update("canvas", "user_1", 150, 250)
        assert result is True

        pos = await cursors.get_position("canvas", "user_1")
        assert pos["x"] == 150
        assert pos["y"] == 250

    @pytest.mark.asyncio
    async def test_remove_removes_cursor(self, cursors):
        """Verify remove removes cursor."""
        await cursors.update("canvas", "user_1", 100, 200)
        result = await cursors.remove("canvas", "user_1")

        assert result is True
        pos = await cursors.get_position("canvas", "user_1")
        assert pos is None

    @pytest.mark.asyncio
    async def test_remove_returns_false_if_not_found(self, cursors):
        """Verify remove returns False if cursor not found."""
        result = await cursors.remove("canvas", "user_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_positions_returns_all(self, cursors):
        """Verify get_positions returns all cursors."""
        await cursors.update("canvas", "user_1", 100, 200, {"color": "red"})
        await cursors.update("canvas", "user_2", 300, 400, {"color": "blue"})

        positions = await cursors.get_positions("canvas")

        assert len(positions) == 2
        assert positions["user_1"]["x"] == 100
        assert positions["user_1"]["color"] == "red"
        assert positions["user_2"]["x"] == 300
        assert positions["user_2"]["color"] == "blue"

    @pytest.mark.asyncio
    async def test_auto_remove_removes_inactive_cursors(self, cursors):
        """Verify auto-remove removes inactive cursors."""
        await cursors.update("canvas", "user_1", 100, 200)
        assert await cursors.get_position("canvas", "user_1") is not None

        # Wait for auto-remove
        await asyncio.sleep(0.7)

        # Cursor should be removed
        assert await cursors.get_position("canvas", "user_1") is None

    @pytest.mark.asyncio
    async def test_get_cursor_count(self, cursors):
        """Verify get_cursor_count returns correct count."""
        await cursors.update("canvas", "user_1", 100, 200)
        await cursors.update("canvas", "user_2", 300, 400)

        count = await cursors.get_cursor_count("canvas")
        assert count == 2

    @pytest.mark.asyncio
    async def test_metadata_preserved(self, cursors):
        """Verify metadata is preserved between updates."""
        await cursors.update(
            "canvas", "user_1", 100, 200, {"color": "red", "name": "João"}
        )

        # Wait and update without metadata
        await asyncio.sleep(0.06)
        await cursors.update("canvas", "user_1", 150, 250)

        pos = await cursors.get_position("canvas", "user_1")
        assert pos["color"] == "red"
        assert pos["name"] == "João"

    @pytest.mark.asyncio
    async def test_cursors_isolated_per_topic(self, cursors):
        """Verify cursors are isolated per topic."""
        await cursors.update("canvas1", "user_1", 100, 200)
        await cursors.update("canvas2", "user_1", 300, 400)

        pos1 = await cursors.get_position("canvas1", "user_1")
        pos2 = await cursors.get_position("canvas2", "user_1")

        assert pos1["x"] == 100
        assert pos2["x"] == 300
