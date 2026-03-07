"""
Basic Example - Zero Config

This example shows the simplest possible usage of StarStream.
Just initialize the plugin and it works!
"""

from starhtml import *
from starstream import StarStreamPlugin

# Create StarHTML app
app, rt = star_app()

# Initialize StarStream - Zero Config!
stream = StarStreamPlugin(app)

# Example 1: Global Chat
# All clients receive all messages automatically


@rt("/")
def home():
    return Titled(
        "StarStream Basic Demo",
        Div(
            H1("Global Chat"),
            Div(id="chat", cls="messages"),
            Form(
                Input(name="msg", placeholder="Type a message..."),
                Button("Send"),
                data_on_submit=(post("/chat"), {"prevent": True}),
            ),
        ),
    )


@rt("/chat", methods=["POST"])
@sse
async def chat(msg: str):
    """
    Send a message to the global chat.

    Automatically broadcasts to all connected clients!
    No explicit broadcast call needed.
    """
    yield elements(Div(msg, cls="message"), "#chat", "append")


# Example 2: Simple Notifications


@rt("/notify", methods=["POST"])
@sse
async def notify(text: str, type_: str = "info"):
    """
    Send a notification to all clients.
    """
    yield signals(
        notification={
            "text": text,
            "type": type_,
            "timestamp": asyncio.get_event_loop().time(),
        }
    )


# Example 3: Counter that syncs across all clients

(counter_value := Signal("counter", 0))


@rt("/counter")
def counter_page():
    return Titled(
        "Sync Counter",
        Div(
            H1("Shared Counter"),
            Div(
                "Count: ",
                Span(data_text=counter_value, id="count"),
                cls="counter-display",
            ),
            Button("Increment", data_on_click=post("/counter/increment")),
            cls="counter",
        ),
    )


@rt("/counter/increment", methods=["POST"])
@sse
async def increment_counter():
    """
    Increment counter and sync to all clients.
    """
    # Get current value (in real app, use persistent storage)
    current = 0  # Would get from DB
    new_value = current + 1

    yield signals(counter=new_value)


if __name__ == "__main__":
    serve()
