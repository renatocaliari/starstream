"""
Full Features Demo - Shows all StarStream features working together

This example demonstrates:
- Multi-room chat with presence
- Typing indicators
- Cursor tracking (collaborative editing feel)
- Message history
- Auto-detection of room_id
"""

import asyncio
from starhtml import *
from starhtml.plugins.sse import sse
from starstream import StarStreamPlugin, PresenceSystem, TypingIndicator, CursorTracker, MessageHistory

app, rt = star_app()

# Create feature systems
presence = PresenceSystem(expire_seconds=300)  # 5 min timeout
typing = TypingIndicator(auto_stop_seconds=5)  # Stop after 5s
cursors = CursorTracker(update_throttle=0.05)  # 20Hz max
history = MessageHistory(max_messages=500, ttl_seconds=3600)  # 1 hour TTL

# Initialize plugin with all features
stream = StarStreamPlugin(
    app,
    enable_presence=True,
    enable_typing=True,
    enable_cursor=True,
    enable_history=True
)

# Register feature systems with the plugin
stream.presence = presence
stream.typing = typing
stream.cursors = cursors
stream.history = history


# ========== Page Components ==========

def ChatRoom(room_id: str, username: str):
    """A complete chat room with all features"""
    return Container(
        # Page setup
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        
        # SSE Datastar connection
        stream.get_stream_element(topic=f"room:{room_id}"),
        
        # Header
        Div(
            H2(f"Room: {room_id}", cls="text-2xl font-bold"),
            P(f"Logged in as: {username}", cls="text-gray-600"),
            cls="mb-6"
        ),
        
        # Online users indicator
        Div(
            cls="online-users bg-green-100 p-3 rounded mb-4",
            **data_star_signals({"online": [], "typing": [], "cursors": {}})
        )(
            P(cls="font-semibold text-green-800")("Online Users:"),
            Ul(
                cls="flex gap-2 flex-wrap",
                data_star_children="online",
                template=Li(cls="bg-white px-3 py-1 rounded")("${user}")
            ),
            P(cls="text-sm text-gray-600 mt-2")(
                data_star_text("typing.length > 0 ? typing.join(', ') + ' is typing...' : ''")
            )
        ),
        
        # Collaborative cursor area (simulated shared space)
        Div(
            cls="relative h-64 bg-gray-100 rounded mb-4 overflow-hidden border-2 border-dashed border-gray-300",
            **data_star_signals({"myCursor": {"x": 0, "y": 0}})
        )(
            P(cls="absolute top-2 left-2 text-gray-500")("Move your mouse here!"),
            # Cursors will be rendered here
            Div(
                cls="absolute inset-0",
                data_star_html="Object.entries(cursors).filter(([k,v]) => k !== username).map(([user, pos]) => `
                    <div class='absolute w-4 h-4 bg-blue-500 rounded-full shadow-lg transition-all duration-75' 
                         style='left:${pos.x}px;top:${pos.y}px'>
                        <span class='absolute -top-6 left-0 text-xs bg-blue-500 text-white px-2 py-1 rounded'>${user}</span>
                    </div>
                `).join('')"
            ),
            # Mouse tracking
            data_star_on("mousemove", f"myCursor.x = event.offsetX; myCursor.y = event.offsetY; fetch('/cursor', {{method:'POST', body: new URLSearchParams({{user:'{username}', room_id:'{room_id}', x:myCursor.x, y:myCursor.y}})}})")
        ),
        
        # Message history
        Div(
            cls="chat-history bg-white border rounded h-96 overflow-y-auto mb-4 p-4",
            **data_star_signals({"messages": []})
        )(
            Div(
                data_star_children="messages",
                template=Div(cls="mb-2 p-2 bg-gray-50 rounded")(
                    Span(cls="font-bold text-blue-600")("${user}: "),
                    Span("${text}")
                )
            )
        ),
        
        # Message input
        Form(
            **data_star_signals({"msg": ""})
        )(
            Div(cls="flex gap-2")(
                Input(
                    type="text",
                    name="msg",
                    data_star_bind="msg",
                    placeholder="Type a message...",
                    cls="flex-1 px-4 py-2 border rounded",
                    data_star_on("input", f"fetch('/typing', {{method:'POST', body: new URLSearchParams({{user:'{username}', room_id:'{room_id}'}})}})")
                ),
                Button(
                    "Send",
                    type="submit",
                    cls="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                )
            ),
            hx_post=f"/room/{room_id}/send",
            hx_target="#messages",
            hx_swap="beforeend",
            data_star_on("submit", "msg = ''")  # Clear input on send
        ),
        
        # Status
        Div(cls="mt-4 text-sm text-gray-500")(
            "Connection: ",
            Span(cls="text-green-600 font-semibold")("● Live")
        ),
        
        cls="max-w-4xl mx-auto p-6"
    )


# ========== Routes ==========

@rt("/")
def home():
    """Home page - choose a room"""
    return Container(
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        Div(cls="max-w-md mx-auto mt-20 p-6 bg-white rounded-lg shadow-lg")(
            H1("StarStream Demo", cls="text-3xl font-bold mb-2"),
            P("Real-time collaboration with zero config", cls="text-gray-600 mb-6"),
            
            Form(action="/join", method="post")(
                Div(cls="space-y-4")(
                    Div(
                        Label("Your Name:", cls="block text-sm font-medium mb-1"),
                        Input(
                            type="text",
                            name="username",
                            required=True,
                            cls="w-full px-3 py-2 border rounded"
                        )
                    ),
                    Div(
                        Label("Room ID:", cls="block text-sm font-medium mb-1"),
                        Input(
                            type="text",
                            name="room_id",
                            placeholder="e.g., general, team-alpha",
                            required=True,
                            cls="w-full px-3 py-2 border rounded"
                        )
                    ),
                    Button(
                        "Join Room",
                        type="submit",
                        cls="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    )
                )
            )
        )
    )


@rt("/join", methods=["POST"])
def join_room(username: str, room_id: str):
    """Join a chat room"""
    return ChatRoom(room_id, username)


@rt("/room/{room_id}/send", methods=["POST"])
@sse
async def send_message(room_id: str, username: str, msg: str):
    """Send a message to the room (auto-detected topic!)"""
    # Store in history
    await history.add(room_id, {
        'user': username,
        'text': msg,
        'timestamp': asyncio.get_event_loop().time()
    })
    
    # Stop typing indicator
    await typing.stop(room_id, username)
    
    # Broadcast to room (auto-detected!)
    message_el = Div(cls="mb-2 p-2 bg-gray-50 rounded")(
        Span(cls="font-bold text-blue-600")(f"{username}: "),
        Span(msg)
    )
    
    yield elements(message_el, ".chat-history", "append")


@rt("/typing", methods=["POST"])
async def typing_indicator(user: str, room_id: str):
    """Handle typing indicator"""
    await typing.start(room_id, user)
    typers = typing.get_typing(room_id)
    
    # Broadcast typing status
    await stream.broadcast_to_room(room_id,
        ('signals', {'typing': typers})
    )


@rt("/cursor", methods=["POST"])
async def cursor_position(user: str, room_id: str, x: int, y: int):
    """Handle cursor position updates"""
    await cursors.update(room_id, user, x, y)
    positions = cursors.get_positions(room_id)
    
    # Broadcast cursor positions
    await stream.broadcast_to_room(room_id,
        ('signals', {'cursors': positions})
    )


@rt("/room/{room_id}/users")
async def get_online_users(room_id: str):
    """Get online users for a room"""
    users = presence.get_online(room_id)
    return {'users': users}


# ========== Startup ==========

if __name__ == "__main__":
    print("=" * 50)
    print("StarStream Full Features Demo")
    print("=" * 50)
    print("\nOpen: http://localhost:8000")
    print("\nFeatures:")
    print("  ✓ Multi-room chat")
    print("  ✓ Presence (online users)")
    print("  ✓ Typing indicators")
    print("  ✓ Cursor tracking")
    print("  ✓ Message history")
    print("\nTry opening multiple browser tabs!")
    print("=" * 50)
    
    serve()
