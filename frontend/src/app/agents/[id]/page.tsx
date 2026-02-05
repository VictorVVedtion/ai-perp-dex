'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import Link from 'next/link';

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
  Degen: 'bg-red-500/20 text-red-400 border-red-500/30',
  Conservative: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  Momentum: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  Arbitrage: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  Grid: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

// Mock data (will be replaced by API calls)
const mockAgent: Agent = {
  id: '1',
  name: 'AlphaBot',
  avatar: '🤖',
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
    { date: '2024-01-01', pnl: 0 },
    { date: '2024-01-08', pnl: 3200 },
    { date: '2024-01-15', pnl: 2800 },
    { date: '2024-01-22', pnl: 5600 },
    { date: '2024-01-29', pnl: 8200 },
    { date: '2024-02-05', pnl: 7400 },
    { date: '2024-02-12', pnl: 11200 },
    { date: '2024-02-19', pnl: 14800 },
    { date: '2024-02-26', pnl: 18600 },
    { date: '2024-03-04', pnl: 22100 },
    { date: '2024-03-11', pnl: 24580 },
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
    { name: 'Leverage', value: 65 },
    { name: 'Concentration', value: 45 },
    { name: 'Volatility', value: 38 },
    { name: 'Drawdown', value: 22 },
  ],
};

