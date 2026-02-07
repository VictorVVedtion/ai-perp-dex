'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { Bot, BarChart3, Target, TrendingUp } from 'lucide-react';

interface NetworkStatsProps {
  agentCount: number;
  volume24h: number;
  activeSignals: number;
  topAgentPnl: number;
}

function fmtUsd(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(abs / 1e3).toFixed(1)}K`;
  return `$${abs.toFixed(0)}`;
}

export default function NetworkStats({ agentCount, volume24h, activeSignals, topAgentPnl }: NetworkStatsProps) {
  const { data } = useWebSocket();
  const liveAgents = data.onlineCount > 0 ? data.onlineCount : agentCount;

  const stats = [
    {
      label: 'Agents Online',
      value: liveAgents.toString(),
      icon: Bot,
      color: 'text-rb-cyan',
    },
    {
      label: '24h Volume',
      value: fmtUsd(volume24h),
      icon: BarChart3,
      color: 'text-rb-text-main',
    },
    {
      label: 'Active Signals',
      value: activeSignals.toString(),
      icon: Target,
      color: 'text-rb-yellow',
    },
    {
      label: 'Top Agent PnL',
      value: `${topAgentPnl >= 0 ? '+' : ''}${fmtUsd(topAgentPnl)}`,
      icon: TrendingUp,
      color: topAgentPnl >= 0 ? 'text-rb-cyan' : 'text-rb-red',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="bg-layer-1 border border-layer-3 rounded-lg px-4 py-3 flex items-center gap-3">
          <Icon className={`w-5 h-5 ${color} shrink-0`} />
          <div>
            <div className="text-[10px] text-rb-text-secondary uppercase tracking-wider font-mono">{label}</div>
            <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
