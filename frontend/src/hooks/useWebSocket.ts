'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Market, TradeRequest } from '@/lib/api';

const WS_URL = 'ws://localhost:8080/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export interface Trade {
  id: string;
  market: string;
  side: 'LONG' | 'SHORT';
  size: number;
  price: number;
  agentId: string;
  timestamp: number;
}

export interface WSData {
  markets: Market[];
  requests: TradeRequest[];
  trades: Trade[];
}

export interface UseWebSocketReturn {
  data: WSData;
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
}

export function useWebSocket(initialData?: Partial<WSData>): UseWebSocketReturn {
  const [data, setData] = useState<WSData>({
    markets: initialData?.markets || [],
    requests: initialData?.requests || [],
    trades: initialData?.trades || [],
  });
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Cleanup existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          switch (msg.type) {
            case 'markets':
            case 'market_update':
              setData(prev => ({
                ...prev,
                markets: Array.isArray(msg.data) ? msg.data.map(parseMarket) : prev.markets,
              }));
              break;

            case 'requests':
            case 'request_update':
              setData(prev => ({
                ...prev,
                requests: Array.isArray(msg.data) ? msg.data.map(parseRequest) : prev.requests,
              }));
              break;

            case 'new_request':
              if (msg.data) {
                setData(prev => ({
                  ...prev,
                  requests: [parseRequest(msg.data), ...prev.requests].slice(0, 20),
                }));
              }
              break;

            case 'trade':
            case 'new_trade':
              if (msg.data) {
                setData(prev => ({
                  ...prev,
                  trades: [parseTrade(msg.data), ...prev.trades].slice(0, 50),
                }));
              }
              break;

            case 'snapshot':
              // Full state snapshot
              setData({
                markets: Array.isArray(msg.markets) ? msg.markets.map(parseMarket) : data.markets,
                requests: Array.isArray(msg.requests) ? msg.requests.map(parseRequest) : data.requests,
                trades: Array.isArray(msg.trades) ? msg.trades.map(parseTrade) : data.trades,
              });
              break;

            default:
              console.log('[WS] Unknown message type:', msg.type);
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Auto reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          const delay = RECONNECT_DELAY * reconnectAttempts.current;
          console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
          
          reconnectTimeout.current = setTimeout(connect, delay);
        } else {
          setError('Connection lost. Click to reconnect.');
        }
      };

      ws.onerror = (event) => {
        console.error('[WS] Error:', event);
        setError('WebSocket error');
      };

    } catch (e) {
      console.error('[WS] Connection failed:', e);
      setError('Failed to connect');
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    setError(null);
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { data, isConnected, error, reconnect };
}

// Parsers for backend data
function parseMarket(m: any): Market {
  return {
    symbol: m.market || m.symbol || 'UNKNOWN',
    price: m.current_price || m.price || 0,
    volume24h: m.volume_24h || m.volume24h || 0,
    openInterest: m.open_interest || m.openInterest || 0,
    change24h: m.change_24h || m.change24h || (Math.random() - 0.3) * 5,
  };
}

function parseRequest(r: any): TradeRequest {
  return {
    id: r.id || `req_${Date.now()}`,
    agentId: r.agent_id || r.agentId || 'Unknown',
    market: r.market || 'BTC-PERP',
    side: (r.side?.toUpperCase() || 'LONG') as 'LONG' | 'SHORT',
    size: r.size_usdc || r.size || 0,
    leverage: r.leverage || 1,
  };
}

function parseTrade(t: any): Trade {
  return {
    id: t.id || `trade_${Date.now()}`,
    market: t.market || 'BTC-PERP',
    side: (t.side?.toUpperCase() || 'LONG') as 'LONG' | 'SHORT',
    size: t.size || 0,
    price: t.price || 0,
    agentId: t.agent_id || t.agentId || 'Unknown',
    timestamp: t.timestamp || Date.now(),
  };
}