// Simple PnL Chart component
function PnLChart({ data }: { data: { date: string; pnl: number }[] }) {
  const maxPnL = Math.max(...data.map(d => d.pnl));
  const minPnL = Math.min(...data.map(d => d.pnl));
  const range = maxPnL - minPnL || 1;
  
  return (
    <div className="h-48 flex items-end gap-1 pt-4">
      {data.map((point, i) => {
        const height = ((point.pnl - minPnL) / range) * 100;
        const isPositive = point.pnl >= 0;
        return (
          <div
            key={i}
            className="flex-1 flex flex-col justify-end group relative"
          >
            <div
              className={`rounded-t transition-all ${isPositive ? 'bg-green-500/60 hover:bg-green-500' : 'bg-red-500/60 hover:bg-red-500'}`}
              style={{ height: `${Math.max(height, 4)}%` }}
            />
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-zinc-800 px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              ${point.pnl.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Risk meter component
function RiskMeter({ risk }: { risk: Risk }) {
  const levelColors = {
    LOW: 'text-green-400',
    MEDIUM: 'text-yellow-400',
    HIGH: 'text-red-400',
  };
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-zinc-400">Risk Score</span>
        <span className={`text-2xl font-bold ${levelColors[risk.level]}`}>
          {risk.score}/100
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${
            risk.level === 'LOW' ? 'bg-green-500' :
            risk.level === 'MEDIUM' ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${risk.score}%` }}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {risk.factors.map(factor => (
          <div key={factor.name} className="bg-zinc-900/50 rounded-lg p-3">
            <div className="text-xs text-zinc-500 mb-1">{factor.name}</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-zinc-400"
                  style={{ width: `${factor.value}%` }}
                />
              </div>
              <span className="text-xs text-zinc-400">{factor.value}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AgentProfilePage() {
  const params = useParams();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Replace with actual API calls
    // GET /agents/{id}
    // GET /positions/{id}
    // GET /risk/{id}
    
    const fetchData = async () => {
      try {
        // Simulating API calls with mock data
        await new Promise(resolve => setTimeout(resolve, 500));
        setAgent({ ...mockAgent, id: params.id as string });
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

  const handleFollow = () => {
    setIsFollowing(!isFollowing);
    // TODO: POST /agents/{id}/follow
  };

  const handleCopyTrade = () => {
    // TODO: Open copy trade modal
    alert('Copy trading coming soon!');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-zinc-500">Loading agent...</div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="text-6xl">🤖</div>
        <div className="text-zinc-500">Agent not found</div>
        <Link href="/agents" className="text-blue-400 hover:underline">
          ← Back to Agents
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link href="/agents" className="text-zinc-500 hover:text-white text-sm flex items-center gap-1">
        ← Back to Agents
      </Link>

      {/* Header Card */}
      <div className="glass-card p-6">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          {/* Avatar & Basic Info */}
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center text-4xl border border-white/10">
              {agent.avatar}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold">{agent.name}</h1>
                <span className={`px-3 py-1 rounded-full text-xs font-medium border ${styleBadgeColors[agent.style]}`}>
                  {agent.style}
                </span>
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" title="Online" />
              </div>
              <p className="text-zinc-400 text-sm mt-1 max-w-md">{agent.description}</p>
              <div className="text-zinc-500 text-sm mt-2">
                {agent.followers.toLocaleString()} followers
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 md:ml-auto">
            <button
              onClick={handleFollow}
              className={`px-6 py-2.5 rounded-xl font-medium transition-all ${
                isFollowing
                  ? 'bg-zinc-700 text-white hover:bg-zinc-600'
                  : 'bg-white/10 text-white hover:bg-white/20 border border-white/20'
              }`}
            >
              {isFollowing ? '✓ Following' : '+ Follow'}
            </button>
            <button
              onClick={handleCopyTrade}
              className="px-6 py-2.5 rounded-xl font-medium bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 transition-all"
            >
              ⚡ Copy Trade
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Total P&L</div>
          <div className={`text-xl font-bold ${agent.stats.totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {agent.stats.totalPnL >= 0 ? '+' : ''}${agent.stats.totalPnL.toLocaleString()}
          </div>
        </div>
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Win Rate</div>
          <div className="text-xl font-bold">{agent.stats.winRate}%</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Avg Return</div>
          <div className="text-xl font-bold text-green-400">+{agent.stats.avgReturn}%</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Sharpe Ratio</div>
          <div className="text-xl font-bold">{agent.stats.sharpeRatio}</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Max Drawdown</div>
          <div className="text-xl font-bold text-red-400">{agent.stats.maxDrawdown}%</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-zinc-500 text-xs mb-1">Total Trades</div>
          <div className="text-xl font-bold">{agent.stats.totalTrades.toLocaleString()}</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* PnL Chart */}
        <div className="glass-card p-6 md:col-span-2">
          <h2 className="text-lg font-semibold mb-4">📈 Performance History</h2>
          <PnLChart data={agent.pnlHistory} />
          <div className="flex justify-between text-xs text-zinc-500 mt-2">
            <span>Jan</span>
            <span>Feb</span>
            <span>Mar</span>
          </div>
        </div>

        {/* Risk Score */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4">⚠️ Risk Assessment</h2>
          {risk && <RiskMeter risk={risk} />}
        </div>
      </div>

      {/* Recent Positions */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">📊 Active Positions</h2>
          <span className="text-zinc-500 text-sm">{positions.length} open</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-zinc-500 text-xs border-b border-white/5">
                <th className="text-left py-3 font-medium">Market</th>
                <th className="text-left py-3 font-medium">Side</th>
                <th className="text-right py-3 font-medium">Size</th>
                <th className="text-right py-3 font-medium">Entry</th>
                <th className="text-right py-3 font-medium">Mark</th>
                <th className="text-right py-3 font-medium">P&L</th>
                <th className="text-right py-3 font-medium">Leverage</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(pos => (
                <tr key={pos.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="py-4 font-medium">{pos.symbol}</td>
                  <td className="py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      pos.side === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {pos.side}
                    </span>
                  </td>
                  <td className="py-4 text-right text-zinc-300">{pos.size}</td>
                  <td className="py-4 text-right text-zinc-400">${pos.entryPrice.toLocaleString()}</td>
                  <td className="py-4 text-right">${pos.markPrice.toLocaleString()}</td>
                  <td className={`py-4 text-right font-medium ${pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                  </td>
                  <td className="py-4 text-right text-zinc-400">{pos.leverage}x</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Signal Accuracy */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold mb-4">🎯 Signal Accuracy</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-zinc-900/50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-green-400">67%</div>
            <div className="text-zinc-500 text-sm mt-1">Overall</div>
          </div>
          <div className="bg-zinc-900/50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-blue-400">72%</div>
            <div className="text-zinc-500 text-sm mt-1">BTC Signals</div>
          </div>
          <div className="bg-zinc-900/50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-purple-400">64%</div>
            <div className="text-zinc-500 text-sm mt-1">ETH Signals</div>
          </div>
          <div className="bg-zinc-900/50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-amber-400">58%</div>
            <div className="text-zinc-500 text-sm mt-1">Altcoins</div>
          </div>
        </div>
      </div>
    </div>
  );
}
