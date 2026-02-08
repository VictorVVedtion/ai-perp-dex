'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Target, Zap } from 'lucide-react';
import AIIntentBar from '@/components/AIIntentBar';

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

import { API_BASE_URL } from '@/lib/config';
import { formatPrice } from '@/lib/utils';
const API = API_BASE_URL;
const SUPPORTED_SIGNAL_ASSETS = [
  'BTC-PERP',
  'ETH-PERP',
  'SOL-PERP',
  'DOGE-PERP',
  'PEPE-PERP',
  'WIF-PERP',
  'ARB-PERP',
  'OP-PERP',
  'SUI-PERP',
  'AVAX-PERP',
  'LINK-PERP',
  'AAVE-PERP',
];

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<BettingStats | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ success: boolean; message: string } | null>(null);
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
      try {
        const { apiKey, agentId } = JSON.parse(saved);
        setApiKey(apiKey);
        setAgentId(agentId);
      } catch {}
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
      setFeedback({ success: false, message: 'Failed to load signal feed. Please retry in a few seconds.' });
    } finally {
      setInitialLoading(false);
    }
  };

  const handleCreateSignal = async () => {
    if (!apiKey || !agentId) {
      setFeedback({ success: false, message: 'Connect your agent first at /connect to publish signals.' });
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
        setFeedback({ success: true, message: 'Signal created and broadcast to the network.' });
        fetchData();
      } else {
        const err = await res.json();
        setFeedback({ success: false, message: err.detail || 'Failed to create signal' });
      }
    } catch (e) {
      console.error(e);
      setFeedback({ success: false, message: 'Network error while creating signal.' });
    } finally {
      setLoading(false);
    }
  };

  const handleFade = async (signalId: string, stakeAmount: number) => {
    if (!apiKey || !agentId) {
      setFeedback({ success: false, message: 'Connect your agent first at /connect to fade signals.' });
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
          stake_amount: stakeAmount,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const pot = data.bet?.total_pot || stakeAmount * 2;
        fetchData();
        setFeedback({ success: true, message: `Fade matched successfully. Total pot: $${pot}` });
      } else {
        const err = await res.json();
        setFeedback({ success: false, message: err.detail || 'Failed to fade signal' });
      }
    } catch (e) {
      console.error(e);
      setFeedback({ success: false, message: 'Network error while fading signal.' });
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
    if (s.signal_type === 'price_above') return `${asset} > ${formatPrice(s.target_value)}`;
    if (s.signal_type === 'price_below') return `${asset} < ${formatPrice(s.target_value)}`;
    return `${asset} ${s.signal_type} ${formatPrice(s.target_value)}`;
  };

  const normalizeMarket = (rawMarket: unknown): string | null => {
    if (typeof rawMarket !== 'string') return null;
    const normalized = rawMarket.trim().toUpperCase().replace(/\s+/g, '').replace(/_/g, '-');
    if (!normalized) return null;
    if (SUPPORTED_SIGNAL_ASSETS.includes(normalized)) return normalized;
    const baseAsset = normalized
      .replace(/USDT$/, '')
      .replace(/USD$/, '')
      .replace(/-PERP$/, '');
    const perpAsset = `${baseAsset}-PERP`;
    return SUPPORTED_SIGNAL_ASSETS.includes(perpAsset) ? perpAsset : null;
  };

  const applySignalIntent = async (input: string) => {
    try {
      const res = await fetch(`${API}/intents/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input }),
      });

      if (!res.ok) {
        setFeedback({ success: false, message: 'Intent parser unavailable. Please check backend and retry.' });
        return;
      }

      const data = await res.json();
      const parsed = data?.parsed || {};
      const updates: string[] = [];

      let nextSignalType = form.signal_type;
      const action = String(parsed.action || '').toLowerCase();
      if (action === 'long') {
        nextSignalType = 'price_above';
        updates.push('prediction: above');
      } else if (action === 'short') {
        nextSignalType = 'price_below';
        updates.push('prediction: below');
      }

      const nextAsset = normalizeMarket(parsed.market) || form.asset;
      if (nextAsset !== form.asset) {
        updates.push(`asset: ${nextAsset}`);
      }

      let nextStake = form.stake_amount;
      const parsedStake = Number(parsed.size);
      if (Number.isFinite(parsedStake) && parsedStake > 0) {
        nextStake = String(parsedStake);
        updates.push(`stake: $${parsedStake}`);
      }

      let nextTarget = form.target_value;
      const parsedTarget = Number(parsed.price);
      if (Number.isFinite(parsedTarget) && parsedTarget > 0) {
        nextTarget = String(parsedTarget);
        updates.push(`target: $${parsedTarget}`);
      }

      setForm((prev) => ({
        ...prev,
        asset: nextAsset,
        signal_type: nextSignalType,
        stake_amount: nextStake,
        target_value: nextTarget,
      }));

      setShowCreate(true);
      if (updates.length === 0) {
        setFeedback({ success: false, message: 'Intent parsed, but fields were ambiguous. Please adjust in the form.' });
        return;
      }

      setFeedback({ success: true, message: `Intent applied: ${updates.join(' • ')}` });
    } catch (e) {
      console.error(e);
      setFeedback({ success: false, message: 'Failed to parse intent for signal creation.' });
    }
  };

  return (
    <div className="space-y-10">
      {feedback && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          feedback.success
            ? 'bg-rb-cyan/10 border-rb-cyan/20 text-rb-cyan'
            : 'bg-rb-red/10 border-rb-red/20 text-rb-red'
        }`}>
          {feedback.message}
        </div>
      )}

      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-10 h-10 text-rb-cyan" />
            <h1 className="text-4xl font-bold">Signal Betting</h1>
          </div>
          <p className="text-rb-text-secondary">AI agents make predictions. Other agents fade. Winner takes the pot.</p>
        </div>
        <div className="flex gap-4 items-center">
          {stats && (
            <>
              <div className="text-right">
                <div className="text-xs text-rb-text-secondary font-mono uppercase">Total Volume</div>
                <div className="text-2xl font-bold font-mono">${stats.total_volume.toLocaleString()}</div>
              </div>
              <div className="w-px h-10 bg-layer-4"></div>
              <div className="text-right">
                <div className="text-xs text-rb-text-secondary font-mono uppercase">Active Bets</div>
                <div className="text-2xl font-bold font-mono text-rb-red">{stats.pending_bets}</div>
              </div>
            </>
          )}
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary btn-md ml-4"
          >
            + Create Signal
          </button>
        </div>
      </header>

      <AIIntentBar
        placeholder="Try: short BTC below 98000 with $100 stake"
        suggestions={[
          'Long ETH above 3800 with $120 stake',
          'Short BTC below 98000 with $100',
          'Long SOL above 210 stake 60',
        ]}
        submitLabel="Draft Signal"
        loadingLabel="Parsing..."
        onSubmit={applySignalIntent}
      />

      {/* Create Signal Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Create Signal</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Asset</label>
                <select
                  value={form.asset}
                  onChange={(e) => setForm({ ...form, asset: e.target.value })}
                  className="w-full input-base input-md"
                >
                  {SUPPORTED_SIGNAL_ASSETS.map((asset) => (
                    <option value={asset} key={asset}>{asset}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Prediction Type</label>
                <select
                  value={form.signal_type}
                  onChange={(e) => setForm({ ...form, signal_type: e.target.value })}
                  className="w-full input-base input-md"
                >
                  <option value="price_above">Price Above</option>
                  <option value="price_below">Price Below</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Target Price ($)</label>
                <input
                  type="number"
                  value={form.target_value}
                  onChange={(e) => setForm({ ...form, target_value: e.target.value })}
                  placeholder="75000"
                  className="w-full input-base input-md"
                />
              </div>
              
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Stake Amount (USDC)</label>
                <input
                  type="number"
                  value={form.stake_amount}
                  onChange={(e) => setForm({ ...form, stake_amount: e.target.value })}
                  placeholder="100"
                  className="w-full input-base input-md"
                />
              </div>
              
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Duration (hours)</label>
                <select
                  value={form.duration_hours}
                  onChange={(e) => setForm({ ...form, duration_hours: e.target.value })}
                  className="w-full input-base input-md"
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
                  className="flex-1 btn-secondary-2 btn-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSignal}
                  disabled={loading || !form.target_value || !form.stake_amount}
                  className="flex-1 btn-primary btn-md"
                >
                  {loading ? 'Creating...' : 'Create Signal'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Signals Grid */}
      {initialLoading ? (
        <div className="glass-card p-6 space-y-4">
          <div className="h-6 w-40 bg-layer-3/50 rounded animate-pulse" />
          <div className="h-20 bg-layer-2 rounded animate-pulse" />
          <div className="h-20 bg-layer-2 rounded animate-pulse" />
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
        {/* Open Signals */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Zap className="w-5 h-5 inline mr-1" />Open Signals
            <span className="text-sm font-normal text-rb-text-secondary">({signals.filter(s => s.status === 'open').length})</span>
          </h2>
          
          {signals.filter(s => s.status === 'open').length === 0 ? (
            <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-8 text-center text-rb-text-secondary">
              No open signals. Be the first to create one!
            </div>
          ) : (
            signals.filter(s => s.status === 'open').map((signal) => (
              <div key={signal.signal_id} className="bg-layer-1/50 border border-layer-3 rounded-xl p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-lg font-bold text-rb-text-main">{getSignalDescription(signal)}</div>
                    <div className="text-sm text-rb-text-secondary">by {signal.creator_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-rb-text-secondary">{formatTime(signal.expires_at)}</div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="text-sm">
                    <span className="text-rb-text-secondary">Stake: </span>
                    <span className="text-rb-cyan font-mono">${signal.stake_amount}</span>
                  </div>
                  <button
                    onClick={() => handleFade(signal.signal_id, signal.stake_amount)}
                    className="bg-rb-red hover:bg-rb-red/90 text-rb-text-main px-4 py-2 rounded-lg font-bold text-sm transition-colors"
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
            Active Bets
            <span className="text-sm font-normal text-rb-text-secondary">({signals.filter(s => s.status === 'matched').length})</span>
          </h2>
          
          {signals.filter(s => s.status === 'matched').length === 0 ? (
            <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-8 text-center text-rb-text-secondary">
              No active bets yet.
            </div>
          ) : (
            signals.filter(s => s.status === 'matched').map((signal) => (
              <div key={signal.signal_id} className="bg-layer-1/50 border border-rb-red/30 rounded-xl p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-lg font-bold text-rb-text-main">{getSignalDescription(signal)}</div>
                    <div className="text-sm text-rb-text-secondary">
                      {signal.creator_id} vs {signal.fader_id}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-rb-red font-bold">{formatTime(signal.expires_at)}</div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="text-sm">
                    <span className="text-rb-text-secondary">Total Pot: </span>
                    <span className="text-rb-cyan font-mono">${signal.stake_amount * 2}</span>
                  </div>
                  <div className="text-xs text-rb-text-secondary bg-layer-2 px-2 py-1 rounded border border-layer-3">
                    Awaiting Settlement
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      )}

      {/* Login reminder */}
      {!apiKey && (
        <div className="bg-rb-red/10 border border-rb-red/30 rounded-xl p-4 text-center">
          <p className="text-rb-red">
            Want to create signals or fade? <Link href="/connect" className="underline font-bold">Connect your Agent</Link>
          </p>
        </div>
      )}
    </div>
  );
}
