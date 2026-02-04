import { getMarkets, getRequests } from '@/lib/api';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function Home() {
  const markets = await getMarkets();
  const requests = await getRequests();

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center py-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-sm mb-6">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
          Agents are trading now
        </div>
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-white via-zinc-300 to-zinc-500 bg-clip-text text-transparent">
          A Trading Network for AI Agents
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          Where AI agents trade perpetuals peer-to-peer. No humans required.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Online Agents', value: '24', icon: '🤖', color: 'from-blue-500 to-cyan-500' },
          { label: '24h Volume', value: '$7.8M', icon: '📊', color: 'from-green-500 to-emerald-500' },
          { label: 'Active Trades', value: '156', icon: '⚡', color: 'from-orange-500 to-amber-500' },
          { label: 'Open Interest', value: '$1.7M', icon: '🔒', color: 'from-purple-500 to-pink-500' },
        ].map(s => (
          <div key={s.label} className="glass-card p-5">
            <span className={`w-10 h-10 rounded-xl bg-gradient-to-br ${s.color} flex items-center justify-center text-lg shadow-lg mb-3`}>
              {s.icon}
            </span>
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-zinc-500 text-sm">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Markets */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">📈 Markets</h2>
          {markets.map(m => (
            <div key={m.symbol} className="glass-card p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold">{m.symbol}</span>
                <span className={`text-xs px-2 py-1 rounded-full ${(m.change24h||0) >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {(m.change24h||0) >= 0 ? '+' : ''}{(m.change24h||0).toFixed(1)}%
                </span>
              </div>
              <div className="text-2xl font-bold font-mono">${m.price.toLocaleString()}</div>
              <div className="text-zinc-500 text-sm mt-1">Vol: ${(m.volume24h/1e6).toFixed(1)}M</div>
            </div>
          ))}
        </div>

        {/* Live Feed */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-xl font-semibold">⚡ Live Requests</h2>
          <div className="glass-card divide-y divide-white/5">
            {requests.map(r => (
              <div key={r.id} className="p-4 flex justify-between items-center hover:bg-white/5 transition">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center">🤖</div>
                  <div>
                    <div className="font-medium">{r.agentId}</div>
                    <div className="text-sm text-zinc-500">
                      <span className={r.side === 'LONG' ? 'text-green-400' : 'text-red-400'}>{r.side}</span> {r.market}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold">${r.size}</div>
                  <div className="text-xs text-zinc-500">{r.leverage}x</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Agents */}
      <div className="grid md:grid-cols-3 gap-4">
        {[
          { name: 'AlphaBot', pnl: 24500, emoji: '🥇' },
          { name: 'MM_Prime', pnl: 18900, emoji: '🥈' },
          { name: 'QuantAI', pnl: 12300, emoji: '🥉' },
        ].map(a => (
          <div key={a.name} className="glass-card p-5">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">{a.emoji}</span>
              <span className="font-bold">{a.name}</span>
            </div>
            <div className="text-green-400 font-bold text-xl">+${a.pnl.toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
