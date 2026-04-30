import { useEffect, useRef, useState } from 'react';

import { getWebSocketUrl } from '../services/api';
import type { WebSocketEvent } from '../types/api';

export type LiveFeedStatus = 'connecting' | 'open' | 'reconnecting' | 'closed' | 'error';

interface UseLiveFeedOptions {
  onEvent?: (event: WebSocketEvent) => void;
}

interface LiveFeedState {
  status: LiveFeedStatus;
  lastEvent: WebSocketEvent | null;
  lastMessageAt: string | null;
  reconnectAttempt: number;
}

export function useLiveFeed(options: UseLiveFeedOptions = {}): LiveFeedState {
  const handlerRef = useRef(options.onEvent);
  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const [status, setStatus] = useState<LiveFeedStatus>('connecting');
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);
  const [lastMessageAt, setLastMessageAt] = useState<string | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  useEffect(() => {
    handlerRef.current = options.onEvent;
  }, [options.onEvent]);

  useEffect(() => {
    let closedByEffect = false;
    let attempt = 0;
    const wsUrl = getWebSocketUrl();

    function connect() {
      if (closedByEffect) {
        return;
      }
      setStatus(attempt === 0 ? 'connecting' : 'reconnecting');
      setReconnectAttempt(attempt);
      const websocket = new WebSocket(wsUrl);
      websocketRef.current = websocket;

      websocket.onopen = () => {
        attempt = 0;
        setReconnectAttempt(0);
        setStatus('open');
      };

      websocket.onmessage = (message) => {
        const parsed = parseEvent(message.data);
        if (!parsed) {
          return;
        }
        setLastEvent(parsed);
        setLastMessageAt(parsed.timestamp || new Date().toISOString());
        if (parsed.event === 'heartbeat' || parsed.event === 'ping') {
          sendPong(websocket, parsed.event);
        }
        handlerRef.current?.(parsed);
      };

      websocket.onerror = () => {
        setStatus('error');
      };

      websocket.onclose = () => {
        if (closedByEffect) {
          setStatus('closed');
          return;
        }
        attempt += 1;
        const delayMs = Math.min(30_000, 1_000 * 2 ** Math.min(attempt, 5));
        setStatus('reconnecting');
        setReconnectAttempt(attempt);
        reconnectTimerRef.current = window.setTimeout(connect, delayMs);
      };
    }

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      websocketRef.current?.close();
    };
  }, []);

  return { status, lastEvent, lastMessageAt, reconnectAttempt };
}

function parseEvent(payload: unknown): WebSocketEvent | null {
  if (typeof payload !== 'string') {
    return null;
  }
  try {
    const parsed = JSON.parse(payload) as WebSocketEvent;
    if (typeof parsed.event !== 'string') {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function sendPong(websocket: WebSocket, sourceEvent: string): void {
  if (websocket.readyState !== WebSocket.OPEN) {
    return;
  }
  websocket.send(
    JSON.stringify({
      event: 'pong',
      timestamp: new Date().toISOString(),
      data: { source_event: sourceEvent },
    }),
  );
}
