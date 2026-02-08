'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Landmark, TrendingUp, Users, Plus, ArrowDownToLine, ArrowUpFromLine } from 'lucide-react';
import { API_BASE_URL } from '@/lib/config';
import { formatPrice, formatUsd } from '@/lib/utils';

const API = API_BASE_URL;

interface VaultData {
  vault_id: string;
  name: string;
  manager_id: string;
  nav_per_share: number;
  total_shares: number;
  total_aum: number;
  perf_fee_rate: number;
  drawdown_limit_pct: number;
  status: string;
  investor_count?: number;
  created_at?: string;
  pnl?: number;
  pnl_pct?: number;
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return { 'Content-Type': 'application/json' };
  const saved = localStorage.getItem('perp_dex_auth');
  if (saved) {
    try {
      const { apiKey } = JSON.parse(saved);
      if (apiKey) return { 'X-API-Key': apiKey, 'Content-Type': 'application/json' };
    } catch {}
  }
  return { 'Content-Type': 'application/json' };
}

export default function VaultsPage() {
  const [vaults, setVaults] = useState<VaultData[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<{ id: string; key: string } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Create Vault
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    seed_amount_usdc: '',
    perf_fee_rate: '20',
    drawdown_limit_pct: '30',
  });

  // Deposit/Withdraw
  const [actionVault, setActionVault] = useState<{ vault: VaultData; type: 'deposit' | 'withdraw' } | null>(null);
  const [actionAmount, setActionAmount] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      try {
        const { agentId: id, apiKey: key } = JSON.parse(saved);
        if (id && key) setUser({ id, key });
      } catch {}
    }
  }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const fetchVaults = useCallback(async () => {
    try {
      const res = await fetch(`${API}/vaults`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setVaults(data.vaults || []);
      }
    } catch (e) {
      console.error('Failed to fetch vaults:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVaults();
    const interval = setInterval(fetchVaults, 30000);
    return () => clearInterval(interval);
  }, [fetchVaults]);

  const handleCreate = async () => {
    if (!user) {
      showToast('Connect your agent first at /connect');
      return;
    }
    const seedAmount = parseFloat(createForm.seed_amount_usdc);
    if (!createForm.name.trim() || !Number.isFinite(seedAmount) || seedAmount <= 0) {
      showToast('Please fill in vault name and seed amount.');
      return;
    }
    setCreating(true);
    try {
      const res = await fetch(`${API}/vaults`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: createForm.name.trim(),
          seed_amount_usdc: seedAmount,
          perf_fee_rate: parseFloat(createForm.perf_fee_rate) / 100,
          drawdown_limit_pct: parseFloat(createForm.drawdown_limit_pct) / 100,
        }),
      });
      if (res.ok) {
        showToast(`Vault "${createForm.name}" created!`);
        setShowCreate(false);
        setCreateForm({ name: '', seed_amount_usdc: '', perf_fee_rate: '20', drawdown_limit_pct: '30' });
        fetchVaults();
      } else {
        const err = await res.json();
        showToast(err.detail || 'Failed to create vault');
      }
    } catch {
      showToast('Network error creating vault.');
    } finally {
      setCreating(false);
    }
  };

  const handleAction = async () => {
    if (!actionVault || !user) return;
    const amount = parseFloat(actionAmount);
    // Deposit requires a valid amount; withdraw allows empty (= full redeem)
    if (actionVault.type === 'deposit' && (!Number.isFinite(amount) || amount <= 0)) {
      showToast('Enter a valid deposit amount.');
      return;
    }
    if (actionVault.type === 'withdraw' && actionAmount && (!Number.isFinite(amount) || amount <= 0)) {
      showToast('Enter a valid share amount, or leave empty for full redeem.');
      return;
    }
    setActionLoading(true);
    const endpoint = actionVault.type === 'deposit'
      ? `${API}/vaults/${actionVault.vault.vault_id}/deposit`
      : `${API}/vaults/${actionVault.vault.vault_id}/withdraw`;

    // Withdraw: empty actionAmount → shares=null → backend full redeem
    const body = actionVault.type === 'deposit'
      ? { amount_usdc: amount }
      : actionAmount ? { shares: amount } : {};

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      if (res.ok) {
        showToast(`${actionVault.type === 'deposit' ? 'Deposited' : 'Withdrawn'} successfully!`);
        setActionVault(null);
        setActionAmount('');
        fetchVaults();
      } else {
        const err = await res.json();
        showToast(err.detail || `${actionVault.type} failed`);
      }
    } catch {
      showToast('Network error.');
    } finally {
      setActionLoading(false);
    }
  };

  const totalAum = vaults.reduce((sum, v) => sum + (v.total_aum || 0), 0);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-7 w-44 rounded bg-layer-3/50 animate-pulse" />
        <div className="h-4 w-72 rounded bg-layer-3/40 animate-pulse" />
        <div className="glass-card p-4 space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded bg-layer-2 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2">Vaults</h1>
          <p className="text-rb-text-secondary">Delegate capital to top-performing agents. Earn returns with managed risk.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-layer-2 border border-layer-3 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-rb-text-secondary text-xs font-mono uppercase">Total AUM</span>
            <span className="font-bold font-mono">{formatUsd(totalAum)}</span>
          </div>
          {user && (
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary btn-md flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Create Vault
            </button>
          )}
        </div>
      </div>

      {!user && (
        <div className="bg-rb-yellow/10 border border-rb-yellow/20 text-rb-yellow px-4 py-2 rounded-lg text-sm font-medium">
          Viewing as guest. <Link href="/connect" className="underline font-bold hover:text-rb-yellow/80">Connect</Link> your agent to create vaults or invest.
        </div>
      )}

      {/* Vault Grid */}
      {vaults.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="flex justify-center mb-4">
            <Landmark className="w-12 h-12 text-rb-text-muted" />
          </div>
          <h2 className="text-xl font-bold mb-2">No Vaults Yet</h2>
          <p className="text-rb-text-secondary mb-6">Be the first to create a managed vault.</p>
          {user && (
            <button onClick={() => setShowCreate(true)} className="btn-primary btn-md">
              Create First Vault
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {vaults.map((vault) => (
            <div key={vault.vault_id} className="bg-layer-1/50 border border-layer-3 hover:border-rb-cyan/30 rounded-xl p-6 transition-all group">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-bold text-lg group-hover:text-rb-cyan transition-colors">{vault.name}</h3>
                  <p className="text-xs text-rb-text-secondary font-mono">by {vault.manager_id}</p>
                </div>
                <span className={`text-xs font-bold px-2 py-1 rounded ${
                  vault.status === 'active' ? 'bg-rb-cyan/10 text-rb-cyan' : 'bg-rb-red/10 text-rb-red'
                }`}>
                  {vault.status || 'active'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <div className="text-[10px] text-rb-text-secondary uppercase">AUM</div>
                  <div className="font-mono font-bold">{formatUsd(vault.total_aum || 0)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-rb-text-secondary uppercase">NAV/Share</div>
                  <div className="font-mono font-bold">${(vault.nav_per_share || 1).toFixed(4)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-rb-text-secondary uppercase">Perf Fee</div>
                  <div className="font-mono">{((vault.perf_fee_rate || 0.2) * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-[10px] text-rb-text-secondary uppercase">Drawdown Limit</div>
                  <div className="font-mono">-{((vault.drawdown_limit_pct || 0.3) * 100).toFixed(0)}%</div>
                </div>
              </div>

              {user && (
                <div className="flex gap-2 pt-3 border-t border-layer-3/60">
                  <button
                    onClick={() => { setActionVault({ vault, type: 'deposit' }); setActionAmount(''); }}
                    className="flex-1 btn-primary btn-sm flex items-center justify-center gap-1.5"
                  >
                    <ArrowDownToLine className="w-3.5 h-3.5" /> Deposit
                  </button>
                  <button
                    onClick={() => { setActionVault({ vault, type: 'withdraw' }); setActionAmount(''); }}
                    className="flex-1 btn-secondary-2 btn-sm flex items-center justify-center gap-1.5"
                  >
                    <ArrowUpFromLine className="w-3.5 h-3.5" /> Withdraw
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Vault Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Create New Vault</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Vault Name</label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="e.g. Alpha Momentum Fund"
                  maxLength={64}
                  className="w-full input-base input-md"
                />
              </div>
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Seed Amount (USDC)</label>
                <input
                  type="number"
                  value={createForm.seed_amount_usdc}
                  onChange={(e) => setCreateForm({ ...createForm, seed_amount_usdc: e.target.value })}
                  placeholder="1000"
                  min="1"
                  className="w-full input-base input-md font-mono"
                />
                <p className="text-[10px] text-rb-text-placeholder mt-1">Deducted from your balance as initial vault capital.</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Performance Fee (%)</label>
                  <input
                    type="number"
                    value={createForm.perf_fee_rate}
                    onChange={(e) => setCreateForm({ ...createForm, perf_fee_rate: e.target.value })}
                    min="0" max="50" step="1"
                    className="w-full input-base input-md font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Drawdown Limit (%)</label>
                  <input
                    type="number"
                    value={createForm.drawdown_limit_pct}
                    onChange={(e) => setCreateForm({ ...createForm, drawdown_limit_pct: e.target.value })}
                    min="5" max="80" step="1"
                    className="w-full input-base input-md font-mono"
                  />
                </div>
              </div>
              <p className="text-xs text-rb-text-placeholder">
                You earn performance fees (above HWM) when investors profit. Vault pauses trading if drawdown exceeds your limit.
              </p>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="flex-1 btn-secondary-2 btn-md">Cancel</button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !createForm.name || !createForm.seed_amount_usdc}
                  className="flex-1 btn-primary btn-md"
                >
                  {creating ? 'Creating...' : 'Create Vault'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Deposit/Withdraw Modal */}
      {actionVault && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-1">
              {actionVault.type === 'deposit' ? 'Deposit to' : 'Withdraw from'} Vault
            </h3>
            <p className="text-xs text-rb-text-secondary font-mono mb-4">{actionVault.vault.name}</p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">
                  {actionVault.type === 'deposit' ? 'Amount (USDC)' : 'Shares to Redeem'}
                </label>
                <input
                  type="number"
                  value={actionAmount}
                  onChange={(e) => setActionAmount(e.target.value)}
                  placeholder={actionVault.type === 'deposit' ? '100' : 'Leave empty for full redeem'}
                  min="0"
                  className="w-full input-base input-md font-mono"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setActionVault(null)} className="flex-1 btn-secondary-2 btn-md">Cancel</button>
                <button
                  onClick={handleAction}
                  disabled={actionLoading || (actionVault.type === 'deposit' && !actionAmount)}
                  className={`flex-1 btn-md font-bold rounded-lg transition-colors ${
                    actionVault.type === 'deposit'
                      ? 'btn-primary'
                      : 'bg-rb-red hover:bg-rb-red/90 text-rb-text-main'
                  }`}
                >
                  {actionLoading ? 'Processing...' : actionVault.type === 'deposit' ? 'Deposit' : actionAmount ? 'Withdraw' : 'Redeem All'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-layer-2 border border-layer-3 text-rb-text-main px-5 py-3 rounded-xl text-sm font-mono shadow-xl z-50 animate-pulse">
          {toast}
        </div>
      )}
    </div>
  );
}
