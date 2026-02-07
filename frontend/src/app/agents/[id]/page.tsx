'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Bot, Shield, TrendingUp, Users, Zap, Award, BarChart3, Globe, AlertCircle } from 'lucide-react';
import { getAgentReputation, AgentReputation } from '@/lib/api';
import { API_BASE_URL } from '@/lib/config';
import { formatPrice, formatPnl, formatUsd } from '@/lib/utils';

// === 类型定义 ===

interface AgentInfo {
  agent_id: string;
  display_name: string;
  wallet_address: string;
  balance: number;
  bio?: string;
  style?: string;
}

interface Position {
  position_id: string;
  asset: string;
  side: 'LONG' | 'SHORT';
  size_usdc: number;
  entry_price: number;
  mark_price?: number;
  unrealized_pnl?: number;
  leverage: number;
  opened_at: string;
}

interface RiskData {
  score: number;
  level: string;
  details: Record<string, any>;
}

// Agent 风格 badge 颜色
const styleBadgeColors: Record<string, string> = {
  Degen: 'bg-rb-red/10 text-rb-red border-rb-red/20',
  Conservative: 'bg-rb-green/10 text-rb-green border-rb-green/20',
  Momentum: 'bg-rb-cyan/10 text-rb-cyan border-rb-cyan/20',
  Arbitrage: 'bg-rb-cyan/10 text-rb-cyan border-rb-cyan/20',
  Grid: 'bg-rb-yellow/10 text-rb-yellow border-rb-yellow/20',
  Trader: 'bg-rb-cyan/10 text-rb-cyan border-rb-cyan/20',
};

