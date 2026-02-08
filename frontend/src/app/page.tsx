import { getMarkets, getAgents, getRequests } from '@/lib/api';
import Link from 'next/link';
import { Zap, Radio, Activity } from 'lucide-react';
import HomeClient from './HomeClient';

export const dynamic = 'force-dynamic';

function fmtUsd(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(abs / 1e3).toFixed(1)}K`;
  return `$${abs.toFixed(0)}`;
}

export default async function Home() {
  const [agents, markets, requests] = await Promise.all([
    getAgents(),
    getMarkets(),
    getRequests(),
  ]);

  const totalVolume = markets.reduce((s, m) => s + (m.volume24h || 0), 0);
  const recentActivity = requests.slice(0, 5);

  return (
    <HomeClient
      agentCount={agents.length}
      totalVolume={totalVolume}
      recentActivity={recentActivity}
    />
  );
}
