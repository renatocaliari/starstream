"""
Custom Example - Advanced Usage

Shows how to customize StarStream behavior when needed.
"""

from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)

# Example 1: Custom topic with filter


@rt("/admin")
@stream.configure(topic="admin-only", filter_fn=lambda ctx: ctx.get("is_admin", False))
@sse
async def admin_message(msg: str):
    """
    Only admins receive these messages.
    Uses custom configuration.
    """
    yield elements(Div(f"[ADMIN] {msg}", cls="admin-msg"), "#admin-panel", "append")


# Example 2: Manual broadcast control


@rt("/notify-selected", methods=["POST"])
async def notify_selected_users(user_ids: list, msg: str):
    """
    Send notification to specific users only.
    Uses manual API.
    """
    for user_id in user_ids:
        await stream.send_to_user(user_id, ("signals", {"notification": msg}))

    return {"sent": len(user_ids)}


# Example 3: Broadcast to multiple rooms


@rt("/announcement", methods=["POST"])
async def announce_to_rooms(room_ids: list, announcement: str):
    """
    Send announcement to multiple rooms.
    """
    for room_id in room_ids:
        await stream.broadcast_to_room(
            room_id, ("signals", {"announcement": announcement})
        )

    return {"rooms_notified": len(room_ids)}


# Example 4: Throttled broadcasts

from starstream.helpers import throttle


@rt("/cursor", methods=["POST"])
@throttle(0.05)  # Max 20 updates per second
async def cursor_update(x: int, y: int, user_id: str):
    """
    Send cursor position to all users.
    Throttled to prevent spam.
    """
    await stream.broadcast_to_topic(
        "global", ("signals", {"cursor": {"x": x, "y": y, "user": user_id}})
    )


# Example 5: Debounced save

from starstream.helpers import debounce


@rt("/doc/{doc_id}/save", methods=["POST"])
@debounce(0.5)  # Wait 500ms after last change
async def save_document(doc_id: str, content: str):
    """
    Save document and notify collaborators.
    Debounced to batch rapid changes.
    """
    # Save to DB...

    # Notify collaborators
    await stream.broadcast_to_topic(
        f"doc:{doc_id}",
        (
            "signals",
            {
                "doc_saved": {
                    "doc_id": doc_id,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            },
        ),
    )


# Example 6: Custom convention

from starstream.conventions import ChatConvention


class MyAppConvention(ChatConvention):
    """Custom convention for this app."""

    def detect(self, route_path: str, **kwargs) -> str:
        # Custom logic
        if "project" in kwargs:
            return f"project:{kwargs['project']}:chat"
        return super().detect(route_path, **kwargs)


# Register custom convention
# stream.register_convention(MyAppConvention())


if __name__ == "__main__":
    serve()
