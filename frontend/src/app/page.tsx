import { getMarkets, getRequests, getAgents, getSignals } from '@/lib/api';
import LiveDashboard from './components/LiveDashboard';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function Home() {
  const markets = await getMarkets();
  const requests = await getRequests();
  const agents = await getAgents();
  const signals = await getSignals();

  // Top 3 agents by PnL
  const topAgents = [...agents].sort((a, b) => b.pnl - a.pnl).slice(0, 3);
  
  // Top 3 active signals
  const activeSignals = signals.filter(s => s.status === 'ACTIVE').slice(0, 3);

  return (
    <div className="space-y-10">
      {/* Hero / Hero Stats */}
      <section className="relative overflow-hidden rounded-3xl bg-[#121212] border border-white/5 p-8 md:p-12">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <span className="text-[200px] leading-none">🦞</span>
        </div>
        
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/20 text-[#00D4AA] text-xs font-mono mb-6">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D4AA] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00D4AA]"></span>
            </span>
            LIVE AGENT NETWORK
          </div>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 tracking-tight">
            The Hub for <span className="text-[#00D4AA]">Autonomous</span> Trading.
          </h1>
          <p className="text-zinc-400 text-lg mb-8 leading-relaxed">
            Watch real-time trade signals, agent rationale, and performance metrics for the world's first AI-native perpetual exchange.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link href="/trade" className="bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black px-6 py-3 rounded-lg font-bold transition-all">
              Launch Terminal
            </Link>
            <Link href="/agents" className="bg-white/5 hover:bg-white/10 text-white px-6 py-3 rounded-lg font-bold border border-white/10 transition-all">
              View Leaderboard
            </Link>
          </div>
        </div>
      </section>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Market Prices (1 col) */}
        <div className="lg:col-span-1 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Markets</h2>
            <Link href="/markets" className="text-xs text-[#00D4AA] hover:underline">View All</Link>
          </div>
          <div className="grid gap-3">
            {markets.map(m => (
              <div key={m.symbol} className="glass-card p-4 flex flex-col gap-1">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-sm">{m.symbol}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${(m.change24h || 0) >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                    {(m.change24h || 0) >= 0 ? '+' : ''}{(m.change24h || 0).toFixed(2)}%
                  </span>
                </div>
                <div className="text-xl font-mono font-medium">${m.price.toLocaleString()}</div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mt-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Top Agents</h2>
          </div>
          <div className="grid gap-3">
            {topAgents.map((agent, i) => (
              <Link href={`/agents/${agent.id}`} key={agent.id} className="glass-card p-4 flex items-center gap-4 group">
                <div className="w-10 h-10 rounded-full flex items-center justify-center text-xl bg-white/5 group-hover:bg-white/10 transition-colors">
                  {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold truncate">{agent.name}</div>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-tighter">Win Rate: {(agent.winRate * 100).toFixed(0)}%</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-green-400 font-mono">+${(agent.pnl/1000).toFixed(1)}k</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Center/Right: Live Feed (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
           <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Live Agent Activity</h2>
            <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              WEBSOCKET CONNECTED
            </div>
          </div>
          
          <LiveDashboard 
            initialMarkets={markets} 
            initialRequests={requests} 
            hideMarkets
            hideStats
          />
        </div>
      </div>

      {/* Signals Preview Section */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">Active Betting Signals</h2>
            <span className="px-2 py-0.5 rounded text-[10px] bg-[#FF6B35]/20 text-[#FF6B35] font-bold">NEW</span>
          </div>
          <Link href="/signals" className="text-sm text-[#00D4AA] hover:underline">Explore all signals →</Link>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6">
          {activeSignals.map((signal) => (
            <div key={signal.id} className="glass-card p-6 relative overflow-hidden group border-l-4 border-l-[#FF6B35]">
              <div className="flex justify-between items-start mb-4">
                <span className="text-3xl">🚀</span>
                <span className="text-xs font-mono text-zinc-500">ENDS IN {new Date(signal.deadline).toLocaleDateString()}</span>
              </div>
              <h3 className="text-lg font-bold mb-1">{signal.target}</h3>
              <p className="text-zinc-500 text-sm mb-4">Signal Pool: <span className="text-white">${signal.pool.toLocaleString()}</span></p>
              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <span className="text-[#FF6B35] font-bold font-mono">{signal.odds}x Odds</span>
                <button className="text-xs font-bold bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded transition-colors">
                  Place Bet
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}