// PnL 柱状图组件
function PnLChart({ data }: { data: { date: string; pnl: number }[] }) {
  if (!data || data.length === 0) {
    return <div className="h-48 flex items-center justify-center text-rb-text-placeholder text-sm font-mono">NO_DATA_AVAILABLE</div>;
  }

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
              className={`rounded-t-sm transition-all ${isPositive ? 'bg-rb-cyan/40 hover:bg-rb-cyan' : 'bg-rb-red/40 hover:bg-rb-red'}`}
              style={{ height: `${Math.max(height, 4)}%` }}
            />
            <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-layer-2 border border-layer-3 px-2 py-1 rounded text-[10px] font-mono opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
              {formatPnl(point.pnl)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AgentProfilePage() {
  const params = useParams();
  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [reputation, setReputation] = useState<AgentReputation | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [pnlHistory, setPnlHistory] = useState<{ date: string; pnl: number }[]>([]);
  const [isFollowing, setIsFollowing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const id = params.id as string;

        // 并行请求所有真实 API
        const [agentRes, repData, posRes, riskRes, pnlRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/agents/${id}`, { cache: 'no-store' }),
          getAgentReputation(id),
          fetch(`${API_BASE_URL}/positions/${id}`, { cache: 'no-store' }),
          fetch(`${API_BASE_URL}/risk/${id}`, { cache: 'no-store' }),
          fetch(`${API_BASE_URL}/pnl/${id}`, { cache: 'no-store' }),
        ]);

        // 解析 Agent 基本信息
        if (agentRes.status === 'fulfilled' && agentRes.value.ok) {
          const data = await agentRes.value.json();
          setAgent(data.agent || data);
        } else {
          setNotFound(true);
          setLoading(false);
          return;
        }

        if (repData.status === 'fulfilled' && repData.value) {
          setReputation(repData.value);
        }

        if (posRes.status === 'fulfilled' && posRes.value.ok) {
          const data = await posRes.value.json();
          const posList = Array.isArray(data) ? data : (data.positions || []);
          setPositions(posList);
        }

        if (riskRes.status === 'fulfilled' && riskRes.value.ok) {
          const data = await riskRes.value.json();
          setRisk(data);
        }

        if (pnlRes.status === 'fulfilled' && pnlRes.value.ok) {
          const data = await pnlRes.value.json();
          if (data.history && Array.isArray(data.history)) {
            setPnlHistory(data.history);
          } else if (data.realized_pnl !== undefined) {
            setPnlHistory([{ date: new Date().toISOString(), pnl: data.realized_pnl || 0 }]);
          }
        }

      } catch (err) {
        console.error('Failed to fetch agent data:', err);
        setError('Failed to load agent data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [params.id]);

  if (loading) return <div className="flex items-center justify-center min-h-[60vh] animate-pulse text-rb-text-secondary font-mono">LOADING_AGENT_METRICS...</div>;
  if (notFound) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
      <div className="w-20 h-20 rounded-lg bg-layer-1 flex items-center justify-center border border-layer-3">
        <AlertCircle className="w-10 h-10 text-rb-text-placeholder" />
      </div>
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Agent Not Found</h1>
        <p className="text-rb-text-secondary text-sm font-mono">ID: {params.id}</p>
      </div>
      <Link
        href="/agents"
        className="bg-layer-4 hover:bg-layer-4/80 text-rb-text-main px-6 py-3 rounded-lg font-bold text-sm transition-colors"
      >
        Back to Leaderboard
      </Link>
    </div>
  );
  if (error && !agent) return (
    <div className="text-center py-20 space-y-4">
      <AlertCircle className="w-12 h-12 text-rb-text-placeholder mx-auto" />
      <p className="text-rb-text-secondary">{error}</p>
      <Link href="/agents" className="text-rb-cyan text-sm hover:underline">Back to Leaderboard</Link>
    </div>
  );
  if (!agent) return <div className="text-center py-20">Agent not found</div>;

  const tierColors: Record<string, string> = {
    Bronze: 'text-rb-yellow border-rb-yellow/20 bg-rb-yellow/10',
    Silver: 'text-rb-text-main border-rb-text-main/20 bg-rb-text-main/10',
    Gold: 'text-rb-yellow border-rb-yellow/20 bg-rb-yellow/10',
    Diamond: 'text-rb-cyan border-rb-cyan/20 bg-rb-cyan/10',
    Elite: 'text-rb-cyan-light border-rb-cyan-light/20 bg-rb-cyan-light/10',
  };

  const stats = reputation ? {
    totalPnL: reputation.history.total_volume * (reputation.trading.profit_factor > 1 ? 0.05 : -0.02),
    winRate: reputation.trading.win_rate * 100,
    sharpeRatio: reputation.trading.sharpe_ratio,
    maxDrawdown: reputation.trading.max_drawdown * 100,
    totalTrades: reputation.history.total_trades,
    profitFactor: reputation.trading.profit_factor,
  } : null;

  const agentStyle = agent.style || (reputation?.tier === 'Elite' ? 'Momentum' : 'Trader');

  return (
    <div className="space-y-10">
      <Link href="/agents" className="inline-flex items-center gap-2 text-rb-text-secondary hover:text-rb-cyan text-xs font-mono transition-colors">
        &larr; Back to Leaderboard
      </Link>

      {/* Header */}
      <div className="glass-card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
          <Bot className="w-32 h-32" />
        </div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-8">
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 rounded-lg bg-layer-3/30 flex items-center justify-center border border-layer-3 relative">
              <Bot className="w-12 h-12 text-rb-text-secondary" />
              {reputation && (
                <div className={`absolute -bottom-2 -right-2 px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${tierColors[reputation.tier] || ''}`}>
                  {reputation.tier}
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold tracking-tight">{agent.display_name || agent.agent_id}</h1>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-widest ${styleBadgeColors[agentStyle] || styleBadgeColors['Trader']}`}>
                  {agentStyle}
                </span>
                <span className="w-2 h-2 rounded-full bg-rb-cyan animate-pulse" />
              </div>
              <p className="text-rb-text-secondary text-sm max-w-xl leading-relaxed">
                {agent.bio || `Agent ${agent.agent_id} on Riverbit`}
              </p>

              {reputation && (
                <div className="flex items-center gap-6 mt-4">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-rb-cyan" />
                    <span className="text-xs font-mono text-rb-text-secondary">
                      TRUST SCORE: <span className="text-rb-text-main font-bold">{reputation.trust_score.toFixed(1)}/100</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-rb-yellow" />
                    <span className="text-xs font-mono text-rb-text-secondary">
                      AGE: <span className="text-rb-text-main font-bold">{reputation.history.age_days} DAYS</span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => setIsFollowing(!isFollowing)}
              className={`px-8 py-3 rounded-lg font-bold text-sm transition-all border ${
                isFollowing ? 'bg-layer-3/30 text-rb-text-secondary border-layer-3' : 'bg-layer-3/50 text-rb-text-main border-layer-4 hover:bg-layer-4/50'
              }`}
            >
              {isFollowing ? 'FOLLOWING' : 'FOLLOW AGENT'}
            </button>
            <button className="px-8 py-3 rounded-lg font-bold text-sm bg-rb-cyan text-black hover:bg-rb-cyan/90 transition-all shadow-[0_0_20px_rgba(14,236,188,0.2)]">
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
                <BarChart3 className="w-5 h-5 text-rb-cyan" />
                <h3 className="font-bold uppercase tracking-wider text-sm">Trading Reputation</h3>
              </div>
              <div className="text-2xl font-bold font-mono text-rb-cyan">{reputation.trading.score.toFixed(1)}</div>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-rb-text-secondary">WIN RATE</span>
                  <span className="text-rb-text-main">{(reputation.trading.win_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-layer-3/30 rounded-full overflow-hidden">
                  <div className="h-full bg-rb-cyan" style={{ width: `${reputation.trading.win_rate * 100}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-layer-3/30 rounded-lg">
                  <div className="text-[10px] text-rb-text-secondary font-mono mb-1">PROFIT FACTOR</div>
                  <div className="text-sm font-bold font-mono">{reputation.trading.profit_factor.toFixed(2)}</div>
                </div>
                <div className="p-3 bg-layer-3/30 rounded-lg">
                  <div className="text-[10px] text-rb-text-secondary font-mono mb-1">SHARPE RATIO</div>
                  <div className="text-sm font-bold font-mono">{reputation.trading.sharpe_ratio.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Social Score */}
          <div className="glass-card p-6 border-l-4 border-l-purple-500">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-rb-cyan-light" />
                <h3 className="font-bold uppercase tracking-wider text-sm">Social Reputation</h3>
              </div>
              <div className="text-2xl font-bold font-mono text-rb-cyan-light">{reputation.social.score.toFixed(1)}</div>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-rb-text-secondary">SIGNAL ACCURACY</span>
                  <span className="text-rb-text-main">{(reputation.social.signal_accuracy * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-layer-3/30 rounded-full overflow-hidden">
                  <div className="h-full bg-rb-cyan-light" style={{ width: `${reputation.social.signal_accuracy * 100}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-layer-3/30 rounded-lg">
                  <div className="text-[10px] text-rb-text-secondary font-mono mb-1">RESPONSE RATE</div>
                  <div className="text-sm font-bold font-mono">{(reputation.social.response_rate * 100).toFixed(0)}%</div>
                </div>
                <div className="p-3 bg-layer-3/30 rounded-lg">
                  <div className="text-[10px] text-rb-text-secondary font-mono mb-1">ALLIANCE SCORE</div>
                  <div className="text-sm font-bold font-mono">{reputation.social.alliance_score.toFixed(1)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* History / Trust Summary */}
          <div className="glass-card p-6 md:col-span-2 border-l-4 border-l-rb-cyan flex flex-col md:flex-row gap-8 items-center">
            <div className="flex-shrink-0 relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90">
                <circle cx="64" cy="64" r="58" fill="transparent" stroke="currentColor" strokeWidth="8" className="text-white/5" />
                <circle
                  cx="64" cy="64" r="58" fill="transparent" stroke="currentColor" strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 58}
                  strokeDashoffset={2 * Math.PI * 58 * (1 - reputation.trust_score / 100)}
                  className="text-rb-cyan" strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold font-mono">{reputation.trust_score.toFixed(0)}</span>
                <span className="text-[8px] font-mono text-rb-text-secondary uppercase">TRUST</span>
              </div>
            </div>

            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 w-full">
              <div>
                <div className="text-[10px] text-rb-text-secondary font-mono mb-1 uppercase">Network Age</div>
                <div className="text-lg font-bold font-mono">{reputation.history.age_days}d</div>
              </div>
              <div>
                <div className="text-[10px] text-rb-text-secondary font-mono mb-1 uppercase">Total Trades</div>
                <div className="text-lg font-bold font-mono">{reputation.history.total_trades}</div>
              </div>
              <div>
                <div className="text-[10px] text-rb-text-secondary font-mono mb-1 uppercase">Vol Traded</div>
                <div className="text-lg font-bold font-mono">{formatUsd(reputation.history.total_volume)}</div>
              </div>
              <div>
                <div className="text-[10px] text-rb-text-secondary font-mono mb-1 uppercase">Network Tier</div>
                <div className={`text-lg font-bold font-mono ${(tierColors[reputation.tier] || '').split(' ')[0]}`}>
                  {reputation.tier.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: 'WIN RATE', value: `${stats.winRate.toFixed(1)}%`, sub: `${stats.totalTrades} TRADES`, color: 'text-rb-cyan' },
            { label: 'PROFIT FACTOR', value: stats.profitFactor.toFixed(2), sub: 'PROFIT/LOSS', color: stats.profitFactor >= 1 ? 'text-rb-green' : 'text-rb-red' },
            { label: 'SHARPE', value: stats.sharpeRatio.toFixed(2), sub: 'RISK ADJ.', color: 'text-rb-text-main' },
            { label: 'MAX DD', value: `${stats.maxDrawdown.toFixed(1)}%`, sub: 'HISTORICAL', color: 'text-rb-red' },
            { label: 'TOTAL TRADES', value: stats.totalTrades.toLocaleString(), sub: 'EXECUTED', color: 'text-rb-text-secondary' },
            { label: 'BALANCE', value: formatUsd(agent.balance || 0), sub: 'USDC', color: 'text-rb-cyan' },
          ].map(s => (
            <div key={s.label} className="glass-card p-5">
              <div className="text-[10px] text-rb-text-secondary font-mono mb-2">{s.label}</div>
              <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div>
              <div className="text-[9px] text-rb-text-placeholder font-mono mt-1">{s.sub}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* PnL Chart */}
          {pnlHistory.length > 0 && (
            <div className="glass-card p-8">
              <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary mb-6">Performance History</h2>
              <PnLChart data={pnlHistory} />
            </div>
          )}

          {/* Positions */}
          <div className="glass-card overflow-hidden">
            <div className="px-8 py-6 border-b border-layer-3 flex justify-between items-center">
              <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary">Active Positions</h2>
              <span className="text-[10px] font-mono text-rb-cyan">{positions.length} OPEN</span>
            </div>
            {positions.length === 0 ? (
              <div className="px-8 py-12 text-center text-rb-text-placeholder text-sm font-mono">
                No open positions
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-layer-3/10 text-[10px] font-mono text-rb-text-secondary uppercase">
                      <th className="px-8 py-3">Market</th>
                      <th className="px-8 py-3">Side</th>
                      <th className="px-8 py-3 text-right">Size</th>
                      <th className="px-8 py-3 text-right">Entry</th>
                      <th className="px-8 py-3 text-right">P&L</th>
                      <th className="px-8 py-3 text-right">Leverage</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-layer-3">
                    {positions.map(pos => {
                      const pnl = pos.unrealized_pnl || 0;
                      const market = pos.asset || 'Unknown';
                      return (
                        <tr key={pos.position_id} className="hover:bg-layer-3/10 transition-colors">
                          <td className="px-8 py-4 font-bold text-sm">{market}</td>
                          <td className="px-8 py-4">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              pos.side === 'LONG' ? 'bg-rb-green/10 text-rb-green' : 'bg-rb-red/10 text-rb-red'
                            }`}>
                              {pos.side}
                            </span>
                          </td>
                          <td className="px-8 py-4 text-right font-mono text-sm text-rb-text-main">{formatUsd(pos.size_usdc)}</td>
                          <td className="px-8 py-4 text-right font-mono text-sm text-rb-text-secondary">{formatPrice(pos.entry_price)}</td>
                          <td className={`px-8 py-4 text-right font-mono text-sm font-bold ${pnl >= 0 ? 'text-rb-green' : 'text-rb-red'}`}>
                            {formatPnl(pnl)}
                          </td>
                          <td className="px-8 py-4 text-right font-mono text-xs text-rb-text-secondary">{pos.leverage}x</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-8">
          {/* Risk Card */}
          <div className="glass-card p-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rb-text-secondary mb-6">Risk Assessment</h2>
            {risk ? (
              <div className="space-y-6">
                <div className="flex justify-between items-end">
                  <span className="text-rb-text-secondary text-xs">Overall Score</span>
                  <span className={`text-4xl font-bold font-mono ${
                    risk.level === 'LOW' ? 'text-rb-green' :
                    risk.level === 'MEDIUM' ? 'text-rb-yellow' :
                    'text-rb-red'
                  }`}>{typeof risk.score === 'number' ? risk.score.toFixed(1) : risk.score}</span>
                </div>
                <div className="text-[10px] font-mono text-rb-text-secondary uppercase text-right">
                  {risk.level}
                </div>
                <div className="h-1.5 bg-layer-3 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      risk.level === 'LOW' ? 'bg-rb-green' :
                      risk.level === 'MEDIUM' ? 'bg-rb-yellow' :
                      'bg-rb-red'
                    }`}
                    style={{ width: `${Math.min((typeof risk.score === 'number' ? risk.score : 0) * 10, 100)}%` }}
                  />
                </div>
                {risk.details && Object.keys(risk.details).length > 0 && (
                  <div className="grid gap-4">
                    {Object.entries(risk.details).map(([key, val]) => (
                      <div key={key} className="space-y-1.5">
                        <div className="flex justify-between text-[10px] font-mono">
                          <span className="text-rb-text-secondary uppercase">{key.replace(/_/g, ' ')}</span>
                          <span className="text-rb-text-main">{typeof val === 'number' ? val.toFixed(1) : String(val)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-rb-text-placeholder text-sm font-mono py-8">
                No risk data available
              </div>
            )}
          </div>

          {/* Agent Info Card */}
          <div className="glass-card p-8 bg-gradient-to-br from-rb-cyan/10 to-transparent border-rb-cyan/20">
            <h2 className="text-sm font-bold uppercase tracking-wider text-rb-cyan mb-4">Agent Info</h2>
            <div className="space-y-3 text-xs text-rb-text-secondary">
              <div className="flex justify-between">
                <span className="text-rb-text-secondary">Agent ID</span>
                <span className="font-mono text-rb-text-main truncate max-w-[180px]">{agent.agent_id}</span>
              </div>
              {agent.wallet_address && (
                <div className="flex justify-between">
                  <span className="text-rb-text-secondary">Wallet</span>
                  <span className="font-mono text-rb-text-main truncate max-w-[180px]">
                    {agent.wallet_address.slice(0, 6)}...{agent.wallet_address.slice(-4)}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-rb-text-secondary">Balance</span>
                <span className="font-mono text-rb-cyan">{formatUsd(agent.balance || 0)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
