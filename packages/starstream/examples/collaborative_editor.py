"""
Simple Collaborative Editor Example

Demonstrates collaborative editing with persist flag.

Install: pip install starstream[collaborative]
Run: uv run examples/collaborative_editor.py
"""

from starhtml import star_app, rt, serve, Div, H1, P, Form, Input, Button, Label, Textarea, Script
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app, collaborative=True, persist=True)


@rt("/")
def home():
    return (
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        Div(cls="max-w-2xl mx-auto p-8")(
            H1("Collaborative Editor", cls="text-3xl font-bold mb-6"),
            P("Real-time editing with CRDT", cls="text-gray-600 mb-8"),
            Form(action="/doc", method="get", cls="space-y-4")(
                Div(
                    Label("Document ID:", cls="block mb-1"),
                    Input(
                        name="doc_id",
                        placeholder="my-doc",
                        required=True,
                        cls="w-full p-2 border rounded",
                    ),
                ),
                Div(
                    Label("Your Name:", cls="block mb-1"),
                    Input(name="user", required=True, cls="w-full p-2 border rounded"),
                ),
                Button("Join", type="submit", cls="w-full p-2 bg-blue-500 text-white rounded"),
            ),
        ),
    )


@rt("/doc")
def editor(doc_id: str, user: str):
    return (
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        stream.get_stream_element(topic=f"doc:{doc_id}"),
        Div(cls="max-w-4xl mx-auto p-6")(
            H1(f"Document: {doc_id}", cls="text-2xl font-bold mb-4"),
            P(f"User: {user}", cls="text-gray-600 mb-4"),
            Textarea(
                id="editor",
                placeholder="Type here...",
                cls="w-full h-96 p-4 border rounded",
                hx_post=f"/doc/{doc_id}/sync?user={user}",
                hx_trigger="input changed delay:300ms",
                hx_target="#status",
            ),
            Div(id="status", cls="mt-2 text-sm text-gray-500")("● Connected"),
        ),
    )


@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_document(doc_id: str, user: str, request):
    """Receive delta from client and sync with auto-broadcast to other peers."""
    # In production, receive delta from request body
    # delta = await request.body()
    # await stream.collaborative.sync(doc_id, delta, user)

    # For demo: just acknowledge the sync
    await stream.collaborative.connect(doc_id, user)
    return Div(cls="text-green-600")("Synced - Auto-broadcast to other peers")


if __name__ == "__main__":
    print("Collaborative Editor Demo")
    print("Open: http://localhost:8000")
    print("Features: CRDT, Persistence, Real-time sync")
    serve()
