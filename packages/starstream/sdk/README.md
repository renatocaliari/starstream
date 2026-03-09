# StarStream SDK - Zero-Config Real-Time Collaboration

The StarStream JavaScript SDK provides **zero-configuration real-time collaboration** with an intuitive, Datastar-like API.

## Quick Start

### 1. Include the SDK

```html
<script src="https://cdn.jsdelivr.net/gh/renatocaliari/starstream@main/packages/starstream/sdk/starstream.js"></script>
```

### 2. Create a Collaborative Document

```javascript
// Create a collaborative document
const doc = starstream.collaborative('my-canvas');
```

### 3. Sync Data (Any JSON)

```javascript
// Send any JSON-serializable data
doc.sync({ 
  x: 100, 
  y: 200, 
  color: 'red',
  action: 'draw' 
});
```

### 4. Receive Updates

```javascript
// Handle updates from other peers
doc.onUpdate((data, fromPeer) => {
  console.log('Received from', fromPeer, ':', data);
  // Update your UI
});
```

## Complete Example: Collaborative Canvas

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/gh/renatocaliari/starstream@main/packages/starstream/sdk/starstream.js"></script>
</head>
<body>
  <canvas id="myCanvas" width="800" height="600"></canvas>
  
  <script>
    // Initialize collaborative canvas
    const doc = starstream.collaborative('canvas-1');
    const canvas = document.getElementById('myCanvas');
    const ctx = canvas.getContext('2d');
    
    // When user draws
    canvas.addEventListener('click', (e) => {
      const rect = canvas.getBoundingClientRect();
      const data = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        color: 'blue'
      };
      
      // Draw locally
      drawPixel(data.x, data.y, data.color);
      
      // Sync to other peers automatically
      doc.sync(data);
    });
    
    // When other peers draw
    doc.onUpdate((data, fromPeer) => {
      drawPixel(data.x, data.y, data.color);
    });
    
    function drawPixel(x, y, color) {
      ctx.fillStyle = color;
      ctx.fillRect(x, y, 5, 5);
    }
  </script>
</body>
</html>
```

## Server-Side Setup (Python)

```python
from starhtml import star_app, rt
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app, collaborative=True)

# That's it! The SDK endpoint is auto-registered.
# Just serve your HTML that uses the SDK.

@rt("/")
def home():
    return """
    <script src="starstream.js"></script>
    <script>
        const doc = starstream.collaborative('my-doc');
        // ... your code
    </script>
    """
```

## API Reference

### `starstream.collaborative(docId, options)`

Creates a collaborative document connection.

**Parameters:**
- `docId` (string): Unique document identifier
- `options` (object, optional):
  - `serverUrl`: Server URL (default: current origin)
  - `peerId`: Custom peer ID (auto-generated if not provided)
  - `debug`: Enable debug logging (default: false)

**Returns:** `CollaborativeDoc` instance

### `doc.sync(data)`

Synchronizes data to all connected peers.

**Parameters:**
- `data` (object): Any JSON-serializable data

### `doc.onUpdate(callback)`

Registers callback for incoming updates.

**Parameters:**
- `callback` (function): `(data, fromPeer) => void`

**Returns:** Unsubscribe function

### `doc.onConnect(callback)`

Called when connection is established.

### `doc.onDisconnect(callback)`

Called when connection is lost.

### `doc.onError(callback)`

Called on connection errors.

### `doc.getPeerId()`

Returns current peer ID.

### `doc.destroy()`

Clean up and disconnect.

## How It Works

1. **Automatic Connection**: SDK connects to StarStream SSE endpoint automatically
2. **JSON Encoding**: Your data is automatically encoded for transmission
3. **Broadcast**: Server broadcasts to all peers subscribed to the same document
4. **Receive**: Other peers receive updates via SSE and trigger your callback

**Note:** Loro CRDT is used under the hood for conflict resolution, but you never interact with it directly. Just send and receive JSON!

## Convention over Configuration

- **No setup required**: Include script and start collaborating
- **Auto-generated peer IDs**: Each tab gets unique ID automatically
- **Auto-reconnection**: Handles connection drops gracefully
- **JSON everywhere**: No special data formats needed

## Browser Support

Works in all modern browsers with EventSource support:
- Chrome/Edge
- Firefox
- Safari

## License

MIT - See main project license
