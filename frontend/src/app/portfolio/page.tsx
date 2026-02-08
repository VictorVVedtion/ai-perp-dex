'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
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
  const [feedback, setFeedback] = useState<{ success: boolean; message: string } | null>(null);
  const [closePositionTarget, setClosePositionTarget] = useState<Position | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      try {
        const { apiKey, agentId } = JSON.parse(saved);
        setApiKey(apiKey);
        setAgentId(agentId);
      } catch {}
    }
  }, []);

  // Ref to prevent stale setState when agent switches quickly
  const fetchIdRef = useRef(0);
  const feedbackTimerRef = useRef<number | null>(null);

  const showFeedback = useCallback((success: boolean, message: string) => {
    setFeedback({ success, message });
  }, []);

  useEffect(() => {
    if (!feedback) return;
    if (feedbackTimerRef.current) {
      window.clearTimeout(feedbackTimerRef.current);
    }
    feedbackTimerRef.current = window.setTimeout(() => {
      setFeedback(null);
      feedbackTimerRef.current = null;
    }, 4000);

    return () => {
      if (feedbackTimerRef.current) {
        window.clearTimeout(feedbackTimerRef.current);
      }
    };
  }, [feedback]);

  const fetchPortfolio = useCallback(async () => {
    if (!agentId || !apiKey) return;
    const currentFetchId = ++fetchIdRef.current;
    const headers = { 'X-API-Key': apiKey };
    try {
      const [posRes, balRes] = await Promise.all([
        fetch(`${API}/positions/${agentId}`, { headers }),
        fetch(`${API}/balance/${agentId}`, { headers }),
      ]);
      // Only update state if this is still the latest fetch
      if (currentFetchId !== fetchIdRef.current) return;
      if (posRes.ok) {
        const data = await posRes.json();
        setPositions(data.positions || []);
      }
      if (balRes.ok) {
        const data = await balRes.json();
        setBalance(data);
      }
    } catch (e) {
      if (currentFetchId === fetchIdRef.current) {
        console.error(e);
        showFeedback(false, 'Failed to load portfolio data. Please retry.');
      }
    }
  }, [agentId, apiKey, showFeedback]);

  useEffect(() => {
    if (agentId && apiKey) {
      fetchPortfolio();
    }
  }, [agentId, apiKey, fetchPortfolio]);

  const handleLogin = () => {
    if (!loginInput.apiKey || !loginInput.agentId) return;
    
    localStorage.setItem('perp_dex_auth', JSON.stringify({
      apiKey: loginInput.apiKey,
      agentId: loginInput.agentId,
    }));
    
    setApiKey(loginInput.apiKey);
    setAgentId(loginInput.agentId);
    setShowLogin(false);
    showFeedback(true, 'Login successful. Portfolio synced.');
  };

  const handleLogout = () => {
    localStorage.removeItem('perp_dex_auth');
    setApiKey('');
    setAgentId('');
    setPositions([]);
    setBalance(null);
    showFeedback(true, 'Logged out successfully.');
  };

  const handleDeposit = async () => {
    if (!apiKey || !agentId || !depositAmount) return;
    const amount = parseFloat(depositAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      showFeedback(false, 'Please enter a valid deposit amount.');
      return;
    }
    
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
          amount,
        }),
      });
      
      if (res.ok) {
        setShowDeposit(false);
        setDepositAmount('');
        showFeedback(true, `Deposit successful: $${amount.toFixed(2)}`);
        fetchPortfolio();
      } else {
        const err = await res.json();
        showFeedback(false, err.detail || 'Deposit failed');
      }
    } catch (e) {
      console.error(e);
      showFeedback(false, 'Network error while depositing funds.');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!apiKey || !agentId || !withdrawAmount) return;
    const amount = parseFloat(withdrawAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      showFeedback(false, 'Please enter a valid withdrawal amount.');
      return;
    }
    if (amount > (balance?.available || 0)) {
      showFeedback(false, 'Withdrawal exceeds available balance.');
      return;
    }
    
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
          amount,
        }),
      });
      
      if (res.ok) {
        setShowWithdraw(false);
        setWithdrawAmount('');
        showFeedback(true, `Withdrawal submitted: $${amount.toFixed(2)}`);
        fetchPortfolio();
      } else {
        const err = await res.json();
        showFeedback(false, err.detail || 'Withdraw failed');
      }
    } catch (e) {
      console.error(e);
      showFeedback(false, 'Network error while withdrawing funds.');
    } finally {
      setLoading(false);
    }
  };

  const confirmClosePosition = async () => {
    if (!apiKey || !closePositionTarget) return;
    const target = closePositionTarget;
    setClosePositionTarget(null);
    try {
      const res = await fetch(`${API}/positions/${target.position_id}/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });
      
      if (res.ok) {
        showFeedback(true, `${target.asset} position closed.`);
        fetchPortfolio();
      } else {
        const err = await res.json();
        showFeedback(false, err.detail || 'Failed to close position');
      }
    } catch (e) {
      console.error(e);
      showFeedback(false, 'Network error while closing position.');
    }
  };

  // Not logged in
  if (!agentId) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        {feedback && (
          <div className={`fixed top-20 right-6 z-50 px-4 py-3 rounded-lg border text-sm shadow-xl ${
            feedback.success
              ? 'bg-rb-cyan/10 border-rb-cyan/30 text-rb-cyan'
              : 'bg-rb-red/10 border-rb-red/30 text-rb-red'
          }`}>
            {feedback.message}
          </div>
        )}
        <div className="flex justify-center mb-6"><Lock className="w-16 h-16 text-rb-text-secondary" /></div>
        <h1 className="text-3xl font-bold mb-4">Portfolio</h1>
        <p className="text-rb-text-secondary mb-8">Login with your API Key to view your portfolio</p>
        
        <div className="flex gap-4">
          <button
            onClick={() => setShowLogin(true)}
            className="btn-primary btn-lg"
          >
            Login with API Key
          </button>
          <Link
            href="/connect"
            className="btn-secondary-2 btn-lg"
          >
            Register New Agent
          </Link>
        </div>
        
        {/* Login Modal */}
        {showLogin && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold mb-4">Login</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-rb-text-secondary mb-2">Agent ID</label>
                  <input
                    type="text"
                    value={loginInput.agentId}
                    onChange={(e) => setLoginInput({ ...loginInput, agentId: e.target.value })}
                    placeholder="agent_0001"
                    className="w-full input-base input-md font-mono"
                  />
                </div>
                
                <div>
                  <label className="block text-sm text-rb-text-secondary mb-2">API Key</label>
                  <input
                    type="password"
                    value={loginInput.apiKey}
                    onChange={(e) => setLoginInput({ ...loginInput, apiKey: e.target.value })}
                    placeholder="th_xxxx_..."
                    className="w-full input-base input-md font-mono"
                  />
                </div>
                
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowLogin(false)}
                    className="flex-1 btn-secondary-2 btn-md"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleLogin}
                    className="flex-1 btn-primary btn-md"
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
  const totalPnl = positions.filter(p => p.is_open).reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const totalValue = (balance?.balance || 0) + totalPnl;

  return (
    <div className="space-y-8">
      {feedback && (
        <div className={`fixed top-20 right-6 z-50 px-4 py-3 rounded-lg border text-sm shadow-xl ${
          feedback.success
            ? 'bg-rb-cyan/10 border-rb-cyan/30 text-rb-cyan'
            : 'bg-rb-red/10 border-rb-red/30 text-rb-red'
        }`}>
          {feedback.message}
        </div>
      )}

      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-8 h-8 text-rb-cyan" />
            <h1 className="text-4xl font-bold">Portfolio</h1>
          </div>
          <p className="text-rb-text-secondary">
            Logged in as <span className="text-rb-cyan font-mono">{agentId}</span>
            <button onClick={handleLogout} className="ml-4 text-rb-text-secondary hover:text-rb-text-main text-sm underline">
              Logout
            </button>
          </p>
        </div>
        
        <div className="flex gap-4">
          <button
            onClick={() => setShowDeposit(true)}
            className="btn-primary btn-md"
          >
            + Deposit
          </button>
          <button
            onClick={() => setShowWithdraw(true)}
            className="bg-rb-red hover:bg-rb-red/90 text-rb-text-main px-4 py-2 rounded-lg font-bold transition-colors"
          >
            − Withdraw
          </button>
          <Link
            href="/trade"
            className="btn-secondary-2 btn-md"
          >
            Trade
          </Link>
        </div>
      </header>

      {/* Balance Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-4">
          <div className="text-xs text-rb-text-secondary uppercase mb-1">Total Value</div>
          <div className="text-2xl font-bold font-mono font-tabular">{formatPrice(totalValue)}</div>
        </div>
        <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-4">
          <div className="text-xs text-rb-text-secondary uppercase mb-1">Available</div>
          <div className="text-2xl font-bold font-mono font-tabular text-rb-cyan">{formatPrice(balance?.available || 0)}</div>
        </div>
        <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-4">
          <div className="text-xs text-rb-text-secondary uppercase mb-1">In Positions</div>
          <div className="text-2xl font-bold font-mono font-tabular text-rb-red">{formatPrice(balance?.locked || 0)}</div>
        </div>
        <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-4">
          <div className="text-xs text-rb-text-secondary uppercase mb-1">Unrealized PnL</div>
          <div className={`text-2xl font-bold font-mono font-tabular ${totalPnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
            {totalPnl >= 0 ? '+' : ''}{formatPrice(totalPnl)}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 inline mr-2" />Open Positions
          <span className="text-sm font-normal text-rb-text-secondary">({positions.filter(p => p.is_open).length})</span>
        </h2>
        
        {positions.filter(p => p.is_open).length === 0 ? (
          <div className="bg-layer-1/50 border border-layer-3 rounded-xl p-8 text-center text-rb-text-secondary">
            No open positions. <Link href="/trade" className="text-rb-cyan underline">Start trading</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {positions.filter(p => p.is_open).map((pos) => (
              <div key={pos.position_id} className="bg-layer-1/50 border border-layer-3 rounded-xl p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl font-bold">{pos.asset}</span>
                      <span className={`text-sm font-bold px-2 py-0.5 rounded ${
                        pos.side === 'long' ? 'bg-rb-cyan/20 text-rb-cyan' : 'bg-rb-red/20 text-rb-red'
                      }`}>
                        {pos.side.toUpperCase()} {pos.leverage}x
                      </span>
                    </div>
                    <div className="text-sm text-rb-text-secondary mt-1">
                      Size: ${pos.size_usdc} @ {formatPrice(pos.entry_price)}
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className={`text-xl font-bold font-mono ${pos.unrealized_pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                      {pos.unrealized_pnl >= 0 ? '+' : ''}{formatPrice(Math.abs(pos.unrealized_pnl))}
                    </div>
                    <div className={`text-sm font-mono ${pos.unrealized_pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                      {pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center text-sm">
                  <div className="flex gap-4 text-rb-text-secondary">
                    <span>Current: <span className="text-rb-text-main font-mono">{formatPrice(pos.current_price)}</span></span>
                    <span>Liq: <span className="text-rb-red font-mono">{formatPrice(pos.liquidation_price)}</span></span>
                  </div>
                  
                  <button
                    onClick={() => setClosePositionTarget(pos)}
                    className="btn-secondary-2 btn-md"
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
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Deposit USDC</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Amount</label>
                <input
                  type="number"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  placeholder="1000"
                  className="w-full input-base input-lg font-mono"
                />
              </div>
              
              <div className="flex gap-2">
                {[100, 500, 1000, 5000].map(amt => (
                  <button
                    key={amt}
                    onClick={() => setDepositAmount(amt.toString())}
                    className="flex-1 bg-layer-2 hover:bg-layer-3 text-rb-text-main px-2 py-1 rounded text-sm border border-layer-3 transition-colors"
                  >
                    ${amt}
                  </button>
                ))}
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowDeposit(false)}
                  className="flex-1 btn-secondary-2 btn-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeposit}
                  disabled={loading || !depositAmount}
                  className="flex-1 btn-primary btn-md"
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
          <div className="bg-layer-1 border border-layer-3 rounded-2xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Withdraw Funds</h2>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-rb-text-secondary block mb-1">Amount (USDC)</label>
                <input
                  type="number"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  placeholder="100"
                  max={balance?.available || 0}
                  className="w-full input-base input-lg font-mono"
                />
              </div>
              
              <div className="text-sm text-rb-text-secondary">
                Available: ${balance?.available.toFixed(2) || '0.00'}
              </div>
              
              <div className="flex gap-2">
                {[25, 50, 75, 100].map(pct => (
                  <button
                    key={pct}
                    onClick={() => setWithdrawAmount(((balance?.available || 0) * pct / 100).toFixed(2))}
                    className="flex-1 bg-layer-2 hover:bg-layer-3 text-rb-text-main px-2 py-1 rounded text-sm border border-layer-3 transition-colors"
                  >
                    {pct}%
                  </button>
                ))}
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowWithdraw(false)}
                  className="flex-1 btn-secondary-2 btn-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleWithdraw}
                  disabled={loading || !withdrawAmount || parseFloat(withdrawAmount) > (balance?.available || 0)}
                  className="flex-1 bg-rb-red hover:bg-rb-red/90 text-rb-text-main px-4 py-2 rounded-lg font-bold disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Processing...' : 'Withdraw'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Close Position Confirm Modal */}
      {closePositionTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-2">Confirm Close</h3>
            <p className="text-rb-text-secondary text-sm mb-6">
              Close <span className="text-rb-text-main font-mono">{closePositionTarget.asset}</span> position now?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setClosePositionTarget(null)}
                className="flex-1 btn-secondary-2 btn-md"
              >
                Cancel
              </button>
              <button
                onClick={confirmClosePosition}
                className="flex-1 btn-danger-outline btn-md"
              >
                Close Position
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
