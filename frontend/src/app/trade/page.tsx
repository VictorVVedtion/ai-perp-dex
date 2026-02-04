'use client';

import { useState, useMemo } from 'react';

const MARKETS = [
  { symbol: 'BTC-PERP', price: 84000 },
  { symbol: 'ETH-PERP', price: 2200 },
  { symbol: 'SOL-PERP', price: 130 },
];

export default function TradePage() {
  const [market, setMarket] = useState('BTC-PERP');
  const [side, setSide] = useState<'LONG' | 'SHORT'>('LONG');
  const [sizeUsdc, setSizeUsdc] = useState('');
  const [leverage, setLeverage] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const selectedMarket = MARKETS.find(m => m.symbol === market)!;
  
  const estimatedMargin = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size / leverage;
  }, [sizeUsdc, leverage]);

  const positionSize = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size / selectedMarket.price;
  }, [sizeUsdc, selectedMarket.price]);

  const handleSubmit = async () => {
    if (!sizeUsdc || parseFloat(sizeUsdc) <= 0) {
      setResult({ success: false, message: 'Please enter a valid size' });
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8080/trade/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: 'web_user',
          market,
          side: side.toLowerCase(),
          size_usdc: parseFloat(sizeUsdc),
          leverage,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult({ success: true, message: `Trade request submitted! ID: ${data.request_id || data.id || 'created'}` });
        setSizeUsdc('');
      } else {
        const error = await response.text();
        setResult({ success: false, message: `Failed: ${error}` });
      }
    } catch (err) {
      setResult({ success: false, message: 'Network error - is the backend running?' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center py-6">
        <h1 className="text-3xl font-bold mb-2">⚡ Trade</h1>
        <p className="text-zinc-500">Open a perpetual position</p>
      </div>

      {/* Trading Card */}
      <div className="glass-card p-6 space-y-6">
        {/* Market Selection */}
        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Market</label>
          <div className="grid grid-cols-3 gap-2">
            {MARKETS.map(m => (
              <button
                key={m.symbol}
                onClick={() => setMarket(m.symbol)}
                className={`p-3 rounded-xl border transition-all ${
                  market === m.symbol
                    ? 'bg-white/10 border-white/30 text-white'
                    : 'border-white/10 text-zinc-400 hover:bg-white/5'
                }`}
              >
                <div className="font-semibold text-sm">{m.symbol.replace('-PERP', '')}</div>
                <div className="text-xs opacity-60">${m.price.toLocaleString()}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Side Selection */}
        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Direction</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setSide('LONG')}
              className={`p-4 rounded-xl border transition-all font-semibold ${
                side === 'LONG'
                  ? 'bg-green-500/20 border-green-500/50 text-green-400'
                  : 'border-white/10 text-zinc-400 hover:bg-white/5'
              }`}
            >
              📈 Long
            </button>
            <button
              onClick={() => setSide('SHORT')}
              className={`p-4 rounded-xl border transition-all font-semibold ${
                side === 'SHORT'
                  ? 'bg-red-500/20 border-red-500/50 text-red-400'
                  : 'border-white/10 text-zinc-400 hover:bg-white/5'
              }`}
            >
              📉 Short
            </button>
          </div>
        </div>

        {/* Size Input */}
        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Size (USDC)</label>
          <div className="relative">
            <input
              type="number"
              value={sizeUsdc}
              onChange={e => setSizeUsdc(e.target.value)}
              placeholder="0.00"
              className="w-full p-4 rounded-xl bg-white/5 border border-white/10 text-white text-xl font-mono placeholder:text-zinc-600 focus:outline-none focus:border-white/30"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500">USDC</span>
          </div>
          <div className="flex gap-2">
            {[100, 500, 1000, 2000].map(v => (
              <button
                key={v}
                onClick={() => setSizeUsdc(String(v))}
                className="flex-1 py-2 text-sm rounded-lg bg-white/5 border border-white/10 text-zinc-400 hover:bg-white/10 transition"
              >
                ${v}
              </button>
            ))}
          </div>
        </div>

        {/* Leverage Slider */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <label className="text-sm text-zinc-400">Leverage</label>
            <span className="text-sm font-bold text-white">{leverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            value={leverage}
            onChange={e => setLeverage(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none bg-white/10 cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow-lg"
          />
          <div className="flex justify-between text-xs text-zinc-500">
            <span>1x</span>
            <span>5x</span>
            <span>10x</span>
            <span>15x</span>
            <span>20x</span>
          </div>
        </div>

        {/* Summary */}
        <div className="glass-card p-4 space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Position Size</span>
            <span className="font-mono">
              {positionSize.toFixed(6)} {market.replace('-PERP', '')}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Notional Value</span>
            <span className="font-mono">${parseFloat(sizeUsdc || '0').toLocaleString()} USDC</span>
          </div>
          <div className="border-t border-white/10 pt-3 flex justify-between">
            <span className="text-zinc-400">Required Margin</span>
            <span className="font-bold text-lg">${estimatedMargin.toFixed(2)} USDC</span>
          </div>
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={loading || !sizeUsdc}
          className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
            side === 'LONG'
              ? 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-400 hover:to-emerald-400'
              : 'bg-gradient-to-r from-red-500 to-orange-500 hover:from-red-400 hover:to-orange-400'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading ? (
            <span className="animate-pulse">Submitting...</span>
          ) : (
            `${side === 'LONG' ? '📈 Open Long' : '📉 Open Short'} ${market.replace('-PERP', '')}`
          )}
        </button>

        {/* Result Message */}
        {result && (
          <div className={`p-4 rounded-xl text-sm ${
            result.success 
              ? 'bg-green-500/20 border border-green-500/30 text-green-400' 
              : 'bg-red-500/20 border border-red-500/30 text-red-400'
          }`}>
            {result.success ? '✅' : '❌'} {result.message}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="text-center text-xs text-zinc-600">
        Trades are matched peer-to-peer with AI agents
      </div>
    </div>
  );
}
