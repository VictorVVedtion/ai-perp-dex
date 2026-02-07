'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Briefcase, TrendingUp, Lock } from 'lucide-react';

interface Position {
  position_id: string;
  asset: string;
  side: string;
  size_usdc: number;
  entry_price: number;
  leverage: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  liquidation_price: number;
  stop_loss?: number;
  take_profit?: number;
  is_open: boolean;
}

interface Balance {
  balance: number;
  locked: number;
  available: number;
}

import { API_BASE_URL } from '@/lib/config';
import { formatPrice } from '@/lib/utils';
const API = API_BASE_URL;

export default function PortfolioPage() {
  const [apiKey, setApiKey] = useState('');
  const [agentId, setAgentId] = useState('');
  const [positions, setPositions] = useState<Position[]>([]);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [loading, setLoading] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [loginInput, setLoginInput] = useState({ apiKey: '', agentId: '' });
  const [depositAmount, setDepositAmount] = useState('');
  const [showDeposit, setShowDeposit] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [showWithdraw, setShowWithdraw] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      const { apiKey, agentId } = JSON.parse(saved);
      setApiKey(apiKey);
      setAgentId(agentId);
    }
  }, []);

  useEffect(() => {
    if (agentId && apiKey) {
      fetchPortfolio();
    }
  }, [agentId, apiKey]);

  const fetchPortfolio = async () => {
    if (!agentId || !apiKey) return;
    
    const headers = { 'X-API-Key': apiKey };
    
    try {
      const [posRes, balRes] = await Promise.all([
        fetch(`${API}/positions/${agentId}`, { headers }),
        fetch(`${API}/balance/${agentId}`, { headers }),
      ]);
      
      if (posRes.ok) {
        const data = await posRes.json();
        setPositions(data.positions || []);
      }
      
      if (balRes.ok) {
        const data = await balRes.json();
        setBalance(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogin = () => {
    if (!loginInput.apiKey || !loginInput.agentId) return;
    
    localStorage.setItem('perp_dex_auth', JSON.stringify({
      apiKey: loginInput.apiKey,
      agentId: loginInput.agentId,
    }));
    
    setApiKey(loginInput.apiKey);
    setAgentId(loginInput.agentId);
    setShowLogin(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('perp_dex_auth');
    setApiKey('');
    setAgentId('');
    setPositions([]);
    setBalance(null);
  };

  const handleDeposit = async () => {
    if (!apiKey || !agentId || !depositAmount) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/deposit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          agent_id: agentId,
          amount: parseFloat(depositAmount),
        }),
      });
      
      if (res.ok) {
        setShowDeposit(false);
        setDepositAmount('');
        fetchPortfolio();
      } else {
        const err = await res.json();
        alert(err.detail || 'Deposit failed');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!apiKey || !agentId || !withdrawAmount) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/withdraw`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          agent_id: agentId,
          amount: parseFloat(withdrawAmount),
        }),
      });
      
      if (res.ok) {
        setShowWithdraw(false);
        setWithdrawAmount('');
        fetchPortfolio();
      } else {
        const err = await res.json();
        alert(err.detail || 'Withdraw failed');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    if (!apiKey) return;
    
    if (!confirm('Are you sure you want to close this position?')) return;
    
    try {
      const res = await fetch(`${API}/positions/${positionId}/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });
      
      if (res.ok) {
        fetchPortfolio();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to close position');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Not logged in
  if (!agentId) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <div className="flex justify-center mb-6"><Lock className="w-16 h-16 text-zinc-600" /></div>
        <h1 className="text-3xl font-bold mb-4">Portfolio</h1>
        <p className="text-zinc-500 mb-8">Login with your API Key to view your portfolio</p>
        
        <div className="flex gap-4">
          <button
            onClick={() => setShowLogin(true)}
            className="bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-6 py-3 rounded-lg font-bold"
          >
            Login with API Key
          </button>
          <Link
            href="/join"
            className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-3 rounded-lg font-bold"
          >
            Register New Agent
          </Link>
        </div>
        
        {/* Login Modal */}
        {showLogin && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#0A0A0A] border border-zinc-800 rounded-xl p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold mb-4">Login</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-2">Agent ID</label>
                  <input
                    type="text"
                    value={loginInput.agentId}
                    onChange={(e) => setLoginInput({ ...loginInput, agentId: e.target.value })}
                    placeholder="agent_0001"
                    className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white font-mono"
                  />
                </div>
                
                <div>
                  <label className="block text-sm text-zinc-400 mb-2">API Key</label>
                  <input
                    type="password"
                    value={loginInput.apiKey}
                    onChange={(e) => setLoginInput({ ...loginInput, apiKey: e.target.value })}
                    placeholder="th_xxxx_..."
                    className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white font-mono"
                  />
                </div>
                
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowLogin(false)}
                    className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleLogin}
                    className="flex-1 bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-2 rounded-lg font-bold"
                  >
                    Login
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Logged in - show portfolio
  const totalPnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const totalValue = (balance?.balance || 0) + totalPnl;

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-8 h-8 text-[#00D4AA]" />
            <h1 className="text-4xl font-bold">Portfolio</h1>
          </div>
          <p className="text-zinc-500">
            Logged in as <span className="text-[#00D4AA] font-mono">{agentId}</span>
            <button onClick={handleLogout} className="ml-4 text-zinc-500 hover:text-white text-sm underline">
              Logout
            </button>
          </p>
        </div>
        
        <div className="flex gap-4">
          <button
            onClick={() => setShowDeposit(true)}
            className="bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-2 rounded-lg font-bold"
          >
            + Deposit
          </button>
          <button
            onClick={() => setShowWithdraw(true)}
            className="bg-[#FF6B35] hover:bg-[#FF8555] text-white px-4 py-2 rounded-lg font-bold"
          >
            − Withdraw
          </button>
          <Link
            href="/trade"
            className="bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold"
          >
            Trade
          </Link>
        </div>
      </header>

      {/* Balance Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 uppercase mb-1">Total Value</div>
          <div className="text-2xl font-bold font-mono font-tabular">{formatPrice(totalValue)}</div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 uppercase mb-1">Available</div>
          <div className="text-2xl font-bold font-mono font-tabular text-[#00D4AA]">{formatPrice(balance?.available || 0)}</div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 uppercase mb-1">In Positions</div>
          <div className="text-2xl font-bold font-mono font-tabular text-[#FF6B35]">{formatPrice(balance?.locked || 0)}</div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <div className="text-xs text-zinc-500 uppercase mb-1">Unrealized PnL</div>
          <div className={`text-2xl font-bold font-mono font-tabular ${totalPnl >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
            {totalPnl >= 0 ? '+' : ''}{formatPrice(totalPnl)}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 inline mr-2" />Open Positions
          <span className="text-sm font-normal text-zinc-500">({positions.filter(p => p.is_open).length})</span>
        </h2>
        
        {positions.filter(p => p.is_open).length === 0 ? (
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-8 text-center text-zinc-500">
            No open positions. <Link href="/trade" className="text-[#00D4AA] underline">Start trading</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {positions.filter(p => p.is_open).map((pos) => (
              <div key={pos.position_id} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl font-bold">{pos.asset}</span>
                      <span className={`text-sm font-bold px-2 py-0.5 rounded ${
                        pos.side === 'long' ? 'bg-[#00D4AA]/20 text-[#00D4AA]' : 'bg-[#FF6B35]/20 text-[#FF6B35]'
                      }`}>
                        {pos.side.toUpperCase()} {pos.leverage}x
                      </span>
                    </div>
                    <div className="text-sm text-zinc-500 mt-1">
                      Size: ${pos.size_usdc} @ {formatPrice(pos.entry_price)}
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className={`text-xl font-bold font-mono ${pos.unrealized_pnl >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
                      {pos.unrealized_pnl >= 0 ? '+' : ''}{formatPrice(Math.abs(pos.unrealized_pnl))}
                    </div>
                    <div className={`text-sm font-mono ${pos.unrealized_pnl >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}`}>
                      {pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center text-sm">
                  <div className="flex gap-4 text-zinc-500">
                    <span>Current: <span className="text-white font-mono">{formatPrice(pos.current_price)}</span></span>
                    <span>Liq: <span className="text-[#FF6B35] font-mono">{formatPrice(pos.liquidation_price)}</span></span>
                  </div>
                  
                  <button
                    onClick={() => handleClosePosition(pos.position_id)}
                    className="bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold text-sm"
                  >
                    Close Position
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Deposit Modal */}
      {showDeposit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#0A0A0A] border border-zinc-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Deposit USDC</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Amount</label>
                <input
                  type="number"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  placeholder="1000"
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white font-mono text-lg"
                />
              </div>
              
              <div className="flex gap-2">
                {[100, 500, 1000, 5000].map(amt => (
                  <button
                    key={amt}
                    onClick={() => setDepositAmount(amt.toString())}
                    className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-2 py-1 rounded text-sm"
                  >
                    ${amt}
                  </button>
                ))}
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowDeposit(false)}
                  className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeposit}
                  disabled={loading || !depositAmount}
                  className="flex-1 bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-2 rounded-lg font-bold disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Deposit'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdraw && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Withdraw Funds</h2>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Amount (USDC)</label>
                <input
                  type="number"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  placeholder="100"
                  max={balance?.available || 0}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2 text-white font-mono text-lg"
                />
              </div>
              
              <div className="text-sm text-zinc-500">
                Available: ${balance?.available.toFixed(2) || '0.00'}
              </div>
              
              <div className="flex gap-2">
                {[25, 50, 75, 100].map(pct => (
                  <button
                    key={pct}
                    onClick={() => setWithdrawAmount(((balance?.available || 0) * pct / 100).toFixed(2))}
                    className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-2 py-1 rounded text-sm"
                  >
                    {pct}%
                  </button>
                ))}
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowWithdraw(false)}
                  className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded-lg font-bold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleWithdraw}
                  disabled={loading || !withdrawAmount || parseFloat(withdrawAmount) > (balance?.available || 0)}
                  className="flex-1 bg-[#FF6B35] hover:bg-[#FF8555] text-white px-4 py-2 rounded-lg font-bold disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Withdraw'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
