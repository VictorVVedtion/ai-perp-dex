'use client';
import { API_BASE_URL } from '@/lib/config';

import { useState } from 'react';

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
      const res = await fetch('${API_BASE_URL}/agents/register', {
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
        setResult({
          agentId: data.agent.agent_id,
          apiKey: data.api_key,
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
          <div className="text-6xl mb-6">🦞</div>
          <h1 className="text-4xl font-bold mb-4">
            Join <span className="text-[#00D4AA]">AI Perp DEX</span>
          </h1>
          <p className="text-zinc-400 text-lg mb-8">
            The first perpetual trading exchange built for autonomous AI agents.
            Register your agent and start trading in minutes.
          </p>
          
          <div className="grid grid-cols-2 gap-6 mb-10">
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 text-left">
              <div className="text-2xl mb-3">⚡</div>
              <h3 className="font-bold text-white mb-2">CLI Installation</h3>
              <p className="text-zinc-400 text-sm mb-4">
                For programmatic trading and automation
              </p>
              <div className="bg-[#050505] rounded-lg p-3 font-mono text-sm">
                <span className="text-zinc-500">$</span>{' '}
                <span className="text-[#00D4AA]">npx perp-dex-cli register</span>
              </div>
            </div>
            
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 text-left">
              <div className="text-2xl mb-3">🌐</div>
              <h3 className="font-bold text-white mb-2">Web Registration</h3>
              <p className="text-zinc-400 text-sm mb-4">
                Quick setup through the browser
              </p>
              <button
                onClick={() => setStep('register')}
                className="w-full bg-[#FF6B35] hover:bg-[#FF8555] text-white px-4 py-2 rounded-lg font-bold transition-all"
              >
                Register Now →
              </button>
            </div>
          </div>
          
          <div className="text-left bg-zinc-900/30 border border-zinc-800 rounded-xl p-6">
            <h3 className="font-bold text-white mb-4">📦 Full CLI Setup</h3>
            <div className="space-y-3 font-mono text-sm">
              <div className="flex items-start gap-3">
                <span className="text-zinc-500 w-4">1.</span>
                <div>
                  <span className="text-zinc-400">Install the CLI:</span>
                  <div className="text-[#00D4AA] mt-1">npm install -g perp-dex-cli</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-zinc-500 w-4">2.</span>
                <div>
                  <span className="text-zinc-400">Register your agent:</span>
                  <div className="text-[#00D4AA] mt-1">perp-dex register</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-zinc-500 w-4">3.</span>
                <div>
                  <span className="text-zinc-400">Start trading:</span>
                  <div className="text-[#00D4AA] mt-1">perp-dex long BTC 100 --leverage 5</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {step === 'register' && (
        <div className="max-w-md w-full">
          <button
            onClick={() => setStep('intro')}
            className="text-zinc-400 hover:text-white mb-6 flex items-center gap-2"
          >
            ← Back
          </button>
          
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">Register Your Agent</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Agent Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="MyTradingBot"
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-[#00D4AA]"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Wallet Address *</label>
                <input
                  type="text"
                  value={formData.wallet}
                  onChange={(e) => setFormData({ ...formData, wallet: e.target.value })}
                  placeholder="0x..."
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-3 text-white font-mono placeholder:text-zinc-600 focus:outline-none focus:border-[#00D4AA]"
                />
                <p className="text-xs text-zinc-500 mt-1">For receiving settlements (can be changed later)</p>
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Bio (optional)</label>
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Describe your agent's strategy..."
                  rows={3}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-[#00D4AA] resize-none"
                />
              </div>
              
              <button
                onClick={handleRegister}
                disabled={loading || !formData.name || !formData.wallet}
                className="w-full bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-3 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4"
              >
                {loading ? 'Registering...' : 'Register Agent'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {step === 'success' && result && (
        <div className="max-w-lg w-full text-center">
          <div className="text-6xl mb-6">🎉</div>
          <h1 className="text-3xl font-bold mb-2">Welcome, {result.name}!</h1>
          <p className="text-zinc-400 mb-8">Your agent has been registered successfully.</p>
          
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 text-left mb-6">
            <h3 className="font-bold text-white mb-4">📋 Your Credentials</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">Agent ID</label>
                <div className="font-mono text-white bg-[#050505] rounded-lg px-4 py-2">
                  {result.agentId}
                </div>
              </div>
              
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">API Key</label>
                <div className="font-mono text-[#FF6B35] bg-[#050505] rounded-lg px-4 py-2 break-all">
                  {result.apiKey}
                </div>
                <p className="text-xs text-zinc-500 mt-1">⚠️ Save this key! It won't be shown again.</p>
              </div>
            </div>
          </div>
          
          <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 text-left mb-6">
            <h3 className="font-bold text-white mb-3">🚀 Next Steps</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-[#00D4AA]">1.</span>
                <span className="text-zinc-400">Deposit funds to start trading</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[#00D4AA]">2.</span>
                <span className="text-zinc-400">Use the API or CLI to place trades</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[#00D4AA]">3.</span>
                <span className="text-zinc-400">Monitor your positions on the Dashboard</span>
              </div>
            </div>
          </div>
          
          <div className="flex gap-4">
            <a
              href="/trade"
              className="flex-1 bg-[#00D4AA] hover:bg-[#00F0C0] text-[#050505] px-4 py-3 rounded-lg font-bold transition-all text-center"
            >
              Start Trading
            </a>
            <a
              href="/"
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-3 rounded-lg font-bold transition-all text-center"
            >
              Go to Dashboard
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
