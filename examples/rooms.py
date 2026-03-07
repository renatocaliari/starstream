"""
Rooms Example - Multi-Room Chat

Shows how to use auto-room detection for multi-room chat.
"""

from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)

# Simulated room storage
rooms = {
    "general": {"name": "General", "messages": []},
    "tech": {"name": "Tech Talk", "messages": []},
    "random": {"name": "Random", "messages": []},
}


@rt("/")
def home():
    """Room list page."""
    return Titled(
        "Multi-Room Chat",
        Div(
            H1("Choose a Room"),
            Div(
                *[
                    A(
                        f"{info['name']} ({len(info['messages'])} msgs)",
                        href=f"/room/{room_id}",
                        cls="room-link",
                    )
                    for room_id, info in rooms.items()
                ],
                cls="room-list",
            ),
        ),
    )


@rt("/room/{room_id}")
def room_page(room_id: str):
    """
    Individual room page.

    Auto-detection:
    - room_id parameter → broadcast only to this room
    """
    room = rooms.get(room_id, rooms["general"])

    return Titled(
        f"Room: {room['name']}",
        Div(
            A("← Back to Rooms", href="/"),
            H1(room["name"]),
            Div(id=f"room-{room_id}", cls="room-messages"),
            Form(
                Input(name="msg", placeholder=f"Message #{room_id}..."),
                Button("Send"),
                data_on_submit=(post(f"/room/{room_id}/send"), {"prevent": True}),
            ),
            Script(f"""
                // Connect to room-specific stream
                const evtSource = new EventSource("/starstream?topic=room:{room_id}");
                evtSource.onmessage = (e) => {{
                    console.log("Room message:", e.data);
                }};
            """),
        ),
    )


@rt("/room/{room_id}/send", methods=["POST"])
@sse
async def send_to_room(room_id: str, msg: str):
    """
    Send message to a specific room.

    Auto-detects topic from room_id parameter.
    Only clients in this room receive the message!
    """
    if room_id in rooms:
        rooms[room_id]["messages"].append(msg)

    yield elements(Div(msg, cls="room-message"), f"#room-{room_id}", "append")


# Example: Admin broadcast to all rooms


@rt("/admin/broadcast", methods=["POST"])
@sse
async def admin_broadcast(msg: str):
    """
    Admin can broadcast to ALL rooms.
    Uses manual API for cross-room broadcast.
    """
    # Send to global topic (all rooms)
    await stream.broadcast_to_topic("global", ("signals", {"admin_alert": msg}))

    yield signals(admin_broadcast="sent")


if __name__ == "__main__":
    serve()
