'use client';

import { useWebSocket, Trade } from '@/hooks/useWebSocket';
import { Market, TradeRequest } from '@/lib/api';
import AgentThoughts from './AgentThoughts';
import { Bot, BarChart3, Zap, Lock, TrendingUp, TrendingDown, Activity, MessageCircle } from 'lucide-react';
import { ReactNode } from 'react';

interface LiveDashboardProps {
  initialMarkets: Market[];
  initialRequests: TradeRequest[];
  hideMarkets?: boolean;
  hideStats?: boolean;
}

export default function LiveDashboard({ initialMarkets, initialRequests, hideMarkets, hideStats }: LiveDashboardProps) {
  const { data, isConnected, error, reconnect } = useWebSocket({
    markets: initialMarkets,
    requests: initialRequests,
  });

  const { markets, requests, trades } = data;

  // Calculate stats from live data
  const stats: { label: string; value: string; icon: ReactNode; color: string }[] = [
    { label: 'Online Agents', value: String(data.onlineCount ?? markets.length), icon: <Bot className="w-5 h-5" />, color: 'from-blue-500 to-cyan-500' },
    { label: '24h Volume', value: `$${(markets.reduce((s, m) => s + m.volume24h, 0) / 1e6).toFixed(1)}M`, icon: <BarChart3 className="w-5 h-5" />, color: 'from-green-500 to-emerald-500' },
    { label: 'Active Requests', value: String(requests.length), icon: <Zap className="w-5 h-5" />, color: 'from-orange-500 to-amber-500' },
    { label: 'Open Interest', value: `$${(markets.reduce((s, m) => s + m.openInterest, 0) / 1e6).toFixed(1)}M`, icon: <Lock className="w-5 h-5" />, color: 'from-purple-500 to-pink-500' },
  ];

  return (
    <div className="space-y-8">
      {/* Connection Status */}
      <div className="flex items-center justify-between">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-rb-cyan/10 border border-rb-cyan/20 text-rb-cyan text-sm">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-rb-green' : 'bg-rb-red'} animate-pulse`}></span>
          {isConnected ? 'Live' : 'Disconnected'}
        </div>
        {error && (
          <button
            onClick={reconnect}
            className="text-sm text-rb-red hover:text-rb-red/80 underline"
          >
            {error}
          </button>
        )}
      </div>

      {/* Stats */}
      {!hideStats && (
        <div className="grid grid-cols-4 gap-4">
          {stats.map(s => (
            <div key={s.label} className="glass-card p-5">
              <span className={`w-10 h-10 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center text-white shadow-lg mb-3`}>
                {s.icon}
              </span>
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-rb-text-secondary text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className={hideMarkets ? 'space-y-6' : 'grid lg:grid-cols-3 gap-6'}>
        {/* Markets */}
        {!hideMarkets && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-rb-cyan" /> Markets
              {isConnected && <span className="w-2 h-2 rounded-full bg-rb-green animate-pulse"></span>}
            </h2>
            {markets.map(m => (
              <div key={m.symbol} className="glass-card p-4 transition-all hover:scale-[1.02]">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold">{m.symbol}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${(m.change24h || 0) >= 0 ? 'bg-rb-green/20 text-rb-green' : 'bg-rb-red/20 text-rb-red'}`}>
                    {(m.change24h || 0) >= 0 ? '+' : ''}{(m.change24h || 0).toFixed(1)}%
                  </span>
                </div>
                <div className="text-2xl font-bold font-mono">${m.price.toLocaleString()}</div>
                <div className="text-rb-text-secondary text-sm mt-1">Vol: ${(m.volume24h / 1e6).toFixed(1)}M</div>
              </div>
            ))}
          </div>
        )}

        {/* Live Requests & Trades */}
        <div className={hideMarkets ? 'space-y-6' : 'lg:col-span-2 space-y-6'}>
          {/* Active Requests */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Zap className="w-5 h-5 text-rb-red" /> Live Requests
              <span className="text-sm font-normal text-rb-text-secondary">({requests.length})</span>
            </h2>
            <div className="glass-card divide-y divide-layer-3 max-h-[300px] overflow-y-auto">
              {requests.length === 0 ? (
                <div className="p-6 text-center text-rb-text-secondary">No active requests</div>
              ) : (
                requests.map(r => (
                  <div key={r.id} className="p-4 hover:bg-layer-3/30 transition animate-in fade-in duration-300">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-layer-4 flex items-center justify-center">
                          <Bot className="w-5 h-5 text-rb-text-secondary" />
                        </div>
                        <div>
                          <div className="font-medium">{r.agentId}</div>
                          <div className="text-sm text-rb-text-secondary">
                            <span className={r.side === 'LONG' ? 'text-rb-green' : 'text-rb-red'}>{r.side}</span> {r.market}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">${r.size.toLocaleString()}</div>
                        <div className="text-xs text-rb-text-secondary">{r.leverage}x</div>
                      </div>
                    </div>
                    {r.reason && (
                      <div className="mt-2 ml-13 pl-13 flex items-start gap-2 text-sm">
                        <MessageCircle className="w-4 h-4 text-rb-text-secondary shrink-0" />
                        <span className="text-rb-text-secondary italic truncate">"{r.reason}"</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Trades */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-rb-cyan" /> Recent Trades
              <span className="text-sm font-normal text-rb-text-secondary">({trades.length})</span>
            </h2>
            <div className="glass-card divide-y divide-layer-3 max-h-[250px] overflow-y-auto">
              {trades.length === 0 ? (
                <div className="p-6 text-center text-rb-text-secondary">No recent trades</div>
              ) : (
                trades.slice(0, 10).map(t => (
                  <div key={t.id} className="p-3 flex justify-between items-center hover:bg-layer-3/30 transition">
                    <div className="flex items-center gap-3">
                      <span className={`${t.side === 'LONG' ? 'text-rb-green' : 'text-rb-red'}`}>
                        {t.side === 'LONG' ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                      </span>
                      <div>
                        <div className="font-medium text-sm">{t.market}</div>
                        <div className="text-xs text-rb-text-secondary">{t.agentId}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-sm">${t.price.toLocaleString()}</div>
                      <div className="text-xs text-rb-text-secondary">${t.size.toLocaleString()}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Agent Thoughts Section */}
      <div className="mt-6">
        <AgentThoughts requests={requests} maxItems={8} />
      </div>
    </div>
  );
}
