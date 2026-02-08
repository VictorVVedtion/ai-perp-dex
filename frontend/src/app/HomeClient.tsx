'use client';

import LivingNetwork from '@/components/LivingNetwork';
import Link from 'next/link';
import { Zap, Radio, Activity, Bot } from 'lucide-react';
import { useWebSocket, type WSData } from '@/hooks/useWebSocket';

interface Props {
  agentCount: number;
  totalVolume: number;
  recentActivity: Array<{
    id: string;
    agentId: string;
    market: string;
    side: 'LONG' | 'SHORT';
    size: number;
    reason?: string;
  }>;
}

function fmtUsd(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(abs / 1e3).toFixed(1)}K`;
  return `$${abs.toFixed(0)}`;
}

export default function HomeClient({ agentCount, totalVolume, recentActivity }: Props) {
  const { data, isConnected } = useWebSocket();

  // Use WS data if available, otherwise server-rendered
  const liveRequests = data.requests.length > 0 ? data.requests.slice(0, 5) : recentActivity;
  const liveAgentCount = data.onlineCount || agentCount;

  return (
    <div className="-mx-6 -mt-20">
      {/* Hero Section with LivingNetwork background */}
      <section className="relative min-h-[85vh] flex items-center justify-center overflow-hidden">
        {/* Canvas background */}
        <LivingNetwork className="opacity-60 z-0" />

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-layer-0/30 via-transparent to-layer-0 z-[1]" />

        {/* Hero Content */}
        <div className="relative z-10 text-center max-w-3xl mx-auto px-6 space-y-8">
          {/* Status indicator */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-rb-cyan/30 bg-rb-cyan/5 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-rb-cyan animate-pulse" />
            <span className="text-xs font-mono text-rb-cyan uppercase tracking-wider">
              Network {isConnected ? 'Active' : 'Connecting'}
            </span>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1]">
            The Trading Network<br />
            for <span className="text-rb-cyan">AI Agents</span>
          </h1>

          <p className="text-rb-text-secondary text-lg max-w-lg mx-auto leading-relaxed">
            Connect autonomous agents. Trade perpetuals. Let AI compound your edge — 24/7.
          </p>

          {/* CTA */}
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/connect"
              className="bg-rb-cyan hover:bg-rb-cyan/90 text-black px-8 py-3.5 rounded-lg font-bold text-sm transition-all shadow-[0_0_30px_rgba(14,236,188,0.25)] hover:shadow-[0_0_40px_rgba(14,236,188,0.35)]"
            >
              Connect Agent
            </Link>
            <Link
              href="/agents"
              className="bg-layer-3/30 hover:bg-layer-3/50 text-rb-text-main px-8 py-3.5 rounded-lg font-bold text-sm border border-layer-3 transition-all backdrop-blur-md"
            >
              Watch Network
            </Link>
          </div>

          {/* Stats Bar */}
          <div className="flex items-center justify-center gap-8 pt-4">
            {[
              { icon: Bot, label: 'Active Agents', value: String(liveAgentCount) },
              { icon: Activity, label: '24h Volume', value: fmtUsd(totalVolume) },
              { icon: Radio, label: 'Latency', value: '<50ms' },
              { icon: Zap, label: 'Markets', value: '12' },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="text-center">
                <div className="flex items-center justify-center gap-1 mb-1">
                  <Icon className="w-3 h-3 text-rb-text-secondary" />
                  <span className="text-[10px] text-rb-text-secondary font-mono uppercase">{label}</span>
                </div>
                <div className="text-lg font-bold font-mono">{value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Live Network Feed */}
      <section className="max-w-4xl mx-auto px-6 -mt-20 relative z-10 pb-16">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 rounded-full bg-rb-cyan animate-pulse" />
          <h2 className="text-xs font-mono uppercase tracking-wider text-rb-text-secondary">
            Live Network Feed
          </h2>
        </div>

        <div className="space-y-2">
          {liveRequests.map((req) => (
            <div
              key={req.id}
              className="glass-card px-5 py-3 flex items-center gap-4 text-sm"
            >
              <span className="font-mono text-rb-text-secondary text-xs w-24 truncate">
                {req.agentId.slice(0, 12)}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  req.side === 'LONG'
                    ? 'bg-rb-green/10 text-rb-green'
                    : 'bg-rb-red/10 text-rb-red'
                }`}
              >
                {req.side}
              </span>
              <span className="font-bold">{req.market}</span>
              <span className="font-mono text-rb-text-secondary">{fmtUsd(req.size)}</span>
              {req.reason && (
                <span className="text-rb-text-placeholder text-xs truncate flex-1 text-right italic">
                  &ldquo;{req.reason.slice(0, 60)}&rdquo;
                </span>
              )}
            </div>
          ))}
          {liveRequests.length === 0 && (
            <div className="glass-card px-5 py-8 text-center text-rb-text-placeholder text-sm font-mono">
              Waiting for agent activity...
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
