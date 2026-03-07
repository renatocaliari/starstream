"""
End-to-end tests with real server.
"""

import pytest
import asyncio
import aiohttp
from starstream.plugin import StarStreamPlugin


@pytest.mark.skip(reason="Requires running server - run manually")
class TestE2E:
    """End-to-end tests requiring running server."""

    @pytest.fixture
    async def server(self):
        """Start test server."""
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn

        app = Starlette()
        plugin = StarStreamPlugin(app)

        # Start server
        config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error")
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())

        await asyncio.sleep(0.5)  # Wait for server

        yield "http://127.0.0.1:8765"

        # Cleanup
        server.should_exit = True
        await task

    @pytest.mark.asyncio
    async def test_client_receives_broadcast(self, server):
        """Verify client receives broadcast message."""
        messages = []

        # Connect client
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server}/starstream?topic=test") as resp:
                # Broadcast from another client
                async with session.post(
                    f"{server}/broadcast", data={"topic": "test", "msg": "Hello"}
                ) as post_resp:
                    pass

                # Read SSE
                async for line in resp.content:
                    if line:
                        messages.append(line.decode())
                        if len(messages) >= 1:
                            break

        assert len(messages) > 0
        assert "Hello" in messages[0]

    @pytest.mark.asyncio
    async def test_room_isolation(self, server):
        """Verify messages don't leak between rooms."""
        room_a_msgs = []
        room_b_msgs = []

        async with aiohttp.ClientSession() as session:
            # Client A in room-a
            task_a = asyncio.create_task(
                self._collect_sse(
                    session, f"{server}/starstream?topic=room:a", room_a_msgs
                )
            )

            # Client B in room-b
            task_b = asyncio.create_task(
                self._collect_sse(
                    session, f"{server}/starstream?topic=room:b", room_b_msgs
                )
            )

            await asyncio.sleep(0.2)

            # Send to room-a only
            async with session.post(
                f"{server}/broadcast", data={"topic": "room:a", "msg": "Only A"}
            ) as resp:
                pass

            await asyncio.sleep(0.2)

            task_a.cancel()
            task_b.cancel()

        # Only room-a should receive
        assert len(room_a_msgs) > 0
        assert len(room_b_msgs) == 0

    async def _collect_sse(self, session, url, messages, timeout=1.0):
        """Helper to collect SSE messages."""
        try:
            async with session.get(url) as resp:
                async for line in resp.content:
                    if line and not line.startswith(b":"):
                        messages.append(line.decode())
        except asyncio.CancelledError:
            pass
