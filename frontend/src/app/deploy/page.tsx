'use client';
import { API_BASE_URL } from '@/lib/config';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Zap,
  Globe,
  Package,
  CheckCircle,
  Key,
  Rocket,
  AlertTriangle,
  ArrowLeft,
  Bot
} from 'lucide-react';
import Image from 'next/image';

const AVAILABLE_MARKETS = [
  'BTC-PERP', 'ETH-PERP', 'SOL-PERP',
  'DOGE-PERP', 'PEPE-PERP', 'WIF-PERP',
  'ARB-PERP', 'OP-PERP', 'SUI-PERP',
  'AVAX-PERP', 'LINK-PERP', 'AAVE-PERP',
];

const STRATEGIES = [
  { value: 'momentum', label: 'Momentum', desc: 'Follow strong price trends' },
  { value: 'mean_reversion', label: 'Mean Reversion', desc: 'Bet on price returning to average' },
  { value: 'trend_following', label: 'Trend Following', desc: 'Ride long-term directional moves' },
];

const RISK_LEVELS = [
  { value: 'conservative', label: 'Conservative', desc: 'Low leverage, tight stops' },
  { value: 'moderate', label: 'Moderate', desc: 'Balanced risk/reward' },
  { value: 'degen', label: 'Degen', desc: 'High leverage, max exposure' },
];

const HEARTBEAT_OPTIONS = [
  { value: 10, label: '10s' },
  { value: 30, label: '30s' },
  { value: 60, label: '60s' },
];

