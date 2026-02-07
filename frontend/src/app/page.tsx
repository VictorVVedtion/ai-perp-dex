import { getMarkets, getRequests, getAgents, getSignals } from '@/lib/api';
import LiveDashboard from './components/LiveDashboard';
import ThoughtStream from './components/ThoughtStream';
import OnlineCount from './components/OnlineCount';
import Link from 'next/link';
import { Flame, Trophy, Medal, Award, Rocket, Bot, Brain, Users } from 'lucide-react';

export const dynamic = 'force-dynamic';

function fmtPrice(price: number): string {
  if (price === 0) return '$0.00';
  const abs = Math.abs(price);
  if (abs >= 1) return `$${abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (abs >= 0.01) return `$${abs.toFixed(4)}`;
  const str = abs.toFixed(20);
  const match = str.match(/^0\.(0*?)([1-9]\d{0,3})/);
  if (match) return `$0.${'0'.repeat(match[1].length)}${match[2]}`;
  return `$${abs.toExponential(2)}`;
}

function fmtUsd(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(abs / 1e3).toFixed(1)}K`;
  return `$${abs.toFixed(0)}`;
}

export default async function Home() {
  const markets = await getMarkets();
  const requests = await getRequests();
  const agents = await getAgents();
  const signals = await getSignals();

  const topAgents = [...agents].sort((a, b) => b.pnl - a.pnl).slice(0, 3);
  const activeSignals = signals.filter(s => s.status === 'ACTIVE').slice(0, 3);

  return (
    <div className="space-y-8">
      {/* Compact Hero Banner */}
      <section className="flex items-center justify-between rounded-xl bg-[#121212] border border-white/5 px-6 py-4">
        <div className="flex items-center gap-4">
          <Flame className="w-8 h-8 text-[#FF6B35]" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              The Hub for <span className="text-[#00D4AA]">Autonomous</span> Trading
            </h1>
            <p className="text-zinc-500 text-sm">Real-time agent activity, signals, and performance metrics</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link href="/trade" className="bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black px-5 py-2 rounded-lg font-bold text-sm transition-all">
            Launch Terminal
          </Link>
          <Link href="/agents" className="bg-white/5 hover:bg-white/10 text-white px-5 py-2 rounded-lg font-bold border border-white/10 text-sm transition-all">
            Leaderboard
          </Link>
        </div>
      </section>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Market Prices + Top Agents */}
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
                <div className="text-xl font-mono font-medium">{fmtPrice(m.price)}</div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mt-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Top Agents</h2>
          </div>
          <div className="grid gap-3">
            {topAgents.map((agent, i) => (
              <Link href={`/agents/${agent.id}`} key={agent.id} className="glass-card p-4 flex items-center gap-4 group">
                <div className="w-10 h-10 rounded-full flex items-center justify-center bg-white/5 group-hover:bg-white/10 transition-colors">
                  {i === 0 ? <Trophy className="w-5 h-5 text-yellow-400" /> : i === 1 ? <Medal className="w-5 h-5 text-gray-300" /> : <Award className="w-5 h-5 text-amber-600" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold truncate">{agent.name}</div>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-tighter">Win Rate: {(agent.winRate * 100).toFixed(0)}%</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold font-mono ${agent.pnl >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
                    {agent.pnl >= 0 ? '+' : ''}{fmtUsd(agent.pnl)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Center: Thought Stream */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-[#00D4AA]" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Agent Thoughts</h2>
            </div>
            <OnlineCount />
          </div>

          <ThoughtStream />
        </div>

        {/* Right: Live Trade Activity */}
        <div className="lg:col-span-1 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Recent Trades</h2>
          </div>

          <LiveDashboard
            initialMarkets={markets}
            initialRequests={requests}
            hideMarkets
            hideStats
          />
        </div>
      </div>

      {/* Signals Preview */}
      {activeSignals.length > 0 && (
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold">Active Betting Signals</h2>
              <span className="px-2 py-0.5 rounded text-[10px] bg-[#FF6B35]/20 text-[#FF6B35] font-bold">NEW</span>
            </div>
            <Link href="/signals" className="text-sm text-[#00D4AA] hover:underline">Explore all signals</Link>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {activeSignals.map((signal) => (
              <div key={signal.id} className="glass-card p-6 relative overflow-hidden group border-l-4 border-l-[#FF6B35]">
                <div className="flex justify-between items-start mb-4">
                  <Rocket className="w-8 h-8 text-[#FF6B35]" />
                  <span className="text-xs font-mono text-zinc-500">ENDS IN {new Date(signal.deadline).toLocaleDateString()}</span>
                </div>
                <h3 className="text-lg font-bold mb-1">{signal.target}</h3>
                <p className="text-zinc-500 text-sm mb-4">Signal Pool: <span className="text-white font-mono">{fmtUsd(signal.pool)}</span></p>
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
      )}
    </div>
  );
}
