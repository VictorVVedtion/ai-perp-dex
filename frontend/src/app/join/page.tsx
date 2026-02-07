'use client';
import { API_BASE_URL } from '@/lib/config';

import { useState } from 'react';
import {
  Zap,
  Globe,
  Package,
  CheckCircle,
  Key,
  Rocket,
  AlertTriangle,
  ArrowLeft
} from 'lucide-react';
import Image from 'next/image';

export default function JoinPage() {
  const [step, setStep] = useState<'intro' | 'register' | 'success'>('intro');
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    wallet: '',
    bio: '',
  });
  const [result, setResult] = useState<{
    agentId: string;
    apiKey: string;
    name: string;
  } | null>(null);

  const handleRegister = async () => {
    if (!formData.name || !formData.wallet) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/agents/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: formData.wallet,
          display_name: formData.name,
          bio: formData.bio || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const agentId = data.agent.agent_id;
        const apiKey = data.api_key;

        // Auto-save credentials to localStorage for Portfolio page
        localStorage.setItem('perp_dex_auth', JSON.stringify({
          apiKey,
          agentId,
        }));

        setResult({
          agentId,
          apiKey,
          name: data.agent.display_name,
        });
        setStep('success');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center">
      {step === 'intro' && (
        <div className="max-w-2xl text-center">
          <div className="flex justify-center mb-6">
            <Image src="/logo-icon.svg" alt="Riverbit" width={64} height={64} />
          </div>
          <h1 className="text-4xl font-bold mb-4">
            Join <span className="text-rb-cyan">Riverbit</span>
          </h1>
          <p className="text-rb-text-secondary text-lg mb-8">
            The first perpetual trading exchange built for autonomous AI agents.
            Register your agent and start trading in minutes.
          </p>

          <div className="grid grid-cols-2 gap-6 mb-10">
            <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left">
              <Zap className="w-6 h-6 text-rb-cyan mb-3" />
              <h3 className="font-bold mb-2">API Integration</h3>
              <p className="text-rb-text-secondary text-sm mb-4">
                通过 REST API 接入，支持任意语言
              </p>
              <div className="bg-layer-0 rounded-lg p-3 font-mono text-sm">
                <span className="text-rb-text-secondary">POST</span>{' '}
                <span className="text-rb-cyan">/agents/register</span>
              </div>
            </div>

            <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left">
              <Globe className="w-6 h-6 text-rb-cyan mb-3" />
              <h3 className="font-bold mb-2">Web Registration</h3>
              <p className="text-rb-text-secondary text-sm mb-4">
                浏览器一键注册，无需安装
              </p>
              <button
                onClick={() => setStep('register')}
                className="w-full bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-2 rounded-lg font-bold transition-all"
              >
                Register Now →
              </button>
            </div>
          </div>

          <div className="text-left bg-layer-1 border border-layer-3 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Package className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">API Quick Start</h3>
            </div>
            <div className="space-y-4 font-mono text-sm">
              <div>
                <span className="text-rb-text-secondary">1. 注册 Agent:</span>
                <pre className="text-rb-cyan mt-1 bg-layer-0 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE_URL}/agents/register \\
  -H "Content-Type: application/json" \\
  -d '{"name":"MyBot","wallet_address":"0x..."}'`}</pre>
              </div>
              <div>
                <span className="text-rb-text-secondary">2. 充值 USDC:</span>
                <pre className="text-rb-cyan mt-1 bg-layer-0 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE_URL}/deposit \\
  -H "X-API-Key: YOUR_KEY" \\
  -d '{"agent_id":"...","amount":1000}'`}</pre>
              </div>
              <div>
                <span className="text-rb-text-secondary">3. 开仓交易:</span>
                <pre className="text-rb-cyan mt-1 bg-layer-0 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE_URL}/intents \\
  -H "X-API-Key: YOUR_KEY" \\
  -d '{"agent_id":"...","intent_type":"long","asset":"BTC-PERP","size_usdc":100,"leverage":5}'`}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {step === 'register' && (
        <div className="max-w-md w-full">
          <button
            onClick={() => setStep('intro')}
            className="text-rb-text-secondary hover:text-rb-text-main mb-6 flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>

          <div className="bg-layer-2 border border-layer-3 rounded-lg p-8">
            <h2 className="text-2xl font-bold mb-6">Register Your Agent</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Agent Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="MyTradingBot"
                  className="w-full bg-layer-0 border border-layer-3 rounded-lg px-4 py-3 text-rb-text-main placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan"
                />
              </div>

              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Wallet Address *</label>
                <input
                  type="text"
                  value={formData.wallet}
                  onChange={(e) => setFormData({ ...formData, wallet: e.target.value })}
                  placeholder="0x..."
                  className="w-full bg-layer-0 border border-layer-3 rounded-lg px-4 py-3 text-rb-text-main font-mono placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan"
                />
                <p className="text-xs text-rb-text-secondary mt-1">For receiving settlements (can be changed later)</p>
              </div>

              <div>
                <label className="block text-sm text-rb-text-secondary mb-2">Bio (optional)</label>
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Describe your agent's strategy..."
                  rows={3}
                  className="w-full bg-layer-0 border border-layer-3 rounded-lg px-4 py-3 text-rb-text-main placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan resize-none"
                />
              </div>

              <button
                onClick={handleRegister}
                disabled={loading || !formData.name || !formData.wallet}
                className="w-full bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-3 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4"
              >
                {loading ? 'Registering...' : 'Register Agent'}
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
          <h1 className="text-3xl font-bold mb-2">Welcome, {result.name}!</h1>
          <p className="text-rb-text-secondary mb-8">Your agent has been registered successfully.</p>

          <div className="bg-layer-2 border border-layer-3 rounded-lg p-6 text-left mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Key className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">Your Credentials</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase tracking-wider mb-1">Agent ID</label>
                <div className="font-mono bg-layer-0 rounded-lg px-4 py-2">
                  {result.agentId}
                </div>
              </div>

              <div>
                <label className="block text-xs text-rb-text-secondary uppercase tracking-wider mb-1">API Key</label>
                <div className="font-mono text-rb-red bg-layer-0 rounded-lg px-4 py-2 break-all">
                  {result.apiKey}
                </div>
                <p className="text-xs text-rb-text-secondary mt-1 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Save this key! It won't be shown again.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-layer-1 border border-layer-3 rounded-lg p-6 text-left mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Rocket className="w-5 h-5 text-rb-cyan" />
              <h3 className="font-bold">Next Steps</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-rb-cyan">1.</span>
                <span className="text-rb-text-secondary">Deposit funds to start trading</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rb-cyan">2.</span>
                <span className="text-rb-text-secondary">Use the API or CLI to place trades</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rb-cyan">3.</span>
                <span className="text-rb-text-secondary">Monitor your positions on the Dashboard</span>
              </div>
            </div>
          </div>

          <div className="flex gap-4">
            <a
              href="/trade"
              className="flex-1 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-3 rounded-lg font-bold transition-all text-center"
            >
              Start Trading
            </a>
            <a
              href="/"
              className="flex-1 bg-layer-4 hover:bg-layer-4/80 text-rb-text-main px-4 py-3 rounded-lg font-bold transition-all text-center"
            >
              Go to Dashboard
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
