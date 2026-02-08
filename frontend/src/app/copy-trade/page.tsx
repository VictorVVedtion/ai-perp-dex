'use client';

import { useState, useEffect } from 'react';
import { getLeaderboard, getFollowing, followAgent, unfollowAgent, Agent } from '@/lib/api';
import { formatPnl, formatUsd } from '@/lib/utils';
import Link from 'next/link';
import { Trophy, Users, Copy, UserMinus } from 'lucide-react';

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

  // Confirm Unfollow Dialog
  const [unfollowTarget, setUnfollowTarget] = useState<string | null>(null);

  // Toast
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    // Check auth
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
      showToast(`Successfully followed ${selectedAgent.name}`);
      setSelectedAgent(null);
      fetchFollowing(user.id);
    } else {
      showToast('Failed to follow agent. Please try again.');
    }
  };

  const handleUnfollow = async (leaderId: string) => {
    if (!user) return;
    // Show custom confirm dialog
    setUnfollowTarget(leaderId);
  };

  const confirmUnfollow = async () => {
    if (!user || !unfollowTarget) return;
    const leaderId = unfollowTarget;
    setUnfollowTarget(null);

    const success = await unfollowAgent(user.id, leaderId);
    if (success) {
      showToast('Stopped copying agent');
      fetchFollowing(user.id);
    } else {
      showToast('Failed to unfollow. Please try again.');
    }
  };

  const isFollowing = (agentId: string) => {
    return following.some(f => f.leader_id === agentId || f.leaderId === agentId);
  };

  return (
    <div className="space-y-8 relative">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-layer-3">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-rb-text-main">Copy Trading</h1>
          <p className="text-rb-text-secondary">Automatically mirror the trades of top performing agents.</p>
        </div>
        {!user && (
           <div className="bg-rb-yellow/10 border border-rb-yellow/20 text-rb-yellow px-4 py-2 rounded-lg text-sm font-medium">
             You are viewing as guest. <Link href="/connect" className="underline font-bold hover:text-rb-yellow/80">Connect</Link> your agent to trade.
           </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Leaderboard Section */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2 text-rb-text-main">
            <Trophy className="w-6 h-6 text-rb-yellow" /> Leaderboard
          </h2>

          <div className="glass-card overflow-hidden">
             <table className="w-full text-left border-collapse">
               <thead>
                 <tr className="border-b border-layer-3 bg-layer-1/50">
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary">Rank</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary">Agent</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Win Rate</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Total PnL</th>
                   <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Action</th>
                 </tr>
               </thead>
               <tbody>
                 {loading ? (
                   <tr><td colSpan={5} className="text-center py-10 text-rb-text-secondary">Loading leaders...</td></tr>
                 ) : leaders.length === 0 ? (
                   <tr><td colSpan={5} className="text-center py-10 text-rb-text-secondary">No active agents found.</td></tr>
                 ) : (
                   leaders.map((agent, i) => (
                     <tr key={agent.id} className="border-b border-layer-3/50 hover:bg-layer-2/30 transition-colors">
                       <td className="px-6 py-4 text-rb-text-secondary font-mono">#{i + 1}</td>
                       <td className="px-6 py-4">
                         <div className="font-bold text-rb-text-main">{agent.name}</div>
                         <div className="text-xs text-rb-text-placeholder font-mono">{agent.type}</div>
                       </td>
                       <td className="px-6 py-4 text-right font-mono text-rb-text-secondary">
                         {(agent.winRate * 100).toFixed(1)}%
                       </td>
                       <td className={`px-6 py-4 text-right font-mono font-bold ${agent.pnl >= 0 ? 'text-rb-green' : 'text-rb-red'}`}>
                         {formatPnl(agent.pnl)}
                       </td>
                       <td className="px-6 py-4 text-right">
                         {isFollowing(agent.id) ? (
                           <button disabled className="text-rb-text-placeholder text-xs font-bold px-3 py-1 bg-layer-3 rounded">
                             Following
                           </button>
                         ) : (
                           <button
                             onClick={() => setSelectedAgent(agent)}
                             disabled={!user}
                             className="btn-primary px-4 py-1.5 text-xs font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                           >
                             <Copy className="w-3 h-3 inline mr-1" />
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
          <h2 className="text-xl font-bold flex items-center gap-2 text-rb-text-main">
            <Users className="w-6 h-6 text-rb-cyan" /> Following
          </h2>

          <div className="glass-card p-6 min-h-[200px]">
            {!user ? (
               <div className="text-center text-rb-text-secondary mt-10">
                 Connect your agent to view your following list.
               </div>
            ) : following.length === 0 ? (
               <div className="text-center text-rb-text-secondary mt-10">
                 You are not copying anyone yet.
               </div>
            ) : (
              <div className="space-y-4">
                {following.map((f, i) => (
                  <div key={i} className="bg-layer-2/50 border border-layer-3 p-4 rounded-lg flex flex-col gap-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-bold text-rb-text-main">Agent {f.leader_id?.slice(0, 8)}...</div>
                        <div className="text-xs text-rb-text-placeholder">Since: {new Date(f.followed_at || Date.now()).toLocaleDateString()}</div>
                      </div>
                      <button
                        onClick={() => handleUnfollow(f.leader_id || f.leaderId)}
                        className="text-rb-red text-xs hover:underline flex items-center gap-1"
                      >
                        <UserMinus className="w-3 h-3" />
                        Unfollow
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono text-rb-text-secondary bg-layer-1/50 p-2 rounded">
                       <div>Mult: {f.settings?.multiplier || '1.0'}x</div>
                       <div>Max: ${f.settings?.max_per_trade || '\u221e'}</div>
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-2xl font-bold mb-2 text-rb-text-main">Copy {selectedAgent.name}</h3>
            <p className="text-rb-text-secondary mb-6">Configure your copy trading settings for this agent.</p>

            <div className="space-y-4 mb-8">
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Multiplier (Position Size)</label>
                <input
                  type="number"
                  value={copySettings.multiplier}
                  onChange={e => setCopySettings({...copySettings, multiplier: parseFloat(e.target.value) || 1})}
                  step="0.1"
                  min="0.1"
                  className="input-base input-lg w-full"
                />
                <p className="text-xs text-rb-text-placeholder mt-1">1.0 = same size as leader. 0.5 = half size.</p>
              </div>

              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Max Amount Per Trade (USDC)</label>
                <input
                  type="number"
                  value={copySettings.max_per_trade}
                  onChange={e => setCopySettings({...copySettings, max_per_trade: parseFloat(e.target.value) || 100})}
                  step="10"
                  className="input-base input-lg w-full"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setSelectedAgent(null)}
                className="flex-1 btn-secondary-2 btn-md"
              >
                Cancel
              </button>
              <button
                onClick={handleFollow}
                className="flex-1 btn-primary btn-md"
              >
                Confirm Copy
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Unfollow Dialog (replaces native confirm()) */}
      {unfollowTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-2 text-rb-text-main">Stop Copy Trading</h3>
            <p className="text-rb-text-secondary text-sm mb-6">
              Stop copying this agent? You will no longer mirror their trades.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setUnfollowTarget(null)}
                className="flex-1 btn-secondary-2 btn-md"
              >
                Cancel
              </button>
              <button
                onClick={confirmUnfollow}
                className="flex-1 px-4 py-2 rounded-lg font-bold text-sm bg-rb-red text-white hover:bg-rb-red/90 transition-colors"
              >
                Stop Copying
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-layer-2 border border-layer-3 text-rb-text-main px-5 py-3 rounded-xl text-sm font-mono shadow-xl z-50 animate-pulse">
          {toast}
        </div>
      )}
    </div>
  );
}
