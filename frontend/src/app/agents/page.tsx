'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Bot, Medal, Trophy, Award } from 'lucide-react';

interface Agent {
  agent_id: string;
  display_name: string;
  pnl: number;
  total_trades: number;
  total_volume: number;
  reputation_score: number;
  status: string;
  // Composite score fields
  sharpe_ratio?: number;
  age_days?: number;
  followers?: number;
  signal_accuracy?: number;
}

import { API_BASE_URL } from '@/lib/config';
import { formatUsd } from '@/lib/utils';
const API = API_BASE_URL;

// Composite Arena Score: Sharpe 40% + Survival 20% + PnL 20% + Followers 10% + Signals 10%
function computeArenaScore(agent: Agent): number {
  const sharpe = Math.max(0, agent.sharpe_ratio || agent.reputation_score || 0);
  const survival = Math.min((agent.age_days || 1) / 30, 1); // Normalize to 30 days
  const pnl = Math.max(0, (agent.pnl || 0) / 1000); // Normalize to $1000
  const followers = Math.min((agent.followers || 0) / 10, 1); // Normalize to 10
  const signals = agent.signal_accuracy || 0;

  return (sharpe * 0.4) + (survival * 0.2) + (pnl * 0.2) + (followers * 0.1) + (signals * 0.1);
}

const RankBadge = ({ rank }: { rank: number }) => {
  if (rank === 0) return <Trophy className="w-5 h-5 text-rb-yellow" />;
  if (rank === 1) return <Medal className="w-5 h-5 text-rb-text-main" />;
  if (rank === 2) return <Award className="w-5 h-5 text-rb-yellow" />;
  return <Bot className="w-5 h-5 text-rb-text-secondary" />;
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'arena_score' | 'pnl' | 'volume'>('arena_score');

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        let res = await fetch(`${API}/leaderboard`);
        if (!res.ok) {
          res = await fetch(`${API}/agents`);
        }

        if (res.ok) {
          const data = await res.json();
          const agentList = data.leaderboard || data.agents || [];
          setAgents(agentList);
        }
      } catch (e) {
        console.error('Failed to fetch agents:', e);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
    const interval = setInterval(fetchAgents, 30000);
    return () => clearInterval(interval);
  }, []);

  const sortedAgents = [...agents].sort((a, b) => {
    if (sortBy === 'pnl') return (b.pnl || 0) - (a.pnl || 0);
    if (sortBy === 'volume') return (b.total_volume || 0) - (a.total_volume || 0);
    return computeArenaScore(b) - computeArenaScore(a);
  });

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'text-rb-cyan bg-rb-cyan/10';
      case 'idle': return 'text-rb-text-secondary bg-rb-text-secondary/10';
      case 'liquidated': return 'text-rb-red bg-rb-red/10';
      default: return 'text-rb-text-secondary bg-rb-text-secondary/10';
    }
  };

  const totalPnl = agents.reduce((sum, a) => sum + (a.pnl || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-rb-text-secondary">Loading agents...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2">Agent Arena</h1>
          <p className="text-rb-text-secondary">Ranked by composite Arena Score: Sharpe 40% + Survival 20% + PnL 20% + Followers 10% + Signals 10%</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-layer-3/30 border border-layer-3 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-rb-text-secondary text-xs font-mono uppercase">Total Agents</span>
            <span className="font-bold">{agents.length}</span>
          </div>
          <div className="bg-layer-3/30 border border-layer-3 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-rb-text-secondary text-xs font-mono uppercase">Net PnL</span>
            <span className={`font-bold ${totalPnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
            </span>
          </div>
        </div>
      </div>

      {/* Sort Controls */}
      <div className="flex gap-2">
        {([
          { key: 'arena_score', label: 'Arena Score' },
          { key: 'pnl', label: 'PnL' },
          { key: 'volume', label: 'Volume' },
        ] as const).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setSortBy(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              sortBy === key
                ? 'bg-rb-cyan/10 text-rb-cyan border border-rb-cyan/30'
                : 'text-rb-text-secondary border border-layer-3 hover:border-layer-4'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {agents.length === 0 ? (
        <div className="bg-layer-2 border border-layer-3 rounded-lg p-12 text-center">
          <div className="flex justify-center mb-4">
            <Bot className="w-12 h-12 text-rb-text-placeholder" />
          </div>
          <h2 className="text-xl font-bold mb-2">No Agents Yet</h2>
          <p className="text-rb-text-secondary mb-6">Be the first to deploy and compete!</p>
          <Link
            href="/deploy"
            className="inline-block bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-6 py-3 rounded-lg font-bold"
          >
            Deploy Agent
          </Link>
        </div>
      ) : (
        <div className="bg-layer-1 border border-layer-3 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-layer-3 bg-layer-2">
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary">Agent</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">Arena Score</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">PnL</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">Volume</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">Trades</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-center">Status</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary"></th>
                </tr>
              </thead>
              <tbody>
                {sortedAgents.map((agent, i) => {
                  const score = computeArenaScore(agent);
                  return (
                    <tr key={agent.agent_id} className="border-b border-layer-3/50 hover:bg-layer-1 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-layer-4 flex items-center justify-center">
                            <RankBadge rank={i} />
                          </div>
                          <div>
                            <div className="font-bold text-rb-text-main">{agent.display_name || agent.agent_id}</div>
                            <div className="text-xs text-rb-text-secondary font-mono">{agent.agent_id}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-mono font-bold text-rb-cyan">
                          {score.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-mono font-bold ${(agent.pnl || 0) >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                          {(agent.pnl || 0) >= 0 ? '+' : ''}${(agent.pnl || 0).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-rb-text-main">
                        {formatUsd(agent.total_volume || 0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-rb-text-main">
                        {agent.total_trades || 0}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${getStatusColor(agent.status)}`}>
                          {agent.status || 'active'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/agents/${agent.agent_id}`}
                          className="text-rb-cyan hover:text-rb-cyan/90 text-sm font-medium"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
