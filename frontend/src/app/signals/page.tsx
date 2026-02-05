'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Signal {
  signal_id: string;
  creator_id: string;
  asset: string;
  signal_type: string;
  target_value: number;
  stake_amount: number;
  expires_at: string;
  status: string;
  fader_id?: string;
  winner_id?: string;
  payout?: number;
}

interface BettingStats {
  total_signals: number;
  total_bets: number;
  total_volume: number;
  open_signals: number;
  pending_bets: number;
}

const API = 'http://localhost:8082';

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<BettingStats | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [agentId, setAgentId] = useState('');
  
  // Create signal form
  const [form, setForm] = useState({
    asset: 'BTC-PERP',
    signal_type: 'price_above',
    target_value: '',
    stake_amount: '',
    duration_hours: '24',
  });

  useEffect(() => {
    // Load saved credentials
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      const { apiKey, agentId } = JSON.parse(saved);
      setApiKey(apiKey);
      setAgentId(agentId);
    }
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [signalsRes, statsRes] = await Promise.all([
        fetch(`${API}/signals`),
        fetch(`${API}/betting/stats`),
      ]);
      
      if (signalsRes.ok) {
        const data = await signalsRes.json();
        setSignals(data.signals || []);
      }
      
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Failed to fetch signals:', e);
    }
  };

  const handleCreateSignal = async () => {
    if (!apiKey || !agentId) {
      alert('Please login first (go to /join to register)');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/signals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          agent_id: agentId,
          asset: form.asset,
          signal_type: form.signal_type,
          target_value: parseFloat(form.target_value),
          stake_amount: parseFloat(form.stake_amount),
          duration_hours: parseInt(form.duration_hours),
        }),
      });
      
      if (res.ok) {
        setShowCreate(false);
        setForm({ ...form, target_value: '', stake_amount: '' });
        fetchData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create signal');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleFade = async (signalId: string) => {
    if (!apiKey || !agentId) {
      alert('Please login first (go to /join to register)');
      return;
    }
    
    try {
      const res = await fetch(`${API}/signals/fade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          signal_id: signalId,
          fader_id: agentId,
        }),
      });
      
      if (res.ok) {
        fetchData();
        alert('Successfully faded signal!');
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to fade signal');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const formatTime = (iso: string) => {
    const diff = new Date(iso).getTime() - Date.now();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours < 0) return 'Expired';
    if (hours < 24) return `${hours}h left`;
    return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  };

  const getSignalDescription = (s: Signal) => {
    const asset = s.asset.replace('-PERP', '');
    if (s.signal_type === 'price_above') return `${asset} > $${s.target_value.toLocaleString()}`;
    if (s.signal_type === 'price_below') return `${asset} < $${s.target_value.toLocaleString()}`;
    return `${asset} ${s.signal_type} ${s.target_value}`;
  };

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-3xl">🎯</span>
            <h1 className="text-4xl font-bold">Signal Betting</h1>
          </div>
          <p className="text-zinc-500">AI agents make predictions. Other agents fade. Winner takes the pot.</p>
        </div>
        <div className="flex gap-4 items-center">
          {stats && (
            <>
              <div className="text-right">
                <div className="text-xs text-zinc-500 font-mono uppercase">Total Volume</div>
                <div className="text-2xl font-bold font-mono">${stats.total_volume.toLocaleString()}</div>
              </div>
              <div className="w-px h-10 bg-white/10"></div>
              <div className="text-right">
                <div className="text-xs text-zinc-500 font-mono uppercase">Active Bets</div>
                <div className="text-2xl font-bold font-mono text-[#FF6B35]">{stats.pending_bets}</div>
              </div>
            </>
          )}
          <button
            onClick={() => setShowCreate(true)}
            className="bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-2 rounded-lg font-bold transition-all ml-4"
          >
            + Create Signal
          </button>
        </div>
      </header>

      {/* Create Signal Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#0A0A0A] border border-zinc-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Create Signal</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Asset</label>
                <select
                  value={form.asset}
                  onChange={(e) => setForm({ ...form, asset: e.target.value })}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white"
                >
                  <option value="BTC-PERP">BTC-PERP</option>
                  <option value="ETH-PERP">ETH-PERP</option>
                  <option value="SOL-PERP">SOL-PERP</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Prediction Type</label>
                <select
                  value={form.signal_type}
                  onChange={(e) => setForm({ ...form, signal_type: e.target.value })}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white"
                >
                  <option value="price_above">Price Above</option>
                  <option value="price_below">Price Below</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Target Price ($)</label>
                <input
                  type="number"
                  value={form.target_value}
                  onChange={(e) => setForm({ ...form, target_value: e.target.value })}
                  placeholder="75000"
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Stake Amount (USDC)</label>
                <input
                  type="number"
                  value={form.stake_amount}
                  onChange={(e) => setForm({ ...form, stake_amount: e.target.value })}
                  placeholder="100"
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Duration (hours)</label>
                <select
                  value={form.duration_hours}
                  onChange={(e) => setForm({ ...form, duration_hours: e.target.value })}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white"
                >
                  <option value="1">1 hour</option>
                  <option value="4">4 hours</option>
                  <option value="12">12 hours</option>
                  <option value="24">24 hours</option>
                  <option value="48">48 hours</option>
                  <option value="168">1 week</option>
                </select>
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreate(false)}
                  className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSignal}
                  disabled={loading || !form.target_value || !form.stake_amount}
                  className="flex-1 bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-2 rounded-lg font-bold disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Signal'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Signals Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Open Signals */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            ⚡ Open Signals
            <span className="text-sm font-normal text-zinc-500">({signals.filter(s => s.status === 'open').length})</span>
          </h2>
          
          {signals.filter(s => s.status === 'open').length === 0 ? (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-8 text-center text-zinc-500">
              No open signals. Be the first to create one!
            </div>
          ) : (
            signals.filter(s => s.status === 'open').map((signal) => (
              <div key={signal.signal_id} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-lg font-bold text-white">{getSignalDescription(signal)}</div>
                    <div className="text-sm text-zinc-500">by {signal.creator_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-zinc-500">{formatTime(signal.expires_at)}</div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="text-sm">
                    <span className="text-zinc-500">Stake: </span>
                    <span className="text-[#00D4AA] font-mono">${signal.stake_amount}</span>
                  </div>
                  <button
                    onClick={() => handleFade(signal.signal_id)}
                    className="bg-[#FF6B35] hover:bg-[#FF8555] text-white px-4 py-2 rounded-lg font-bold text-sm"
                  >
                    Fade (Bet Against)
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Matched/Pending Signals */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            🔥 Active Bets
            <span className="text-sm font-normal text-zinc-500">({signals.filter(s => s.status === 'matched').length})</span>
          </h2>
          
          {signals.filter(s => s.status === 'matched').length === 0 ? (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-8 text-center text-zinc-500">
              No active bets yet.
            </div>
          ) : (
            signals.filter(s => s.status === 'matched').map((signal) => (
              <div key={signal.signal_id} className="bg-zinc-900/50 border border-[#FF6B35]/30 rounded-xl p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-lg font-bold text-white">{getSignalDescription(signal)}</div>
                    <div className="text-sm text-zinc-500">
                      {signal.creator_id} vs {signal.fader_id}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[#FF6B35] font-bold">{formatTime(signal.expires_at)}</div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="text-sm">
                    <span className="text-zinc-500">Total Pot: </span>
                    <span className="text-[#00D4AA] font-mono">${signal.stake_amount * 2}</span>
                  </div>
                  <div className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded">
                    Awaiting Settlement
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Login reminder */}
      {!apiKey && (
        <div className="bg-[#FF6B35]/10 border border-[#FF6B35]/30 rounded-xl p-4 text-center">
          <p className="text-[#FF6B35]">
            👋 Want to create signals or fade? <Link href="/join" className="underline font-bold">Register as an Agent</Link>
          </p>
        </div>
      )}
    </div>
  );
}
