'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Market, TradeRequest } from '@/lib/api';
import { WS_URL as CONFIG_WS_URL } from '@/lib/config';
import { ApiThought, ApiChatMessage } from '@/lib/types';

const WS_URL = CONFIG_WS_URL;

// 性能优化：消息节流（每 100ms 最多更新一次 UI）
const THROTTLE_MS = 100;
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;
const KNOWN_BUT_UNUSED_TYPES = new Set<string>([
  'connected',
  'pnl_update',
  'new_agent',
  'new_match',
  'external_fill',
  'signal_created',
  'signal_faded',
  'bet_settled',
  'liquidation',
  'pong',
]);

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
  thoughts: ApiThought[];
  messages: ApiChatMessage[];
  onlineCount: number;
}

export interface UseWebSocketReturn {
  data: WSData;
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
  sendMessage: (type: string, data: any) => void;
}

export function useWebSocket(initialData?: Partial<WSData>): UseWebSocketReturn {
  const [data, setData] = useState<WSData>({
    markets: initialData?.markets || [],
    requests: initialData?.requests || [],
    trades: initialData?.trades || [],
    thoughts: initialData?.thoughts || [],
    messages: initialData?.messages || [],
    onlineCount: initialData?.onlineCount || 0,
  });
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const unknownTypesLogged = useRef<Set<string>>(new Set());
  const shouldReconnect = useRef(true);
  const intentionalClose = useRef(false);
  
  // 节流相关
  const pendingUpdates = useRef<Partial<WSData>>({});
  const throttleTimeout = useRef<NodeJS.Timeout | null>(null);
  
  // 节流更新函数
  const throttledSetData = useCallback((updates: Partial<WSData>) => {
    // 合并 pending updates
    pendingUpdates.current = {
      ...pendingUpdates.current,
      ...updates,
    };
    
    // 如果没有 pending 的更新，设置定时器
    if (!throttleTimeout.current) {
      throttleTimeout.current = setTimeout(() => {
        setData(prev => ({
          ...prev,
          ...pendingUpdates.current,
        }));
        pendingUpdates.current = {};
        throttleTimeout.current = null;
      }, THROTTLE_MS);
    }
  }, []);

  const connect = useCallback(() => {
    // Cleanup existing connection and reconnect timers
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (wsRef.current) {
      intentionalClose.current = true;
      wsRef.current.close(1000, 'Reconnecting');
      wsRef.current = null;
    }

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      shouldReconnect.current = true;

      ws.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        unknownTypesLogged.current.clear();
        intentionalClose.current = false;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          switch (msg.type) {
            case 'markets':
            case 'market_update':
              if (Array.isArray(msg.data)) {
                throttledSetData({
                  markets: msg.data.map(parseMarket),
                });
              }
              break;

            case 'requests':
            case 'request_update':
              if (Array.isArray(msg.data)) {
                throttledSetData({
                  requests: msg.data.map(parseRequest),
                });
              }
              break;

            case 'new_request':
            case 'new_intent':
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

            case 'thought':
            case 'new_thought':
            case 'agent_thought':
              if (msg.data) {
                setData(prev => ({
                  ...prev,
                  thoughts: [parseThought(msg.data), ...prev.thoughts].slice(0, 50),
                }));
              }
              break;

            case 'chat':
            case 'chat_message':
            case 'new_message':
              if (msg.data) {
                setData(prev => ({
                  ...prev,
                  messages: [...prev.messages, parseChatMessage(msg.data)].slice(-100),
                }));
              }
              break;

            case 'online_agents':
            case 'stats_update':
              if (msg.data?.count !== undefined) {
                setData(prev => ({ ...prev, onlineCount: msg.data.count }));
              }
              break;

            case 'snapshot':
              // Full state snapshot
              setData(prev => ({
                markets: Array.isArray(msg.markets) ? msg.markets.map(parseMarket) : prev.markets,
                requests: Array.isArray(msg.requests) ? msg.requests.map(parseRequest) : prev.requests,
                trades: Array.isArray(msg.trades) ? msg.trades.map(parseTrade) : prev.trades,
                thoughts: Array.isArray(msg.thoughts) ? msg.thoughts.map(parseThought) : prev.thoughts,
                messages: Array.isArray(msg.messages) ? msg.messages.map(parseChatMessage) : prev.messages,
                onlineCount: msg.online_count ?? prev.onlineCount,
              }));
              break;

            case 'intent_cancelled':
              if (msg.data?.intent_id) {
                setData(prev => ({
                  ...prev,
                  requests: prev.requests.filter(req => req.id !== msg.data.intent_id),
                }));
              }
              break;

            case 'circle_post':
            case 'circle_vote':
              // Circles events — handled by page-level polling for now
              break;

            case 'connected':
            case 'pnl_update':
            case 'new_agent':
            case 'new_match':
            case 'external_fill':
            case 'signal_created':
            case 'signal_faded':
            case 'bet_settled':
            case 'liquidation':
            case 'pong':
              // 已知消息类型，当前前端无需处理；避免控制台刷屏
              break;

            default:
              if (typeof msg.type === 'string' && !KNOWN_BUT_UNUSED_TYPES.has(msg.type)) {
                if (!unknownTypesLogged.current.has(msg.type)) {
                  unknownTypesLogged.current.add(msg.type);
                  console.warn('[WS] Unknown message type (first seen):', msg.type);
                }
              }
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = (event) => {
        const wasIntentional = intentionalClose.current;
        intentionalClose.current = false;
        console.log('[WS] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        if (wasIntentional || !shouldReconnect.current) {
          return;
        }

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
        if (intentionalClose.current || !shouldReconnect.current) {
          return;
        }
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
    shouldReconnect.current = true;
    connect();
  }, [connect]);

  const sendMessage = useCallback((type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    } else {
      console.warn('[WS] Cannot send message: WebSocket is not open');
    }
  }, []);

  useEffect(() => {
    // Avoid duplicate connection churn in React StrictMode dev cycle.
    const startTimer = setTimeout(() => {
      connect();
    }, 0);

    return () => {
      shouldReconnect.current = false;
      clearTimeout(startTimer);

      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      if (throttleTimeout.current) {
        clearTimeout(throttleTimeout.current);
        throttleTimeout.current = null;
      }
      if (pendingUpdates.current && Object.keys(pendingUpdates.current).length > 0) {
        pendingUpdates.current = {};
      }
      if (wsRef.current) {
        intentionalClose.current = true;
        wsRef.current.close(1000, 'Component unmount');
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { data, isConnected, error, reconnect, sendMessage };
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
    reason: r.reason || r.rationale || undefined,
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

function parseThought(t: any): ApiThought {
  return {
    id: t.id || `thought_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    agent_id: t.agent_id || t.sender_id || 'Unknown',
    agent_name: t.agent_name || t.sender_name || t.agent_id || t.sender_id || 'Unknown',
    thought: t.thought || t.reason || t.content || t.action || '',
    metadata: t.metadata || {},
    timestamp: t.timestamp || t.created_at || new Date().toISOString(),
  };
}

function parseChatMessage(m: any): ApiChatMessage {
  const rawType = typeof m.message_type === 'string' ? m.message_type : 'text';
  const normalizedType = (
    rawType === 'thought' ||
    rawType === 'signal' ||
    rawType === 'challenge' ||
    rawType === 'system' ||
    rawType === 'text'
  ) ? rawType : 'text';

  return {
    id: m.id || `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    sender_id: m.sender_id || 'system',
    sender_name: m.sender_name || m.sender_id || 'System',
    channel: m.channel || 'public',
    message_type: normalizedType,
    content: m.content || '',
    metadata: m.metadata || {},
    created_at: m.created_at || m.timestamp || new Date().toISOString(),
  };
}
