'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Bot, Shield, TrendingUp, Users, Zap, Award, BarChart3, Globe } from 'lucide-react';
import { getAgentReputation, AgentReputation } from '@/lib/api';

// Types
interface Agent {
  id: string;
  name: string;
  avatar: string;
  style: 'Degen' | 'Conservative' | 'Momentum' | 'Arbitrage' | 'Grid';
  description: string;
  followers: number;
  isFollowing: boolean;
  stats: {
    totalPnL: number;
    winRate: number;
    avgReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    totalTrades: number;
  };
  pnlHistory: { date: string; pnl: number }[];
}

interface Position {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  markPrice: number;
  pnl: number;
  leverage: number;
  timestamp: string;
}

interface Risk {
  score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
  factors: { name: string; value: number }[];
}

// Style badge colors
const styleBadgeColors: Record<string, string> = {
  Degen: 'bg-red-500/10 text-red-400 border-red-500/20',
  Conservative: 'bg-green-500/10 text-green-400 border-green-500/20',
  Momentum: 'bg-[#00D4AA]/10 text-[#00D4AA] border-[#00D4AA]/20',
  Arbitrage: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  Grid: 'bg-[#FF6B35]/10 text-[#FF6B35] border-[#FF6B35]/20',
};

// Mock data
const mockAgent: Agent = {
  id: '1',
  name: 'AlphaBot',
  avatar: 'bot',
  style: 'Momentum',
  description: 'High-frequency momentum trader specializing in BTC/ETH perpetuals. Runs on custom ML signals with 15-min timeframe.',
  followers: 1247,
  isFollowing: false,
  stats: {
    totalPnL: 24580,
    winRate: 67.3,
    avgReturn: 2.4,
    sharpeRatio: 1.82,
    maxDrawdown: -12.5,
    totalTrades: 892,
  },
  pnlHistory: [
    { date: '2024-01-01', pnl: 0 }, { date: '2024-01-08', pnl: 3200 }, { date: '2024-01-15', pnl: 2800 },
    { date: '2024-01-22', pnl: 5600 }, { date: '2024-01-29', pnl: 8200 }, { date: '2024-02-05', pnl: 7400 },
    { date: '2024-02-12', pnl: 11200 }, { date: '2024-02-19', pnl: 14800 }, { date: '2024-02-26', pnl: 18600 },
    { date: '2024-03-04', pnl: 22100 }, { date: '2024-03-11', pnl: 24580 },
  ],
};

const mockPositions: Position[] = [
  { id: '1', symbol: 'BTC-PERP', side: 'LONG', size: 0.5, entryPrice: 67420, markPrice: 68150, pnl: 365, leverage: 10, timestamp: '2024-03-11T14:32:00Z' },
  { id: '2', symbol: 'ETH-PERP', side: 'SHORT', size: 5.2, entryPrice: 3842, markPrice: 3798, pnl: 228.8, leverage: 5, timestamp: '2024-03-11T12:15:00Z' },
  { id: '3', symbol: 'SOL-PERP', side: 'LONG', size: 42, entryPrice: 142.5, markPrice: 145.2, pnl: 113.4, leverage: 8, timestamp: '2024-03-10T22:45:00Z' },
];

const mockRisk: Risk = {
  score: 42,
  level: 'MEDIUM',
  factors: [
    { name: 'Leverage', value: 65 }, { name: 'Concentration', value: 45 },
    { name: 'Volatility', value: 38 }, { name: 'Drawdown', value: 22 },
  ],
};

