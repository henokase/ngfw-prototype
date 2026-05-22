import { useEffect, useRef, useCallback } from 'react';

const SSE_URL = 'http://192.168.1.70:5001/api/stream';

export type SSEEventType = 'service_update' | 'block_update' | 'log_new' | 'ml_prediction' | 'malware_alert' | 'system_update';

export interface SSEMessage {
  type: SSEEventType;
  services?: Array<{ name: string; status: string }>;
  blocks?: Array<{ id: number; ip: string; reason: string; ttl: string; timestamp: string }>;
  stats?: {
    cpu_load: number;
    memory_percent: number;
    events_today: number;
    active_threats: number;
  };
  connections?: number;
  packets_in?: number;
  packets_out?: number;
  bytes_in?: number;
  bytes_out?: number;
  malwareDetected?: number;
  ml_prediction?: boolean;
  [key: string]: unknown;
}

type SSEHandler = (data: SSEMessage) => void;

class SSEManager {
  private connections: Map<string, EventSource> = new Map();
  private handlers: Map<string, Set<SSEHandler>> = new Map();
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  connect(event: string, handler: SSEHandler): () => void {
    if (this.connections.has(event)) {
      const handlers = this.handlers.get(event);
      if (handlers) {
        handlers.add(handler);
      }
      return () => this.disconnect(event, handler);
    }

    const handlers = new Set<SSEHandler>();
    handlers.add(handler);
    this.handlers.set(event, handlers);

    const eventSource = new EventSource(`${SSE_URL}?event=${event}`);
    this.connections.set(event, eventSource);

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const eventHandlers = this.handlers.get(event);
        if (eventHandlers) {
          eventHandlers.forEach((h) => h(data));
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = () => {
      console.warn(`SSE connection error for ${event}, attempting reconnect...`);
      this.handleDisconnect(event);
    };

    return () => this.disconnect(event, handler);
  }

  private handleDisconnect(event: string): void {
    this.disconnect(event);
    
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectTimeout = setTimeout(() => {
        this.reconnectAttempts++;
        const handlers = this.handlers.get(event);
        if (handlers && handlers.size > 0) {
          handlers.forEach((handler) => this.connect(event, handler));
        }
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect(event: string, handler?: SSEHandler): void {
    if (handler) {
      const handlers = this.handlers.get(event);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(event);
          this.closeConnection(event);
        }
      }
    } else {
      this.handlers.delete(event);
      this.closeConnection(event);
    }
  }

  private closeConnection(event: string): void {
    const eventSource = this.connections.get(event);
    if (eventSource) {
      eventSource.close();
      this.connections.delete(event);
    }
  }

  disconnectAll(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    this.connections.forEach((es) => es.close());
    this.connections.clear();
    this.handlers.clear();
    this.reconnectAttempts = 0;
  }

  isConnected(event: string): boolean {
    const es = this.connections.get(event);
    return es !== undefined && es.readyState === EventSource.OPEN;
  }

  getConnectionState(event: string): number {
    const es = this.connections.get(event);
    return es?.readyState ?? EventSource.CLOSED;
  }
}

export const sseManager = new SSEManager();

export function useSSE(event: string, handler: SSEHandler, enabled = true) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  const stableHandler = useCallback((data: SSEMessage) => {
    handlerRef.current(data);
  }, []);

  useEffect(() => {
    if (!enabled) return () => {};

    return sseManager.connect(event, stableHandler);
  }, [event, stableHandler, enabled]);

  return {
    isConnected: sseManager.isConnected(event),
    state: sseManager.getConnectionState(event),
  };
}

export function createSSEConnection(event: string, handler: SSEHandler): () => void {
  return sseManager.connect(event, handler);
}

export function closeSSEConnection(event: string): void {
  sseManager.disconnect(event);
}

export function closeAllSSEConnections(): void {
  sseManager.disconnectAll();
}