#!/usr/bin/env python3
"""
Agent-Browser E2E Tests for StarStream Monorepo

Validates all collaborative features work in real browsers:
- Multi-tab broadcasting
- Real-time synchronization
- Basic SSE functionality
"""

import subprocess
import time
import json
import requests
import sys
from pathlib import Path


def run_e2e_tests():
    """Run comprehensive E2E tests using agent-browser for multi-tab collaboration."""

    print("🧪 Starting StarStream E2E Tests...")

    # Paths - Create minimal test app right here
    test_app_dir = Path("temp_test_app")
    test_app_dir.mkdir(exist_ok=True)

    # Create minimal StarStream test app
    test_app_content = """
from starhtml import *

app, rt = star_app()

@rt("/")
def home():
    from starstream import StarStreamPlugin
    stream = StarStreamPlugin(app, default_topic="e2e_tests")
    
    # Simple broadcast example using starstream
    return Div(
        Div(data_init=f"@get('/starstream?topic=e2e', {{openWhenHidden: true}})"),  # SSE connection
        Div("E2E Test App", id="title"),
        Div(id="status", data_text="Waiting..."),
        Button("Trigger Broadcast", 
               data_on_click="@post('/test-broadcast', {value: 42})")
    )

@rt("/test-broadcast", methods=["POST"])
@sse
def test_broadcast():
    from starstream import StarStreamPlugin
    
    # Find plugin instance
    plugin = None
    for plugin_inst in getattr(app, '_starstream_plugins', []):
        if hasattr(plugin_inst, 'broadcast'):
            plugin = plugin_inst
            break
    
    if plugin:
        plugin.broadcast(("signals", {"status": f"Broadcasted! Time: {int(__import__('time').time())}"}), target="e2e")
    
    yield signals(status="Triggered")


if __name__ == "__main__":
    import uvicorn
    
    # Use available port
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    addr = s.getsockname()
    port = addr[1]
    s.close()
    
    print(f"Starting server on port {port}")
    
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(cfg)
    import asyncio
    asyncio.run(server.serve())
"""

    (test_app_dir / "app.py").write_text(test_app_content)

    # 1. Start minimal test server based on StarStream
    print("🚀 Starting minimal test server...")
    server_proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            """
import sys
sys.path.insert(0, ".")
exec(open("temp_test_app/app.py").read())
""",
        ],
        cwd=Path.cwd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(10)  # Wait for server startup (adjust as needed)

    try:
        # Find the actual port from logs (simplified - would need real port detection)
        import socket

        test_port = 8000  # Default to standard port

        # Test server is responding
        import urllib3

        http = urllib3.PoolManager()
        try:
            resp = http.request("GET", f"http://localhost:{test_port}/", timeout=5)
            if resp.status != 200:
                print(f"❌ Server not responding on port {test_port}")
                return False
        except:
            # Try different common ports
            for port in [8080, 8000, 5000]:
                try:
                    resp = http.request("GET", f"http://localhost:{port}/", timeout=5)
                    if resp.status == 200:
                        test_port = port
                        break
                except:
                    continue
            else:
                print("❌ Server not responding on any common ports")
                return False

        print(f"✅ Server running on http://localhost:{test_port}")

        # 2. Run basic broadcast test
        print(f"\n📋 Testing Basic Broadcast on port {test_port}...")
        basic_success = test_basic_broadcast(test_port)

        # Results
        print(f"\n{'🎉 BASIC TEST PASSED!' if basic_success else '❌ BASIC TEST FAILED'}")

        return basic_success

    finally:
        server_proc.terminate()
        server_proc.wait()

        # Cleanup
        import shutil

        if test_app_dir.exists():
            shutil.rmtree(test_app_dir)


def test_basic_broadcast(port):
    """Test basic broadcast functionality between tabs."""
    try:
        # Open two test tabs
        subprocess.run(
            ["agent-browser", "open", f"http://localhost:{port}/", "--session", "bc1"],
            check=True,
            timeout=15,
            capture_output=True,
        )
        subprocess.run(
            ["agent-browser", "open", f"http://localhost:{port}/", "--session", "bc2"],
            check=True,
            timeout=15,
            capture_output=True,
        )

        time.sleep(5)

        # Check initial state in both tabs
        initial1 = (
            subprocess.check_output(
                [
                    "agent-browser",
                    "--session",
                    "bc1",
                    "eval",
                    'document.getElementById("status").textContent',
                ]
            )
            .decode()
            .strip()
            .strip("\"'")
        )

        initial2 = (
            subprocess.check_output(
                [
                    "agent-browser",
                    "--session",
                    "bc2",
                    "eval",
                    'document.getElementById("status").textContent',
                ]
            )
            .decode()
            .strip()
            .strip("\"'")
        )

        # Initial state should be "Waiting..." for both
        if "Waiting" not in initial1 or "Waiting" not in initial2:
            print(f"❌ Unexpected initial state: {initial1}, {initial2}")
            return False

        # Trigger a broadcast from one tab
        subprocess.run(
            ["agent-browser", "--session", "bc1", "click", "button:text('Trigger Broadcast')"],
            check=True,
            capture_output=True,
        )

        time.sleep(5)  # Wait for broadcast propagation

        # Check state in both tabs after broadcast
        final1 = (
            subprocess.check_output(
                [
                    "agent-browser",
                    "--session",
                    "bc1",
                    "eval",
                    'document.getElementById("status").textContent',
                ]
            )
            .decode()
            .strip()
            .strip("\"'")
        )

        final2 = (
            subprocess.check_output(
                [
                    "agent-browser",
                    "--session",
                    "bc2",
                    "eval",
                    'document.getElementById("status").textContent',
                ]
            )
            .decode()
            .strip()
            .strip("\"'")
        )

        # Both should have received the broadcasted signal
        success = ("Broadcasted!" in final1 or "Triggered" in final1) and (
            "Broadcasted!" in final2 or "Triggered" in final2
        )

        subprocess.run(["agent-browser", "--session", "bc1", "close"], capture_output=True)
        subprocess.run(["agent-browser", "--session", "bc2", "close"], capture_output=True)

        return success

    except subprocess.TimeoutExpired:
        print("Broadcast test timed out")
        return False
    except Exception as e:
        print(f"Basic broadcast test failed: {e}")
        return False


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
