import { WS_URL } from './config';
import type { ApiThought, ApiChatMessage } from './types';

type MessageHandler = (data: any) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    if (this.socket?.readyState === WebSocket.OPEN) return;

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log('[WS] Connected to', this.url);
        this.reconnectAttempts = 0;
        this.emit('open', null);
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;
          if (type) {
            this.emit(type, data || message);
          }
          // Also emit a general 'message' event
          this.emit('message', message);
        } catch (e) {
          console.error('[WS] Failed to parse message:', e);
        }
      };

      this.socket.onclose = () => {
        console.log('[WS] Disconnected');
        this.emit('close', null);
        this.handleReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('[WS] Error:', error);
        this.emit('error', error);
      };
    } catch (e) {
      console.error('[WS] Connection error:', e);
      this.handleReconnect();
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), this.reconnectDelay);
    }
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
    return () => this.off(type, handler);
  }

  off(type: string, handler: MessageHandler) {
    this.handlers.get(type)?.delete(handler);
  }

  private emit(type: string, data: any) {
    this.handlers.get(type)?.forEach(handler => handler(data));
  }

  send(type: string, data: any) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type, data }));
    } else {
      console.warn('[WS] Cannot send message: WebSocket is not open');
    }
  }

  close() {
    this.socket?.close();
    this.socket = null;
  }
}

export const wsClient = new WebSocketClient(WS_URL);