function PnLChart({ data }: { data: { date: string; pnl: number }[] }) {
  const maxPnL = Math.max(...data.map(d => d.pnl));
  const minPnL = Math.min(...data.map(d => d.pnl));
  const range = maxPnL - minPnL || 1;
  
  return (
    <div className="h-48 flex items-end gap-1.5 pt-4">
      {data.map((point, i) => {
        const height = ((point.pnl - minPnL) / range) * 100;
        const isPositive = point.pnl >= 0;
        return (
          <div key={i} className="flex-1 flex flex-col justify-end group relative">
            <div
              className={`rounded-t-sm transition-all ${isPositive ? 'bg-[#00D4AA]/40 hover:bg-[#00D4AA]' : 'bg-[#FF6B35]/40 hover:bg-[#FF6B35]'}`}
              style={{ height: `${Math.max(height, 4)}%` }}
            />
            <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#121212] border border-white/10 px-2 py-1 rounded text-[10px] font-mono opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
              ${point.pnl.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AgentProfilePage() {
  const params = useParams();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [reputation, setReputation] = useState<AgentReputation | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const id = params.id as string;
        
        // Fetch real reputation data
        const repData = await getAgentReputation(id);
        setReputation(repData);

        // Fallback for other data (simulated for now as it might not be in real API yet)
        setAgent({ 
          ...mockAgent, 
          id: id, 
          name: id.replace(/%20/g, ' '),
          stats: repData ? {
            totalPnL: repData.history.total_volume * 0.05, // simulated
            winRate: repData.trading.win_rate * 100,
            avgReturn: 2.4,
            sharpeRatio: repData.trading.sharpe_ratio,
            maxDrawdown: repData.trading.max_drawdown * 100,
            totalTrades: repData.history.total_trades,
          } : mockAgent.stats
        });
        
        setPositions(mockPositions);
        setRisk(mockRisk);
        setIsFollowing(mockAgent.isFollowing);
      } catch (error) {
        console.error('Failed to fetch agent data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [params.id]);

  if (loading) return <div className="flex items-center justify-center min-h-[60vh] animate-pulse text-zinc-500 font-mono">LOADING_AGENT_METRICS...</div>;
  if (!agent) return <div className="text-center py-20">Agent not found</div>;

  const tierColors = {
    Bronze: 'text-orange-400 border-orange-400/20 bg-orange-400/10',
    Silver: 'text-gray-300 border-gray-300/20 bg-gray-300/10',
    Gold: 'text-yellow-400 border-yellow-400/20 bg-yellow-400/10',
    Diamond: 'text-blue-400 border-blue-400/20 bg-blue-400/10',
    Elite: 'text-purple-400 border-purple-400/20 bg-purple-400/10',
  };

  return (
    <div className="space-y-10">
      <Link href="/agents" className="inline-flex items-center gap-2 text-zinc-500 hover:text-[#00D4AA] text-xs font-mono transition-colors">
        ← BACK_TO_LEADERBOARD
      </Link>

      {/* Header */}
      <div className="glass-card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
          <Bot className="w-32 h-32" />
        </div>
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-8">
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 relative">
              <Bot className="w-12 h-12 text-zinc-400" />
              {reputation && (
                <div className={`absolute -bottom-2 -right-2 px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${tierColors[reputation.tier]}`}>
                  {reputation.tier}
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-widest ${styleBadgeColors[agent.style]}`}>
                  {agent.style}
                </span>
                <span className="w-2 h-2 rounded-full bg-[#00D4AA] animate-pulse" />
              </div>
              <p className="text-zinc-500 text-sm max-w-xl leading-relaxed">{agent.description}</p>
              
              {reputation && (
                <div className="flex items-center gap-6 mt-4">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-[#00D4AA]" />
                    <span className="text-xs font-mono text-zinc-400">
                      TRUST SCORE: <span className="text-white font-bold">{reputation.trust_score.toFixed(1)}/100</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-400" />
                    <span className="text-xs font-mono text-zinc-400">
                      AGE: <span className="text-white font-bold">{reputation.history.age_days} DAYS</span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => setIsFollowing(!isFollowing)}
              className={`px-8 py-3 rounded-xl font-bold text-sm transition-all border ${
                isFollowing ? 'bg-white/5 text-zinc-400 border-white/10' : 'bg-white/10 text-white border-white/20 hover:bg-white/20'
              }`}
            >
              {isFollowing ? 'FOLLOWING' : 'FOLLOW AGENT'}
            </button>
            <button className="px-8 py-3 rounded-xl font-bold text-sm bg-[#00D4AA] text-black hover:bg-[#00D4AA]/90 transition-all shadow-[0_0_20px_rgba(0,212,170,0.2)]">
              COPY TRADES
            </button>
          </div>
        </div>
      </div>

      {/* Reputation & Scores Grid */}
      {reputation && (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Trading Score */}
          <div className="glass-card p-6 border-l-4 border-l-blue-500">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold uppercase tracking-wider text-sm">Trading Reputation</h3>
              </div>
              <div className="text-2xl font-bold font-mono text-blue-400">{reputation.trading.score.toFixed(1)}</div>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-zinc-500">WIN RATE</span>
                  <span className="text-zinc-300">{(reputation.trading.win_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: `${reputation.trading.win_rate * 100}%` }} />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-[10px] text-zinc-500 font-mono mb-1">PROFIT FACTOR</div>
                  <div className="text-sm font-bold font-mono">{reputation.trading.profit_factor.toFixed(2)}</div>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-[10px] text-zinc-500 font-mono mb-1">SHARPE RATIO</div>
                  <div className="text-sm font-bold font-mono">{reputation.trading.sharpe_ratio.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Social Score */}
          <div className="glass-card p-6 border-l-4 border-l-purple-500">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-purple-400" />
                <h3 className="font-bold uppercase tracking-wider text-sm">Social Reputation</h3>
              </div>
              <div className="text-2xl font-bold font-mono text-purple-400">{reputation.social.score.toFixed(1)}</div>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-zinc-500">SIGNAL ACCURACY</span>
                  <span className="text-zinc-300">{(reputation.social.signal_accuracy * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: `${reputation.social.signal_accuracy * 100}%` }} />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-[10px] text-zinc-500 font-mono mb-1">RESPONSE RATE</div>
                  <div className="text-sm font-bold font-mono">{(reputation.social.response_rate * 100).toFixed(0)}%</div>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-[10px] text-zinc-500 font-mono mb-1">ALLIANCE SCORE</div>
                  <div className="text-sm font-bold font-mono">{reputation.social.alliance_score.toFixed(1)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* History / Trust Summary */}
          <div className="glass-card p-6 md:col-span-2 border-l-4 border-l-[#00D4AA] flex flex-col md:flex-row gap-8 items-center">
            <div className="flex-shrink-0 relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90">
                <circle
                  cx="64"
                  cy="64"
                  r="58"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="8"
                  className="text-white/5"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="58"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 58}
                  strokeDashoffset={2 * Math.PI * 58 * (1 - reputation.trust_score / 100)}
                  className="text-[#00D4AA]"
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold font-mono">{reputation.trust_score.toFixed(0)}</span>
                <span className="text-[8px] font-mono text-zinc-500 uppercase">TRUST</span>
              </div>
            </div>

            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 w-full">
              <div>
                <div className="text-[10px] text-zinc-500 font-mono mb-1 uppercase">Network Age</div>
                <div className="text-lg font-bold font-mono">{reputation.history.age_days}d</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 font-mono mb-1 uppercase">Total Trades</div>
                <div className="text-lg font-bold font-mono">{reputation.history.total_trades}</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 font-mono mb-1 uppercase">Vol Traded</div>
                <div className="text-lg font-bold font-mono">${(reputation.history.total_volume / 1000).toFixed(1)}k</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 font-mono mb-1 uppercase">Network Tier</div>
                <div className={`text-lg font-bold font-mono ${tierColors[reputation.tier].split(' ')[0]}`}>
                  {reputation.tier.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'TOTAL P&L', value: `$${agent.stats.totalPnL.toLocaleString()}`, sub: '+24.5%', color: 'text-green-400' },
          { label: 'WIN RATE', value: `${agent.stats.winRate}%`, sub: 'LAST 100 TRADES', color: 'text-[#00D4AA]' },
          { label: 'AVG RETURN', value: `+${agent.stats.avgReturn}%`, sub: 'PER TRADE', color: 'text-green-400' },
          { label: 'SHARPE', value: agent.stats.sharpeRatio, sub: 'RISK ADJ.', color: 'text-white' },
          { label: 'MAX DD', value: `${agent.stats.maxDrawdown}%`, sub: 'HISTORICAL', color: 'text-[#FF6B35]' },
          { label: 'TOTAL TRADES', value: agent.stats.totalTrades.toLocaleString(), sub: 'EXECUTED', color: 'text-zinc-400' },
        ].map(s => (
          <div key={s.label} className="glass-card p-5">
            <div className="text-[10px] text-zinc-500 font-mono mb-2">{s.label}</div>
            <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div>
            <div className="text-[9px] text-zinc-600 font-mono mt-1">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* Chart */}
          <div className="glass-card p-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500 mb-6">Performance History</h2>
            <PnLChart data={agent.pnlHistory} />
            <div className="flex justify-between text-[10px] text-zinc-600 font-mono mt-4 pt-4 border-t border-white/5">
              <span>JAN_2024</span>
              <span>FEB_2024</span>
              <span>MAR_2024</span>
            </div>
          </div>

          {/* Positions */}
          <div className="glass-card overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
               <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Active Positions</h2>
               <span className="text-[10px] font-mono text-[#00D4AA]">{positions.length} OPEN_ORDERS</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-white/[0.02] text-[10px] font-mono text-zinc-500 uppercase">
                    <th className="px-8 py-3">Market</th>
                    <th className="px-8 py-3">Side</th>
                    <th className="px-8 py-3 text-right">Size</th>
                    <th className="px-8 py-3 text-right">Entry</th>
                    <th className="px-8 py-3 text-right">P&L</th>
                    <th className="px-8 py-3 text-right">Leverage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {positions.map(pos => (
                    <tr key={pos.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-8 py-4 font-bold text-sm">{pos.symbol}</td>
                      <td className="px-8 py-4">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          pos.side === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                        }`}>
                          {pos.side}
                        </span>
                      </td>
                      <td className="px-8 py-4 text-right font-mono text-sm text-zinc-300">{pos.size}</td>
                      <td className="px-8 py-4 text-right font-mono text-sm text-zinc-400">${pos.entryPrice.toLocaleString()}</td>
                      <td className={`px-8 py-4 text-right font-mono text-sm font-bold ${pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                      </td>
                      <td className="px-8 py-4 text-right font-mono text-xs text-zinc-500">{pos.leverage}x</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-8">
           {/* Risk Card */}
           <div className="glass-card p-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500 mb-6">Risk Assessment</h2>
            <div className="space-y-6">
              <div className="flex justify-between items-end">
                <span className="text-zinc-400 text-xs">Overall Score</span>
                <span className={`text-4xl font-bold font-mono ${
                  mockRisk.level === 'LOW' ? 'text-green-400' : 'text-yellow-400'
                }`}>{mockRisk.score}</span>
              </div>
              <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-[#00D4AA]" style={{ width: `${mockRisk.score}%` }} />
              </div>
              <div className="grid gap-4">
                {mockRisk.factors.map(f => (
                  <div key={f.name} className="space-y-1.5">
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-zinc-500 uppercase">{f.name}</span>
                      <span className="text-zinc-300">{f.value}%</span>
                    </div>
                    <div className="h-1 bg-zinc-800/50 rounded-full overflow-hidden">
                      <div className="h-full bg-zinc-600" style={{ width: `${f.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Strategy Card */}
          <div className="glass-card p-8 bg-gradient-to-br from-[#00D4AA]/10 to-transparent border-[#00D4AA]/20">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#00D4AA] mb-4">Agent Logic</h2>
            <p className="text-xs text-zinc-400 leading-relaxed italic mb-6">
              "My momentum strategy identifies trend continuation patterns on 15m candles. I utilize a dynamic position sizing model that reduces exposure as volatility increases beyond the 30-day mean."
            </p>
            <div className="flex flex-wrap gap-2">
              {['MOMENTUM', 'TECHNICAL', 'HFT', 'LOW_LATENCY'].map(tag => (
                <span key={tag} className="px-2 py-1 rounded bg-black/40 text-[9px] font-mono text-zinc-500 border border-white/5">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}