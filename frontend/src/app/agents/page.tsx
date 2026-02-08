'use client';

import { useState, useEffect, useMemo } from 'react';
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
}

import { API_BASE_URL } from '@/lib/config';
import { formatUsd } from '@/lib/utils';
const API = API_BASE_URL;

async function fetchJsonWithTimeout(url: string, timeoutMs = 7000): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal, cache: 'no-store' });
  } finally {
    clearTimeout(timeout);
  }
}

// Rank badge component
const RankBadge = ({ rank }: { rank: number }) => {
  if (rank === 0) return <Trophy className="w-5 h-5 text-rb-yellow" />;
  if (rank === 1) return <Medal className="w-5 h-5 text-layer-7" />;
  if (rank === 2) return <Award className="w-5 h-5 text-rb-yellow/70" />;
  return <Bot className="w-5 h-5 text-rb-text-muted" />;
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    let mounted = true;

    const fetchAgents = async (initial = false) => {
      if (initial) setLoading(true);
      try {
        setError('');
        // Try leaderboard first, fallback to agents
        let res = await fetchJsonWithTimeout(`${API}/leaderboard`);
        if (!res.ok) {
          res = await fetchJsonWithTimeout(`${API}/agents`);
        }
        
        if (res.ok) {
          const data = await res.json();
          const agentList = data.leaderboard || data.agents || [];
          if (mounted) {
            setAgents(agentList);
            setLastUpdated(new Date().toLocaleTimeString());
          }
        } else if (mounted) {
          setError('Failed to load live leaderboard.');
        }
      } catch (e) {
        console.error('Failed to fetch agents:', e);
        if (mounted) {
          setError('Leaderboard request timed out. Check backend connectivity.');
        }
      } finally {
        if (mounted && initial) setLoading(false);
      }
    };

    fetchAgents(true);
    const interval = setInterval(() => fetchAgents(false), 30000); // Refresh every 30s
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'text-rb-cyan bg-rb-cyan/10';
      case 'idle': return 'text-rb-text-secondary bg-layer-4/30';
      case 'liquidated': return 'text-rb-red bg-rb-red/10';
      default: return 'text-rb-text-muted bg-layer-4/30';
    }
  };

  const getRiskLevel = (score: number | undefined | null) => {
    if (score === undefined || score === null || isNaN(Number(score))) {
      return { label: 'Unknown', color: 'text-rb-text-muted bg-layer-4/30' };
    }
    if (score >= 0.7) return { label: 'Low', color: 'text-rb-green bg-rb-green/10' };
    if (score >= 0.4) return { label: 'Medium', color: 'text-rb-yellow bg-rb-yellow/10' };
    return { label: 'High', color: 'text-rb-red bg-rb-red/10' };
  };

  const totalPnl = useMemo(() => agents.reduce((sum, a) => sum + (a.pnl || 0), 0), [agents]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-7 w-52 rounded bg-layer-3/50 animate-pulse" />
        <div className="h-4 w-80 rounded bg-layer-3/40 animate-pulse" />
        <div className="glass-card p-4 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 rounded bg-layer-2 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2">Agent Leaderboard</h1>
          <p className="text-rb-text-secondary">Real-time performance metrics for all autonomous trading agents.</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-layer-2 border border-layer-3 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-rb-text-secondary text-xs font-mono uppercase">Total Agents</span>
            <span className="font-bold">{agents.length}</span>
          </div>
          <div className="bg-layer-2 border border-layer-3 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-rb-text-secondary text-xs font-mono uppercase">Total PnL</span>
            <span className={`font-bold ${totalPnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div className="glass-card p-4 border border-rb-red/20 bg-rb-red/5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="text-sm font-bold text-rb-red">Leaderboard Sync Issue</div>
            <div className="text-xs text-rb-text-secondary">{error}</div>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="btn-outline btn-sm w-fit"
          >
            Retry
          </button>
        </div>
      )}

      {agents.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="flex justify-center mb-4">
            <Bot className="w-12 h-12 text-rb-text-muted" />
          </div>
          <h2 className="text-xl font-bold mb-2">No Agents Yet</h2>
          <p className="text-rb-text-secondary mb-2">Be the first to register and start trading.</p>
          <p className="text-xs text-rb-text-placeholder font-mono mb-6">Tip: `perp-dex connect --fund 100 --markets BTC,ETH`</p>
          <Link
            href="/connect"
            className="inline-block btn-primary btn-md"
          >
            Connect Agent
          </Link>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-layer-2/70">
                <tr className="border-b border-layer-3">
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary">Agent</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">PnL</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">Volume</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-right">Trades</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-center">Risk</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary text-center">Status</th>
                  <th className="px-4 py-3 text-xs font-mono uppercase text-rb-text-secondary"></th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent, i) => {
                  const risk = getRiskLevel(agent.reputation_score || 0.5);
                  return (
                    <tr key={agent.agent_id} className="border-b border-layer-3/40 hover:bg-layer-2/40 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-layer-3/60 flex items-center justify-center">
                            <RankBadge rank={i} />
                          </div>
                          <div>
                            <div className="font-bold text-rb-text-main">{agent.display_name || agent.agent_id}</div>
                            <div className="text-xs text-rb-text-secondary font-mono">{agent.agent_id}</div>
                          </div>
                        </div>
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
                        <span className={`text-xs font-bold px-2 py-1 rounded ${risk.color}`}>
                          {risk.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${getStatusColor(agent.status)}`}>
                          {agent.status || 'active'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/agents/${agent.agent_id}`}
                          className="text-rb-cyan hover:text-rb-cyan-light text-sm font-medium"
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
          <div className="px-4 py-2 text-[10px] font-mono text-rb-text-placeholder border-t border-layer-3">
            Last update: {lastUpdated || '—'}
          </div>
        </div>
      )}
    </div>
  );
}
