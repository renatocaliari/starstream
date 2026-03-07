"""
Test configuration and fixtures for StarStream tests.
"""

import pytest
import asyncio
from starstream.plugin import StarStreamPlugin, StarStreamCore


@pytest.fixture
def core():
    """Fresh StarStreamCore instance."""
    return StarStreamCore()


@pytest.fixture
def mock_app():
    """Mock StarHTML app for testing."""

    class MockApp:
        def __init__(self):
            self.routes = []
            self.middlewares = []

        def route(self, path, **kwargs):
            """Decorator to register routes."""

            def decorator(func):
                self.routes.append((path, func))
                return func

            return decorator

        def add_middleware(self, middleware):
            """Add middleware (not used in tests)."""
            self.middlewares.append(middleware)

    return MockApp()


@pytest.fixture
def plugin(mock_app):
    """StarStreamPlugin instance with mock app."""
    return StarStreamPlugin(mock_app)


@pytest.fixture
async def subscriber(core):
    """Helper to create a subscriber and collect messages."""
    messages = []

    async def collect(topic="global"):
        async for msg in core.subscribe(topic):
            messages.append(msg)
            if len(messages) >= 1:  # Stop after first message for tests
                break

    return messages, collect
