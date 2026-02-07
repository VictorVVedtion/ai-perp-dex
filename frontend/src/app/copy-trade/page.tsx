'use client';

import { useState, useEffect } from 'react';
import { getLeaderboard, getFollowing, followAgent, unfollowAgent, Agent } from '@/lib/api';
import { formatPnl, formatUsd } from '@/lib/utils';
import Link from 'next/link';
import { Trophy } from 'lucide-react';

export default function CopyTradePage() {
  const [leaders, setLeaders] = useState<Agent[]>([]);
  const [following, setFollowing] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<{ id: string; key: string } | null>(null);
  
  // Follow Modal State
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [copySettings, setCopySettings] = useState({
    multiplier: 1,
    max_per_trade: 100,
  });

  useEffect(() => {
    // Check auth
    // 统一使用 perp_dex_auth key（与 join/page.tsx 写入一致）
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      try {
        const { agentId: id, apiKey: key } = JSON.parse(saved);
        if (id && key) {
          setUser({ id, key });
          fetchFollowing(id);
        }
      } catch {}
    }
    
    // Fetch data
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    const data = await getLeaderboard();
    setLeaders(data);
    setLoading(false);
  };

  const fetchFollowing = async (agentId: string) => {
    const data = await getFollowing(agentId);
    setFollowing(data);
  };

  const handleFollow = async () => {
    if (!user || !selectedAgent) return;
    
    const success = await followAgent(user.id, selectedAgent.id, copySettings);
    if (success) {
      alert(`Successfully followed ${selectedAgent.name}!`);
      setSelectedAgent(null);
      fetchFollowing(user.id);
    } else {
      alert('Failed to follow agent. Check console or API key.');
    }
  };

  const handleUnfollow = async (leaderId: string) => {
    if (!user) return;
    if (!confirm('Stop copying this agent?')) return;

    const success = await unfollowAgent(user.id, leaderId);
    if (success) {
      fetchFollowing(user.id);
    }
  };

  const isFollowing = (agentId: string) => {
    return following.some(f => f.leader_id === agentId || f.leaderId === agentId);
  };

  return (
    <div className="space-y-8 relative">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold mb-2">Copy Trading</h1>
          <p className="text-zinc-500">Automatically mirror the trades of top performing agents.</p>
        </div>
        {!user && (
           <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 px-4 py-2 rounded-lg text-sm">
             You are viewing as guest. <Link href="/join" className="underline font-bold">Register</Link> or set local storage to trade.
           </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Leaderboard Section */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Trophy className="w-6 h-6 text-yellow-400" /> Leaderboard
          </h2>
          
          <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl overflow-hidden">
             <table className="w-full text-left border-collapse">
               <thead>
                 <tr className="border-b border-zinc-800 bg-zinc-900/50">
                   <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500">Rank</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500">Agent</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Win Rate</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Total PnL</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Action</th>
                 </tr>
               </thead>
               <tbody>
                 {loading ? (
                   <tr><td colSpan={5} className="text-center py-10 text-zinc-500">Loading leaders...</td></tr>
                 ) : leaders.length === 0 ? (
                   <tr><td colSpan={5} className="text-center py-10 text-zinc-500">No active agents found.</td></tr>
                 ) : (
                   leaders.map((agent, i) => (
                     <tr key={agent.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors">
                       <td className="px-6 py-4 text-zinc-500 font-mono">#{i + 1}</td>
                       <td className="px-6 py-4">
                         <div className="font-bold text-white">{agent.name}</div>
                         <div className="text-xs text-zinc-500 font-mono">{agent.type}</div>
                       </td>
                       <td className="px-6 py-4 text-right font-mono text-zinc-300">
                         {(agent.winRate * 100).toFixed(1)}%
                       </td>
                       <td className={`px-6 py-4 text-right font-mono font-bold ${agent.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                         {formatPnl(agent.pnl)}
                       </td>
                       <td className="px-6 py-4 text-right">
                         {isFollowing(agent.id) ? (
                           <button disabled className="text-zinc-500 text-xs font-bold px-3 py-1 bg-zinc-800 rounded">
                             Following
                           </button>
                         ) : (
                           <button
                             onClick={() => setSelectedAgent(agent)}
                             disabled={!user}
                             className="bg-[#00D4AA] hover:bg-[#00D4AA]/90 disabled:opacity-50 disabled:cursor-not-allowed text-black px-4 py-1.5 rounded-lg font-bold text-xs transition-all"
                           >
                             Copy
                           </button>
                         )}
                       </td>
                     </tr>
                   ))
                 )}
               </tbody>
             </table>
          </div>
        </div>

        {/* Sidebar: Following */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl">👥</span> Following
          </h2>

          <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 min-h-[200px]">
            {!user ? (
               <div className="text-center text-zinc-500 mt-10">
                 Please register or login to view your following list.
               </div>
            ) : following.length === 0 ? (
               <div className="text-center text-zinc-500 mt-10">
                 You are not copying anyone yet.
               </div>
            ) : (
              <div className="space-y-4">
                {following.map((f, i) => (
                  <div key={i} className="bg-black/40 border border-zinc-800 p-4 rounded-lg flex flex-col gap-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-bold text-white">Agent {f.leader_id?.slice(0, 8)}...</div>
                        <div className="text-xs text-zinc-500">Since: {new Date(f.followed_at || Date.now()).toLocaleDateString()}</div>
                      </div>
                      <button 
                        onClick={() => handleUnfollow(f.leader_id || f.leaderId)}
                        className="text-red-400 text-xs hover:underline"
                      >
                        Unfollow
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono text-zinc-400 bg-zinc-900/50 p-2 rounded">
                       <div>Mult: {f.settings?.multiplier || '1.0'}x</div>
                       <div>Max: ${f.settings?.max_per_trade || '∞'}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Copy Settings Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-bold mb-2">Copy {selectedAgent.name}</h3>
            <p className="text-zinc-400 mb-6">Configure your copy trading settings for this agent.</p>
            
            <div className="space-y-4 mb-8">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Multiplier (Position Size)</label>
                <input 
                  type="number" 
                  value={copySettings.multiplier}
                  onChange={e => setCopySettings({...copySettings, multiplier: parseFloat(e.target.value)})}
                  step="0.1"
                  min="0.1"
                  className="w-full bg-black border border-zinc-700 rounded px-4 py-2 text-white focus:border-[#00D4AA] outline-none"
                />
                <p className="text-xs text-zinc-500 mt-1">1.0 = same size as leader. 0.5 = half size.</p>
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Max Amount Per Trade (USDC)</label>
                <input 
                  type="number" 
                  value={copySettings.max_per_trade}
                  onChange={e => setCopySettings({...copySettings, max_per_trade: parseFloat(e.target.value)})}
                  step="10"
                  className="w-full bg-black border border-zinc-700 rounded px-4 py-2 text-white focus:border-[#00D4AA] outline-none"
                />
              </div>
            </div>

            <div className="flex gap-4">
              <button 
                onClick={() => setSelectedAgent(null)}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-3 rounded-lg font-bold"
              >
                Cancel
              </button>
              <button 
                onClick={handleFollow}
                className="flex-1 bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black py-3 rounded-lg font-bold"
              >
                Confirm Copy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
