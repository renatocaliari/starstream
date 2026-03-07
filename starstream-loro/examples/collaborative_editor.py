"""
Collaborative Document Editor with Loro CRDTs

This example demonstrates how to use starstream-loro to build
a real-time collaborative text editor with automatic conflict resolution.

Run:
    pip install starstream starstream-loro
    python collaborative_editor.py
"""

from starhtml import *
from starstream import StarStreamPlugin, Presence, TypingIndicator
from starstream_loro import LoroPlugin

app, rt = star_app()

# Initialize StarStream with features
stream = StarStreamPlugin(
    app,
    enable_presence=True,
    enable_typing=True
)

# Create collaborative features
presence = Presence(expire_seconds=300)
typing = TypingIndicator(auto_stop_seconds=5)
stream.presence = presence
stream.typing = typing

# Initialize Loro plugin for CRDT support
loro = LoroPlugin(stream)


def CollaborativeEditor(doc_id: str):
    """A collaborative text editor with presence and CRDT sync"""
    return Container(
        # Load Tailwind
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        
        # SSE Connection for real-time updates
        stream.get_stream_element(topic=f"doc:{doc_id}"),
        
        # Page header
        Div(cls="max-w-4xl mx-auto p-6")(
            H1(f"Collaborative Document: {doc_id}", 
               cls="text-3xl font-bold mb-4"),
            
            # Presence indicator
            Div(
                cls="bg-green-50 p-3 rounded-lg mb-4",
                **data_star_signals({"online_users": [], "typing_users": []})
            )(
                P(cls="text-green-800 font-semibold")("Online Users:"),
                Div(
                    cls="flex gap-2 flex-wrap mt-2",
                    data_star_children="online_users",
                    template=Span(cls="bg-white px-3 py-1 rounded-full text-sm")("${user}")
                ),
                P(cls="text-gray-600 text-sm mt-2")(
                    data_star_text("typing_users.length > 0 ? typing_users.join(', ') + ' is typing...' : ''")
                )
            ),
            
            # Editor
            Div(cls="mb-4")(
                TextArea(
                    id="editor",
                    cls="w-full h-96 p-4 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none font-mono",
                    placeholder="Start typing...",
                    data_star_on("input", f"""
                        fetch('/doc/{doc_id}/update', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                peer_id: window.peerId,
                                delta: this.value
                            }})
                        }});
                        
                        fetch('/doc/{doc_id}/typing', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{peer_id: window.peerId}})
                        }});
                    """)
                )
            ),
            
            # Stats
            Div(cls="text-sm text-gray-500")(
                Span("Connected peers: "),
                Span(data_star_text="online_users.length")
            )
        ),
        
        # Initialize on load
        Script(f"""
            window.peerId = 'user_' + Math.random().toString(36).substr(2, 9);
            window.docId = '{doc_id}';
            
            // Connect to document
            fetch('/doc/{doc_id}/connect?peer_id=' + window.peerId)
                .then(r => r.json())
                .then(data => console.log('Connected:', data));
        """)
    )


@rt("/")
def home():
    """Home page - list available documents"""
    return Container(
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        Div(cls="max-w-2xl mx-auto mt-20 p-6")(
            H1("Collaborative Documents", cls="text-4xl font-bold mb-8"),
            P("Create or join a document to start collaborating.", 
              cls="text-gray-600 mb-6"),
            
            Form(action="/doc/new", method="post")(
                Div(cls="flex gap-4")(
                    Input(
                        type="text",
                        name="doc_id",
                        placeholder="Document name (e.g., meeting-notes)",
                        cls="flex-1 px-4 py-3 border rounded-lg",
                        required=True
                    ),
                    Button(
                        "Create Document",
                        type="submit",
                        cls="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                    )
                )
            ),
            
            Div(cls="mt-8")(
                P("Quick join:", cls="font-semibold mb-2"),
                A("Sample Doc", href="/doc/sample", 
                  cls="text-blue-500 hover:underline")
            )
        )
    )


@rt("/doc/new", methods=["POST"])
def create_doc(doc_id: str):
    """Create and redirect to a new document"""
    return Redirect(f"/doc/{doc_id}")


@rt("/doc/{doc_id}")
def document_page(doc_id: str):
    """Document editing page"""
    return CollaborativeEditor(doc_id)


@rt("/doc/{doc_id}/connect")
async def doc_connect(doc_id: str, peer_id: str):
    """Connect a peer to the document"""
    # Connect to Loro CRDT
    await loro.connect(doc_id, peer_id)
    
    # Join presence
    await presence.join(f"doc:{doc_id}", peer_id)
    
    # Get document state
    state = await loro.get_state(doc_id)
    
    # Broadcast presence update
    online = presence.get_online(f"doc:{doc_id}")
    await stream.broadcast_to_topic(
        f"doc:{doc_id}",
        ('signals', {'online_users': online, 'user_joined': peer_id})
    )
    
    return {
        "status": "connected",
        "doc_id": doc_id,
        "state": state,
        "online_count": len(online)
    }


@rt("/doc/{doc_id}/update", methods=["POST"])
async def doc_update(doc_id: str, request):
    """Receive document update from a peer"""
    data = await request.json()
    peer_id = data.get("peer_id")
    delta = data.get("delta", "").encode()  # Convert to bytes
    
    # Apply to CRDT (in real app, would be actual Loro delta)
    await loro.receive_delta(doc_id, peer_id, delta)
    
    # Get peers to broadcast to
    peers = await loro.get_peers(doc_id, exclude=peer_id)
    
    # Broadcast update
    for peer in peers:
        await stream.send_to_user(peer, ('signals', {
            'doc_update': {'peer_id': peer_id, 'content': data.get("delta")}
        }))
    
    return {"status": "synced", "peers_notified": len(peers)}


@rt("/doc/{doc_id}/typing", methods=["POST"])
async def doc_typing(doc_id: str, request):
    """Handle typing indicator"""
    data = await request.json()
    peer_id = data.get("peer_id")
    
    await typing.start(f"doc:{doc_id}", peer_id)
    typers = typing.get_typing(f"doc:{doc_id}")
    
    await stream.broadcast_to_topic(
        f"doc:{doc_id}",
        ('signals', {'typing_users': typers})
    )
    
    return {"status": "ok"}


@rt("/doc/{doc_id}/leave", methods=["POST"])
async def doc_leave(doc_id: str, peer_id: str):
    """Peer leaves the document"""
    await loro.disconnect(doc_id, peer_id)
    await presence.leave(f"doc:{doc_id}", peer_id)
    
    online = presence.get_online(f"doc:{doc_id}")
    await stream.broadcast_to_topic(
        f"doc:{doc_id}",
        ('signals', {'online_users': online, 'user_left': peer_id})
    )
    
    return {"status": "disconnected"}


if __name__ == "__main__":
    print("=" * 60)
    print("StarStream-Loro Collaborative Editor Demo")
    print("=" * 60)
    print("\nOpen: http://localhost:8000")
    print("\nFeatures:")
    print("  ✓ Multi-user collaborative editing")
    print("  ✓ CRDT conflict resolution")
    print("  ✓ Real-time presence")
    print("  ✓ Typing indicators")
    print("\nTry opening multiple browser tabs!")
    print("=" * 60)
    
    serve()
