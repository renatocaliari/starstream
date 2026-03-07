# tests/test_core.py
import pytest
import asyncio
from starstream.core import StarStreamCore


@pytest.fixture
def core():
    return StarStreamCore()


def test_core_initialization(core):
    """Test core initializes with empty topics."""
    assert core._topics == {}
    assert core._user_topics == {}


@pytest.mark.asyncio
async def test_subscribe_and_receive(core):
    """Test subscribing to a topic and receiving messages."""
    messages = []
    
    async def consumer():
        async for msg in core.subscribe("test"):
            messages.append(msg)
            break
    
    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)
    
    await core.broadcast("hello", "test")
    await asyncio.sleep(0.01)
    
    assert "hello" in str(messages)
    consumer_task.cancel()


@pytest.mark.asyncio
async def test_broadcast_formats_sse(core):
    """Test broadcast formats message correctly for SSE."""
    messages = []
    
    async def consumer():
        async for msg in core.subscribe("test"):
            messages.append(msg)
            break
    
    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)
    
    await core.broadcast(("elements", ("<div>test</div>", "#app")), "test")
    await asyncio.sleep(0.01)
    
    assert len(messages) > 0
    msg = messages[0]
    assert "event: datastar-patch-elements" in msg
    assert "data: elements <div>test</div>" in msg
    assert "data: selector #app" in msg
    consumer_task.cancel()


@pytest.mark.asyncio
async def test_broadcast_to_multiple_subscribers(core):
    """Test broadcast reaches all subscribers."""
    messages1 = []
    messages2 = []
    
    async def consumer1():
        async for msg in core.subscribe("test"):
            messages1.append(msg)
            break
    
    async def consumer2():
        async for msg in core.subscribe("test"):
            messages2.append(msg)
            break
    
    task1 = asyncio.create_task(consumer1())
    task2 = asyncio.create_task(consumer2())
    await asyncio.sleep(0.01)
    
    await core.broadcast("hello", "test")
    await asyncio.sleep(0.01)
    
    assert len(messages1) > 0
    assert len(messages2) > 0
    assert "hello" in messages1[0]
    assert "hello" in messages2[0]
    
    task1.cancel()
    task2.cancel()


@pytest.mark.asyncio
async def test_subscribe_cleanup(core):
    """Test that subscriber is removed on cancellation."""
    async def consumer():
        async for msg in core.subscribe("test"):
            pass
    
    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)
    
    assert len(core._topics.get("test", set())) == 1
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    await asyncio.sleep(0.01)
    assert "test" not in core._topics or len(core._topics["test"]) == 0
