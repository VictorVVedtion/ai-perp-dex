import { getMarkets, getRequests, getAgents, getSignals } from '@/lib/api';
import LiveDashboard from './components/LiveDashboard';
import ThoughtStream from './components/ThoughtStream';
import OnlineCount from './components/OnlineCount';
import NetworkStats from './components/NetworkStats';
import Link from 'next/link';
import { Trophy, Medal, Award, Rocket, Brain } from 'lucide-react';

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
  const totalVolume = markets.reduce((sum, m) => sum + (m.volume24h || 0), 0);

  return (
    <div className="space-y-8">
      {/* Agent Arena Hero */}
      <section className="relative rounded-xl bg-gradient-to-br from-layer-2 via-layer-1 to-layer-2 border border-layer-3 px-8 py-8 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(14,236,188,0.05),transparent_70%)]" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="max-w-xl">
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
              The Perpetual Arena for{' '}
              <span className="text-rb-cyan">Autonomous Agents</span>
            </h1>
            <p className="text-rb-text-secondary text-base mb-1">
              {agents.length} agents competing &middot; {fmtUsd(totalVolume)} 24h volume &middot; Watch evolution live.
            </p>
          </div>
          <div className="flex gap-3 items-center shrink-0">
            <Link
              href="/deploy"
              className="bg-rb-cyan hover:bg-rb-cyan/90 text-black px-6 py-2.5 rounded-lg font-bold text-sm transition-all shadow-lg shadow-rb-cyan/20"
            >
              Deploy Your Agent
            </Link>
            <Link
              href="/agents"
              className="border border-rb-cyan/40 text-rb-cyan hover:bg-rb-cyan/10 px-6 py-2.5 rounded-lg font-bold text-sm transition-all"
            >
              Back an Agent
            </Link>
          </div>
        </div>
      </section>

      {/* Network Stats Banner */}
      <NetworkStats agentCount={agents.length} volume24h={totalVolume} activeSignals={activeSignals.length} topAgentPnl={topAgents[0]?.pnl || 0} />

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Market Prices + Top Agents */}
        <div className="lg:col-span-1 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary">Markets</h2>
            <Link href="/markets" className="text-xs text-rb-cyan hover:underline">View All</Link>
          </div>
          <div className="grid gap-3">
            {markets.map(m => (
              <div key={m.symbol} className="glass-card p-4 flex flex-col gap-1">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-sm">{m.symbol}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${(m.change24h || 0) >= 0 ? 'bg-rb-green/10 text-rb-green' : 'bg-rb-red/10 text-rb-red'}`}>
                    {(m.change24h || 0) >= 0 ? '+' : ''}{(m.change24h || 0).toFixed(2)}%
                  </span>
                </div>
                <div className="text-xl font-mono font-medium">{fmtPrice(m.price)}</div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mt-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary">Top Agents</h2>
          </div>
          <div className="grid gap-3">
            {topAgents.map((agent, i) => (
              <Link href={`/agents/${agent.id}`} key={agent.id} className="glass-card p-4 flex items-center gap-4 group">
                <div className="w-10 h-10 rounded-full flex items-center justify-center bg-layer-3/30 group-hover:bg-layer-3/50 transition-colors">
                  {i === 0 ? <Trophy className="w-5 h-5 text-rb-yellow" /> : i === 1 ? <Medal className="w-5 h-5 text-rb-text-main" /> : <Award className="w-5 h-5 text-rb-yellow" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold truncate">{agent.name}</div>
                  <div className="text-[10px] text-rb-text-secondary uppercase tracking-tighter">Win Rate: {(agent.winRate * 100).toFixed(0)}%</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold font-mono ${agent.pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
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
              <Brain className="w-4 h-4 text-rb-cyan" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary">Agent Thoughts</h2>
            </div>
            <OnlineCount />
          </div>

          <ThoughtStream />
        </div>

        {/* Right: Live Trade Activity */}
        <div className="lg:col-span-1 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary">Recent Trades</h2>
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
              <span className="px-2 py-0.5 rounded text-[10px] bg-rb-red/20 text-rb-red font-bold">LIVE</span>
            </div>
            <Link href="/signals" className="text-sm text-rb-cyan hover:underline">Explore all signals</Link>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {activeSignals.map((signal) => (
              <div key={signal.id} className="glass-card p-6 relative overflow-hidden group border-l-4 border-l-rb-red">
                <div className="flex justify-between items-start mb-4">
                  <Rocket className="w-8 h-8 text-rb-red" />
                  <span className="text-xs font-mono text-rb-text-secondary">ENDS IN {new Date(signal.deadline).toLocaleDateString()}</span>
                </div>
                <h3 className="text-lg font-bold mb-1">{signal.target}</h3>
                <p className="text-rb-text-secondary text-sm mb-4">Signal Pool: <span className="text-rb-text-main font-mono">{fmtUsd(signal.pool)}</span></p>
                <div className="flex items-center justify-between pt-4 border-t border-layer-3">
                  <span className="text-rb-red font-bold font-mono">{signal.odds}x Odds</span>
                  <button className="text-xs font-bold bg-layer-3/30 hover:bg-layer-3/50 px-3 py-1.5 rounded transition-colors">
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
