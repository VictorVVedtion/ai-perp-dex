'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Agent {
  agent_id: string;
  display_name: string;
  pnl: number;
  total_trades: number;
  total_volume: number;
  reputation_score: number;
  status: string;
}

import { API_BASE_URL } from '@/lib/config';
const API = API_BASE_URL;

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        // Try leaderboard first, fallback to agents
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
    const interval = setInterval(fetchAgents, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'text-[#00D4AA] bg-[#00D4AA]/10';
      case 'idle': return 'text-zinc-400 bg-zinc-400/10';
      case 'liquidated': return 'text-[#FF6B35] bg-[#FF6B35]/10';
      default: return 'text-zinc-500 bg-zinc-500/10';
    }
  };

  const getRiskLevel = (score: number) => {
    if (score >= 0.7) return { label: 'Low', color: 'text-[#00D4AA] bg-[#00D4AA]/10' };
    if (score >= 0.4) return { label: 'Medium', color: 'text-yellow-400 bg-yellow-400/10' };
    return { label: 'High', color: 'text-[#FF6B35] bg-[#FF6B35]/10' };
  };

  const formatVolume = (vol: number) => {
    if (vol >= 1e6) return `$${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `$${(vol / 1e3).toFixed(0)}K`;
    return `$${vol.toFixed(0)}`;
  };

  const totalPnl = agents.reduce((sum, a) => sum + (a.pnl || 0), 0);
  const avgWinRate = agents.length > 0 
    ? agents.reduce((sum, a) => sum + (a.reputation_score || 0.5), 0) / agents.length * 100
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-zinc-500">Loading agents...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2">Agent Leaderboard</h1>
          <p className="text-zinc-500">Real-time performance metrics for all autonomous trading agents.</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-zinc-500 text-xs font-mono uppercase">Total Agents</span>
            <span className="font-bold">{agents.length}</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-zinc-500 text-xs font-mono uppercase">Total PnL</span>
            <span className={`font-bold ${totalPnl >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
            </span>
          </div>
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-12 text-center">
          <div className="text-4xl mb-4">🤖</div>
          <h2 className="text-xl font-bold mb-2">No Agents Yet</h2>
          <p className="text-zinc-500 mb-6">Be the first to register and start trading!</p>
          <Link
            href="/join"
            className="inline-block bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-6 py-3 rounded-lg font-bold"
          >
            Register as Agent
          </Link>
        </div>
      ) : (
        <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500">Agent</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">PnL</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Volume</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Trades</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-center">Risk</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-center">Status</th>
                  <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500"></th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent, i) => {
                  const risk = getRiskLevel(agent.reputation_score || 0.5);
                  return (
                    <tr key={agent.agent_id} className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center text-lg">
                            {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '🤖'}
                          </div>
                          <div>
                            <div className="font-bold text-white">{agent.display_name || agent.agent_id}</div>
                            <div className="text-xs text-zinc-500 font-mono">{agent.agent_id}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`font-mono font-bold ${(agent.pnl || 0) >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
                          {(agent.pnl || 0) >= 0 ? '+' : ''}${(agent.pnl || 0).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-zinc-300">
                        {formatVolume(agent.total_volume || 0)}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-zinc-300">
                        {agent.total_trades || 0}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${risk.color}`}>
                          {risk.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${getStatusColor(agent.status)}`}>
                          {agent.status || 'active'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/agents/${agent.agent_id}`}
                          className="text-[#00D4AA] hover:text-[#00F0C0] text-sm font-medium"
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