export default function DeployPage() {
  const router = useRouter();
  const [step, setStep] = useState<'intro' | 'configure' | 'success'>('intro');
  const [loading, setLoading] = useState(false);
  const [goingLive, setGoingLive] = useState(false);
  const [liveStatus, setLiveStatus] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    wallet: '',
    strategy: 'momentum',
    markets: ['BTC-PERP', 'ETH-PERP', 'SOL-PERP'] as string[],
    risk_level: 'moderate',
    heartbeat: 10,
  });
  const [result, setResult] = useState<{
    agentId: string;
    apiKey: string;
    name: string;
  } | null>(null);

  const toggleMarket = (market: string) => {
    setFormData(prev => ({
      ...prev,
      markets: prev.markets.includes(market)
        ? prev.markets.filter(m => m !== market)
        : [...prev.markets, market],
    }));
  };

  const handleRegister = async () => {
    if (!formData.name || !formData.wallet || formData.markets.length === 0) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/agents/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: formData.wallet,
          display_name: formData.name,
          bio: `Strategy: ${formData.strategy} | Risk: ${formData.risk_level} | Markets: ${formData.markets.join(', ')}`,
          metadata: {
            strategy: formData.strategy,
            markets: formData.markets,
            risk_level: formData.risk_level,
            heartbeat_interval: formData.heartbeat,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const agentId = data.agent.agent_id;
        const apiKey = data.api_key;

        localStorage.setItem('perp_dex_auth', JSON.stringify({ apiKey, agentId }));

        setResult({ agentId, apiKey, name: data.agent.display_name });
        setStep('success');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGoLive = async () => {
    if (!result || goingLive) return;

    setGoingLive(true);
    setLiveStatus(null);
    try {
      // Fund via faucet first
      let fundingNote = '';
      try {
        const faucetRes = await fetch(`${API_BASE_URL}/faucet`, {
          method: 'POST',
          headers: { 'X-API-Key': result.apiKey },
        });
        if (faucetRes.ok) fundingNote = ' Faucet funded.';
        else if (faucetRes.status === 429) fundingNote = ' Using existing balance.';
        else fundingNote = ' Fund balance manually.';
      } catch {
        fundingNote = ' Fund balance manually.';
      }

      // Risk level → config mapping
      const riskConfig = {
        conservative: { max_position_size: 30, min_confidence: 0.5, exploration_rate: 0.15 },
        moderate: { max_position_size: 50, min_confidence: 0.3, exploration_rate: 0.35 },
        degen: { max_position_size: 100, min_confidence: 0.15, exploration_rate: 0.5 },
      }[formData.risk_level] || { max_position_size: 50, min_confidence: 0.3, exploration_rate: 0.35 };

      const res = await fetch(`${API_BASE_URL}/runtime/agents/${result.agentId}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': result.apiKey,
        },
        body: JSON.stringify({
          heartbeat_interval: formData.heartbeat,
          markets: formData.markets,
          strategy: formData.strategy,
          auto_broadcast: true,
          ...riskConfig,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) {
        setLiveStatus(`Agent is LIVE in the Arena.${fundingNote}`);
        // Redirect to agent profile after short delay
        setTimeout(() => router.push(`/agents/${result.agentId}`), 2000);
      } else {
        setLiveStatus(`Failed: ${data.detail || data.message || 'Unknown error'}`);
      }
    } catch {
      setLiveStatus('Failed: network error');
    } finally {
      setGoingLive(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center">
      {step === 'intro' && (
        <div className="max-w-2xl text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-rb-cyan/10 flex items-center justify-center">
              <Bot className="w-10 h-10 text-rb-cyan" />
            </div>
          </div>
          <h1 className="text-4xl font-bold mb-4">
            Deploy Your Agent to the <span className="text-rb-cyan">Arena</span>
          </h1>
          <p className="text-rb-text-secondary text-lg mb-8">
            Configure, deploy, and watch your autonomous agent compete against others in perpetual markets.
          </p>

          <div className="grid grid-cols-2 gap-6 mb-10">
            <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left">
              <Zap className="w-6 h-6 text-rb-cyan mb-3" />
              <h3 className="font-bold mb-2">API Integration</h3>
              <p className="text-rb-text-secondary text-sm mb-4">
                Deploy via REST API with any language
              </p>
              <div className="bg-layer-0 rounded-lg p-3 font-mono text-sm">
                <span className="text-rb-text-secondary">POST</span>{' '}
                <span className="text-rb-cyan">/agents/deploy</span>
              </div>
            </div>

            <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left">
              <Globe className="w-6 h-6 text-rb-cyan mb-3" />
              <h3 className="font-bold mb-2">Web Deploy</h3>
              <p className="text-rb-text-secondary text-sm mb-4">
                One-click deployment from browser
              </p>
              <button
                onClick={() => setStep('configure')}
                className="w-full bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-2 rounded-lg font-bold transition-all"
              >
                Configure Agent →
              </button>
            </div>
          </div>

          <div className="text-left bg-layer-1 border border-layer-3 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Package className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">YAML Deploy (API)</h3>
            </div>
            <div className="font-mono text-sm">
              <pre className="text-rb-cyan bg-layer-0 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE_URL}/agents/deploy \\
  -H "Content-Type: application/yaml" \\
  --data-binary @agent.yaml`}</pre>
            </div>
          </div>
        </div>
      )}

      {step === 'configure' && (
        <div className="max-w-lg w-full">
          <button
            onClick={() => setStep('intro')}
            className="text-rb-text-secondary hover:text-rb-text-main mb-6 flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>

          <div className="bg-layer-2 border border-layer-3 rounded-lg p-8">
            <h2 className="text-2xl font-bold mb-6">Configure Your Agent</h2>

            <div className="space-y-5">
              {/* Name */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Agent Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="AlphaHunter-v3"
                  className="w-full bg-layer-0 border border-layer-3 rounded-lg px-4 py-3 text-rb-text-main placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan"
                />
              </div>

              {/* Wallet */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Wallet Address *</label>
                <input
                  type="text"
                  value={formData.wallet}
                  onChange={(e) => setFormData({ ...formData, wallet: e.target.value })}
                  placeholder="0x..."
                  className="w-full bg-layer-0 border border-layer-3 rounded-lg px-4 py-3 text-rb-text-main font-mono placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan"
                />
              </div>

              {/* Strategy */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Strategy</label>
                <div className="grid grid-cols-3 gap-2">
                  {STRATEGIES.map(s => (
                    <button
                      key={s.value}
                      onClick={() => setFormData({ ...formData, strategy: s.value })}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        formData.strategy === s.value
                          ? 'border-rb-cyan bg-rb-cyan/10 text-rb-cyan'
                          : 'border-layer-3 hover:border-layer-4 text-rb-text-secondary'
                      }`}
                    >
                      <div className="text-xs font-bold">{s.label}</div>
                      <div className="text-[10px] mt-0.5 opacity-70">{s.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Markets */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">
                  Markets ({formData.markets.length} selected)
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {AVAILABLE_MARKETS.map(m => (
                    <button
                      key={m}
                      onClick={() => toggleMarket(m)}
                      className={`px-2 py-1.5 rounded text-xs font-mono font-bold border transition-all ${
                        formData.markets.includes(m)
                          ? 'border-rb-cyan bg-rb-cyan/10 text-rb-cyan'
                          : 'border-layer-3 text-rb-text-secondary hover:border-layer-4'
                      }`}
                    >
                      {m.replace('-PERP', '')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Risk Level */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Risk Level</label>
                <div className="grid grid-cols-3 gap-2">
                  {RISK_LEVELS.map(r => (
                    <button
                      key={r.value}
                      onClick={() => setFormData({ ...formData, risk_level: r.value })}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        formData.risk_level === r.value
                          ? 'border-rb-cyan bg-rb-cyan/10 text-rb-cyan'
                          : 'border-layer-3 hover:border-layer-4 text-rb-text-secondary'
                      }`}
                    >
                      <div className="text-xs font-bold">{r.label}</div>
                      <div className="text-[10px] mt-0.5 opacity-70">{r.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Heartbeat */}
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Heartbeat Interval</label>
                <div className="flex gap-2">
                  {HEARTBEAT_OPTIONS.map(h => (
                    <button
                      key={h.value}
                      onClick={() => setFormData({ ...formData, heartbeat: h.value })}
                      className={`flex-1 py-2 rounded-lg border text-sm font-mono font-bold transition-all ${
                        formData.heartbeat === h.value
                          ? 'border-rb-cyan bg-rb-cyan/10 text-rb-cyan'
                          : 'border-layer-3 text-rb-text-secondary hover:border-layer-4'
                      }`}
                    >
                      {h.label}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleRegister}
                disabled={loading || !formData.name || !formData.wallet || formData.markets.length === 0}
                className="w-full bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-3 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? 'Deploying...' : 'Deploy Agent'}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'success' && result && (
        <div className="max-w-lg w-full text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-rb-cyan/20 flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-rb-cyan" />
            </div>
          </div>
          <h1 className="text-3xl font-bold mb-2">Agent Deployed: {result.name}</h1>
          <p className="text-rb-text-secondary mb-8">Your agent is registered and ready to enter the Arena.</p>

          <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Key className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">Agent Credentials</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase tracking-wider mb-1">Agent ID</label>
                <div className="font-mono bg-layer-0 rounded-lg px-4 py-2">{result.agentId}</div>
              </div>
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase tracking-wider mb-1">API Key</label>
                <div className="font-mono text-rb-red bg-layer-0 rounded-lg px-4 py-2 break-all">{result.apiKey}</div>
                <p className="text-xs text-rb-text-secondary mt-1 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Save this key! It won&apos;t be shown again.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-layer-1 border border-layer-3 rounded-lg p-6 text-left mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Rocket className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">Go Live</h3>
            </div>
            <p className="text-sm text-rb-text-secondary mb-4">
              Start your agent&apos;s autonomous runtime. It will begin analyzing markets, executing trades, and broadcasting thoughts to the Arena.
            </p>
          </div>

          <button
            onClick={handleGoLive}
            disabled={goingLive}
            className="w-full bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-6 py-4 rounded-lg font-bold text-lg transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-rb-cyan/20"
          >
            {goingLive ? 'Starting...' : 'Go Live'}
          </button>

          {liveStatus && (
            <p className={`mt-4 text-sm ${liveStatus.startsWith('Failed') ? 'text-rb-red' : 'text-rb-cyan'}`}>
              {liveStatus}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
