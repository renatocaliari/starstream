"""
StarStream Core - Broadcast Engine.

Separated from plugin for testability and clean architecture.
"""

import asyncio
import json
from typing import Set, Union, Tuple, Optional
from starlette.responses import StreamingResponse


class StarStreamCore:
    """
    Core broadcasting engine - manages topics and subscribers.

    Responsibilities:
    - Manage topic subscriptions
    - Format messages for SSE protocol
    - Execute broadcast safely
    """

    def __init__(self):
        self._topics: dict[str, Set[asyncio.Queue]] = {}
        self._user_topics: dict[str, str] = {}
        self._room_topics: dict[str, Set[str]] = {}

    async def subscribe(self, topic: str = "global"):
        """Subscribe to a topic and yield messages."""
        if topic not in self._topics:
            self._topics[topic] = set()

        queue = asyncio.Queue()
        self._topics[topic].add(queue)

        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            if topic in self._topics:
                self._topics[topic].discard(queue)
                if not self._topics[topic]:
                    del self._topics[topic]

    def _format_message(self, msg: Union[str, Tuple]) -> str:
        """Format message for SSE."""
        if isinstance(msg, tuple) and len(msg) >= 2:
            event_type = f"datastar-patch-{msg[0]}"
            payload = msg[1]
            lines = [f"event: {event_type}"]

            if msg[0] == "elements":
                content, selector, mode, use_vt, signals = self._unpack_elements(payload)
                if selector:
                    lines.append(f"data: selector {selector}")
                if mode:
                    lines.append(f"data: mode {mode}")
                if use_vt:
                    lines.append(f"data: useViewTransition {str(use_vt).lower()}")

                contents = content if isinstance(content, (list, tuple)) else [content]
                for item in contents:
                    for line in str(item).splitlines():
                        lines.append(f"data: elements {line}")

            elif msg[0] == "signals":
                # Handle starhtml signals format: {'payload': {...}, 'options': {...}}
                if isinstance(payload, dict) and "payload" in payload:
                    signals_data = payload["payload"]
                else:
                    signals_data = payload
                for line in json.dumps(signals_data).splitlines():
                    lines.append(f"data: signals {line}")

            return "\n".join(lines) + "\n\n"

        if isinstance(msg, str):
            if msg.startswith("event:"):
                return msg + ("\n\n" if not msg.endswith("\n\n") else "")
            return f"data: {msg}\n\n"
        return ""

    def _unpack_elements(self, payload) -> Tuple:
        """Unpack elements payload - handles various formats."""
        if isinstance(payload, tuple):
            if len(payload) >= 5:
                return payload[:5]
            elif len(payload) >= 2:
                return (payload[0], payload[1], None, None, None)
        return (payload, None, None, None, None)

    async def broadcast(
        self,
        message: Union[str, Tuple],
        topic: str = "global",
        exclude: Optional[Set] = None,
    ):
        """Broadcast message to all subscribers of a topic."""
        formatted = self._format_message(message)

        if topic in self._topics:
            for queue in list(self._topics[topic]):
                await queue.put(formatted)

    def sse_response(self, topic: str = "global"):
        """Create Starlette StreamingResponse for SSE."""

        async def event_publisher():
            try:
                async for msg in self.subscribe(topic):
                    yield msg
            except asyncio.CancelledError:
                pass

        return StreamingResponse(
            event_publisher(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
