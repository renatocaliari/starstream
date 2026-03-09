"""
Collaborative Canvas Example with StarStream SDK

Demonstrates zero-config real-time collaboration.
Users can draw on canvas and see drawings from other peers instantly.

Run: uv run examples/collaborative_canvas_sdk.py
"""

from starhtml import star_app, rt, serve, Div, H1, P, Script
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app, collaborative=True)


@rt("/")
def home():
    return (
        Script(src="https://unpkg.com/@tailwindcss/browser@4"),
        # Include StarStream SDK
        Script(src="/static/starstream.js"),
        stream.get_stream_element(topic="doc:canvas-main"),
        Div(cls="max-w-4xl mx-auto p-6")(
            H1("Collaborative Canvas", cls="text-3xl font-bold mb-4 text-center"),
            P(
                "Draw on the canvas! Open multiple tabs to see real-time sync.",
                cls="text-gray-600 mb-6 text-center",
            ),
            P(id="peer-info", cls="text-sm text-blue-600 mb-4 text-center font-mono"),
            canvas := Div(
                id="canvas",
                cls="w-full h-96 bg-white border-4 border-gray-300 rounded-lg shadow-lg cursor-crosshair relative overflow-hidden",
            ),
            Div(cls="mt-4 flex gap-4 justify-center")(
                Div(cls="flex items-center gap-2")(
                    Div(cls="w-4 h-4 rounded-full bg-red-500"),
                    P("Your drawings", cls="text-sm"),
                ),
                Div(cls="flex items-center gap-2")(
                    Div(cls="w-4 h-4 rounded-full bg-blue-500"),
                    P("Other peers", cls="text-sm"),
                ),
            ),
            Div(id="status", cls="mt-4 text-center text-sm text-gray-500")("Connecting..."),
        ),
        Script("""
            // Initialize StarStream collaborative document
            const doc = starstream.collaborative('canvas-main', { debug: true });
            const canvas = document.getElementById('canvas');
            const status = document.getElementById('status');
            const peerInfo = document.getElementById('peer-info');
            
            // Show peer ID
            peerInfo.textContent = 'Your peer: ' + doc.getPeerId();
            
            // Track drawing state
            let isDrawing = false;
            let currentPath = [];
            
            // Create SVG overlay for drawings
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.style.position = 'absolute';
            svg.style.top = '0';
            svg.style.left = '0';
            svg.style.pointerEvents = 'none';
            canvas.appendChild(svg);
            
            // Get coordinates relative to canvas
            function getCoords(e) {
                const rect = canvas.getBoundingClientRect();
                return {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top
                };
            }
            
            // Draw a path on the canvas
            function drawPath(path, color, peerId) {
                if (path.length < 2) return;
                
                const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                let d = `M ${path[0].x} ${path[0].y}`;
                for (let i = 1; i < path.length; i++) {
                    d += ` L ${path[i].x} ${path[i].y}`;
                }
                
                pathEl.setAttribute('d', d);
                pathEl.setAttribute('stroke', color);
                pathEl.setAttribute('stroke-width', '3');
                pathEl.setAttribute('fill', 'none');
                pathEl.setAttribute('stroke-linecap', 'round');
                pathEl.setAttribute('stroke-linejoin', 'round');
                pathEl.dataset.peer = peerId;
                
                svg.appendChild(pathEl);
            }
            
            // Start drawing
            canvas.addEventListener('mousedown', (e) => {
                isDrawing = true;
                currentPath = [getCoords(e)];
            });
            
            // Draw
            canvas.addEventListener('mousemove', (e) => {
                if (!isDrawing) return;
                const coords = getCoords(e);
                currentPath.push(coords);
                
                // Draw locally immediately
                if (currentPath.length > 1) {
                    // Remove previous temp path
                    const prevPath = svg.querySelector('.temp-path');
                    if (prevPath) prevPath.remove();
                    
                    // Draw current path
                    const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    let d = `M ${currentPath[0].x} ${currentPath[0].y}`;
                    for (let i = 1; i < currentPath.length; i++) {
                        d += ` L ${currentPath[i].x} ${currentPath[i].y}`;
                    }
                    pathEl.setAttribute('d', d);
                    pathEl.setAttribute('stroke', '#ef4444');
                    pathEl.setAttribute('stroke-width', '3');
                    pathEl.setAttribute('fill', 'none');
                    pathEl.setAttribute('stroke-linecap', 'round');
                    pathEl.classList.add('temp-path');
                    pathEl.dataset.peer = 'local';
                    svg.appendChild(pathEl);
                }
            });
            
            // End drawing and sync
            canvas.addEventListener('mouseup', () => {
                if (!isDrawing) return;
                isDrawing = false;
                
                if (currentPath.length > 1) {
                    // Remove temp path
                    const prevPath = svg.querySelector('.temp-path');
                    if (prevPath) prevPath.remove();
                    
                    // Draw final path locally
                    drawPath(currentPath, '#ef4444', doc.getPeerId());
                    
                    // Sync to other peers
                    doc.sync({
                        type: 'draw',
                        path: currentPath,
                        color: '#ef4444',
                        timestamp: Date.now()
                    });
                    
                    status.textContent = 'Drawing synced!';
                    setTimeout(() => {
                        status.textContent = 'Connected';
                    }, 2000);
                }
                
                currentPath = [];
            });
            
            // Handle updates from other peers
            doc.onUpdate((data, fromPeer) => {
                console.log('Received update from:', fromPeer, data);
                
                if (data.type === 'draw' && data.path) {
                    // Draw other peer's path in different color
                    drawPath(data.path, '#3b82f6', fromPeer);
                    status.textContent = 'Received drawing from ' + fromPeer.slice(0, 8);
                    setTimeout(() => {
                        status.textContent = 'Connected';
                    }, 2000);
                }
            });
            
            // Connection events
            doc.onConnect(() => {
                status.textContent = 'Connected! Start drawing.';
                status.classList.remove('text-gray-500');
                status.classList.add('text-green-600');
            });
            
            doc.onDisconnect(() => {
                status.textContent = 'Disconnected';
                status.classList.remove('text-green-600');
                status.classList.add('text-red-500');
            });
            
            doc.onError((error) => {
                status.textContent = 'Error: ' + error.message;
                status.classList.add('text-red-500');
            });
        """),
    )


@rt("/static/starstream.js")
def serve_sdk():
    """Serve the StarStream SDK."""
    from starlette.responses import FileResponse
    import os

    sdk_path = os.path.join(os.path.dirname(__file__), "..", "starstream", "sdk", "starstream.js")
    return FileResponse(sdk_path, media_type="application/javascript")


@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, request):
    """Handle collaborative sync from SDK."""
    import json

    data = await request.json()
    peer_id = data.get("peer_id")
    delta_hex = data.get("delta")

    if not peer_id or not delta_hex:
        return {"error": "peer_id and delta required"}, 400

    # Convert hex to bytes
    delta_bytes = bytes.fromhex(delta_hex)

    # Sync with auto-broadcast
    success = await stream.collaborative.sync(doc_id, delta_bytes, peer_id)

    return {"success": success}


if __name__ == "__main__":
    print("🎨 Collaborative Canvas Example")
    print("=" * 50)
    print("Open: http://localhost:8000")
    print("Open multiple tabs to test real-time sync!")
    print("=" * 50)
    serve()
