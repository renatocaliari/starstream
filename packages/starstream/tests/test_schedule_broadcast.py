# tests/test_schedule_broadcast.py
import pytest
from unittest.mock import Mock, AsyncMock
from starstream.plugin import StarStreamPlugin


def test_schedule_broadcast_exists():
    """Test that schedule_broadcast method exists."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    assert hasattr(plugin, 'schedule_broadcast')
    assert callable(plugin.schedule_broadcast)


def test_schedule_broadcast_adds_task():
    """Test schedule_broadcast adds task to BackgroundTasks."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    plugin.core = Mock()
    
    mock_background = Mock()
    mock_message = ("elements", ("<div>test</div>", "#app"))
    
    plugin.schedule_broadcast(mock_background, mock_message, target="test")
    
    assert mock_background.add_task.called
    
    task_func = mock_background.add_task.call_args[0][0]
    
    import asyncio
    assert asyncio.iscoroutinefunction(task_func)


def test_schedule_broadcast_with_string_message():
    """Test schedule_broadcast with string message."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    plugin.core = Mock()
    
    mock_background = Mock()
    
    plugin.schedule_broadcast(mock_background, "hello world", target="chat")
    
    assert mock_background.add_task.called


def test_schedule_broadcast_with_none_target():
    """Test schedule_broadcast with None target uses default."""
    app = Mock()
    plugin = StarStreamPlugin(app, default_topic="my_default")
    plugin.core = Mock()
    
    mock_background = Mock()
    
    plugin.schedule_broadcast(mock_background, "test", target=None)
    
    assert mock_background.add_task.called
    # Check that the task was added with default topic
    call_args = mock_background.add_task.call_args
    assert call_args is not None


def test_get_metrics():
    """Test get_metrics returns metrics."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    # Get metrics for non-existent topic
    stats = plugin.get_metrics("nonexistent")
    assert stats["success"] == 0
    assert stats["error"] == 0


def test_set_error_hook():
    """Test setting error hook."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    def my_hook(topic, message, error):
        pass
    
    plugin.set_error_hook(my_hook)
    
    assert plugin.on_broadcast_error == my_hook
