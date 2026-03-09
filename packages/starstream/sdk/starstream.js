/**
 * StarStream SDK - Zero-config real-time collaboration
 * 
 * Convention over Configuration: Just works, no setup needed.
 * 
 * @example
 * // Create a collaborative document
 * const doc = starstream.collaborative('my-canvas');
 * 
 * // Send updates (any JSON data)
 * doc.sync({ x: 100, y: 200, color: 'red' });
 * 
 * // Receive updates
 * doc.onUpdate((data, fromPeer) => {
 *   drawPixel(data.x, data.y, data.color);
 * });
 */

(function(global) {
  'use strict';

  /**
   * StarStream Collaborative Document
   * Manages real-time sync for a single document
   */
  class CollaborativeDoc {
    constructor(docId, options = {}) {
      this.docId = docId;
      this.options = {
        serverUrl: options.serverUrl || window.location.origin,
        peerId: options.peerId || this._generatePeerId(),
        debug: options.debug || false,
        ...options
      };
      
      this.eventSource = null;
      this.callbacks = {
        update: [],
        connect: [],
        disconnect: [],
        error: []
      };
      this.isConnected = false;
      this.buffer = []; // Buffer updates before connection
      
      this._log('Created collaborative doc:', docId);
      this._connect();
    }

    _generatePeerId() {
      return 'peer_' + Math.random().toString(36).substr(2, 9);
    }

    _log(...args) {
      if (this.options.debug) {
        console.log('[StarStream]', ...args);
      }
    }

    /**
     * Connect to SSE stream
     */
    _connect() {
      const topic = `doc:${this.docId}`;
      const url = `${this.options.serverUrl}/starstream?topic=${encodeURIComponent(topic)}`;
      
      this._log('Connecting to:', url);
      
      this.eventSource = new EventSource(url);
      
      this.eventSource.onopen = () => {
        this._log('Connected to stream');
        this.isConnected = true;
        this._flushBuffer();
        this._emit('connect', { peerId: this.options.peerId });
      };
      
      this.eventSource.onerror = (error) => {
        this._log('Connection error:', error);
        this.isConnected = false;
        this._emit('error', error);
      };
      
      this.eventSource.addEventListener('datastar-patch-signals', (event) => {
        this._handleSignal(event.data);
      });
    }

    /**
     * Handle incoming signal
     */
    _handleSignal(data) {
      try {
        // Parse Datastar signal format
        const lines = data.split('\n');
        let jsonStr = '';
        
        for (const line of lines) {
          if (line.startsWith('data: signals ')) {
            jsonStr += line.replace('data: signals ', '');
          } else if (line.startsWith('data: ') && jsonStr) {
            jsonStr += line.replace('data: ', '');
          }
        }
        
        if (!jsonStr) return;
        
        const signal = JSON.parse(jsonStr);
        
        // Check if it's a collaborative update
        if (signal.collaborative) {
          const { doc_id, delta, from_peer } = signal.collaborative;
          
          // Only process if it's for our document and from another peer
          if (doc_id === this.docId && from_peer !== this.options.peerId) {
            this._log('Received update from:', from_peer);
            
            // Decode delta (hex to bytes, then JSON)
            const data = this._decodeDelta(delta);
            
            // Emit to all listeners
            this._emit('update', data, from_peer);
          }
        }
      } catch (e) {
        this._log('Error handling signal:', e);
      }
    }

    /**
     * Decode delta from hex string to JSON
     */
    _decodeDelta(hexString) {
      try {
        // Convert hex to bytes
        const bytes = new Uint8Array(hexString.match(/.{2}/g).map(byte => parseInt(byte, 16)));
        // Convert bytes to string
        const str = new TextDecoder().decode(bytes);
        // Parse JSON
        return JSON.parse(str);
      } catch (e) {
        this._log('Error decoding delta:', e);
        return null;
      }
    }

    /**
     * Encode data to delta format
     */
    _encodeDelta(data) {
      // Convert JSON to bytes
      const str = JSON.stringify(data);
      const bytes = new TextEncoder().encode(str);
      // Convert bytes to hex
      return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Flush buffered updates
     */
    _flushBuffer() {
      while (this.buffer.length > 0) {
        const data = this.buffer.shift();
        this._sendToServer(data);
      }
    }

    /**
     * Send data to server
     */
    async _sendToServer(data) {
      const url = `${this.options.serverUrl}/doc/${encodeURIComponent(this.docId)}/sync?peer=${encodeURIComponent(this.options.peerId)}`;
      
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            peer_id: this.options.peerId,
            delta: this._encodeDelta(data)
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        this._log('Sync successful');
      } catch (e) {
        this._log('Sync failed:', e);
        this._emit('error', e);
      }
    }

    /**
     * Emit event to listeners
     */
    _emit(event, ...args) {
      if (this.callbacks[event]) {
        this.callbacks[event].forEach(cb => {
          try {
            cb(...args);
          } catch (e) {
            console.error('Error in callback:', e);
          }
        });
      }
    }

    /**
     * Sync data to server (and other peers)
     * @param {Object} data - Any JSON-serializable data
     */
    sync(data) {
      this._log('Syncing:', data);
      
      if (!this.isConnected) {
        this._log('Buffering (not connected yet)');
        this.buffer.push(data);
        return;
      }
      
      this._sendToServer(data);
    }

    /**
     * Register callback for updates from other peers
     * @param {Function} callback - (data, fromPeer) => void
     */
    onUpdate(callback) {
      this.callbacks.update.push(callback);
      return () => {
        const idx = this.callbacks.update.indexOf(callback);
        if (idx > -1) this.callbacks.update.splice(idx, 1);
      };
    }

    /**
     * Register callback for connection events
     * @param {Function} callback - () => void
     */
    onConnect(callback) {
      this.callbacks.connect.push(callback);
      if (this.isConnected) callback();
      return () => {
        const idx = this.callbacks.connect.indexOf(callback);
        if (idx > -1) this.callbacks.connect.splice(idx, 1);
      };
    }

    /**
     * Register callback for disconnection
     * @param {Function} callback - () => void
     */
    onDisconnect(callback) {
      this.callbacks.disconnect.push(callback);
      return () => {
        const idx = this.callbacks.disconnect.indexOf(callback);
        if (idx > -1) this.callbacks.disconnect.splice(idx, 1);
      };
    }

    /**
     * Register callback for errors
     * @param {Function} callback - (error) => void
     */
    onError(callback) {
      this.callbacks.error.push(callback);
      return () => {
        const idx = this.callbacks.error.indexOf(callback);
        if (idx > -1) this.callbacks.error.splice(idx, 1);
      };
    }

    /**
     * Get current peer ID
     */
    getPeerId() {
      return this.options.peerId;
    }

    /**
     * Disconnect and cleanup
     */
    destroy() {
      this._log('Destroying');
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
      this.isConnected = false;
      this.callbacks = { update: [], connect: [], disconnect: [], error: [] };
    }
  }

  /**
   * StarStream Global SDK
   */
  const starstream = {
    /**
     * Create a collaborative document
     * @param {string} docId - Document identifier
     * @param {Object} options - Configuration options
     * @returns {CollaborativeDoc}
     */
    collaborative(docId, options = {}) {
      return new CollaborativeDoc(docId, options);
    },

    /**
     * Version
     */
    version: '0.5.0'
  };

  // Expose globally
  global.starstream = starstream;

  // Also support module exports
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = starstream;
  }

})(typeof window !== 'undefined' ? window : global);
