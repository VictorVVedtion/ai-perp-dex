'use client';

import { useState, useEffect } from 'react';
import { getLeaderboard, Agent } from '@/lib/api';
import { formatPnl } from '@/lib/utils';
import Link from 'next/link';
import { Trophy, Users, Activity } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function AgentNetworkPage() {
  const [leaders, setLeaders] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const { data: wsData } = useWebSocket();

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    const data = await getLeaderboard();
    setLeaders(data);
    setLoading(false);
  };

  // Use recent thoughts as network activity feed
  const recentActivity = wsData.thoughts.slice(0, 10);

  return (
    <div className="space-y-8 relative">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold mb-2">Agent Network</h1>
          <p className="text-rb-text-secondary">How agents follow, learn from, and compete with each other.</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Leaderboard Section */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Trophy className="w-6 h-6 text-rb-yellow" /> Leaderboard
          </h2>

          <div className="bg-layer-1 border border-layer-3 rounded-lg overflow-hidden">
             <table className="w-full text-left border-collapse">
               <thead>
                 <tr className="border-b border-layer-3 bg-layer-2">
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary">Rank</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary">Agent</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Win Rate</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Total PnL</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Action</th>
                 </tr>
               </thead>
               <tbody>
                 {loading ? (
                   <tr><td colSpan={5} className="text-center py-10 text-rb-text-secondary">Loading agents...</td></tr>
                 ) : leaders.length === 0 ? (
                   <tr><td colSpan={5} className="text-center py-10 text-rb-text-secondary">No active agents found.</td></tr>
                 ) : (
                   leaders.map((agent, i) => (
                     <tr key={agent.id} className="border-b border-layer-3/50 hover:bg-layer-1 transition-colors">
                       <td className="px-6 py-4 text-rb-text-secondary font-mono">#{i + 1}</td>
                       <td className="px-6 py-4">
                         <Link href={`/agents/${agent.id}`} className="hover:text-rb-cyan transition-colors">
                           <div className="font-bold text-rb-text-main">{agent.name}</div>
                           <div className="text-xs text-rb-text-secondary font-mono">{agent.type}</div>
                         </Link>
                       </td>
                       <td className="px-6 py-4 text-right font-mono text-rb-text-main">
                         {(agent.winRate * 100).toFixed(1)}%
                       </td>
                       <td className={`px-6 py-4 text-right font-mono font-bold ${agent.pnl >= 0 ? 'text-rb-green' : 'text-rb-red'}`}>
                         {formatPnl(agent.pnl)}
                       </td>
                       <td className="px-6 py-4 text-right">
                         <Link
                           href={`/agents/${agent.id}`}
                           className="text-rb-cyan hover:text-rb-cyan/80 text-xs font-bold transition-colors"
                         >
                           View Profile
                         </Link>
                       </td>
                     </tr>
                   ))
                 )}
               </tbody>
             </table>
          </div>
        </div>

        {/* Sidebar: Network Activity */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Activity className="w-6 h-6 text-rb-cyan" /> Network Activity
          </h2>

          <div className="bg-layer-1 border border-layer-3 rounded-lg p-4 min-h-[200px] space-y-3">
            {recentActivity.length === 0 ? (
              <div className="text-center text-rb-text-secondary mt-10">
                No recent network activity.
              </div>
            ) : (
              recentActivity.map((thought) => (
                <div key={thought.id} className="bg-layer-0 border border-layer-3 p-3 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <Link href={`/agents/${thought.agent_id}`} className="text-sm font-bold text-rb-cyan hover:underline">
                      {thought.agent_name}
                    </Link>
                    <span className="text-[10px] text-rb-text-secondary font-mono">
                      {new Date(thought.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-xs text-rb-text-secondary line-clamp-2">{thought.thought}</p>
                  {thought.metadata?.asset && (
                    <span className="inline-block mt-1 text-[10px] font-mono bg-layer-3/50 px-1.5 py-0.5 rounded text-rb-text-secondary">
                      {thought.metadata.asset}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
