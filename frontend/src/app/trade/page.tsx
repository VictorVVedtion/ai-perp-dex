'use client';

import { useState, useMemo, useEffect } from 'react';

const MARKETS = [
  { symbol: 'BTC-PERP', price: 84000, icon: '₿' },
  { symbol: 'ETH-PERP', price: 2200, icon: 'Ξ' },
  { symbol: 'SOL-PERP', price: 130, icon: '◎' },
];

export default function TradePage() {
  const [market, setMarket] = useState('BTC-PERP');
  const [side, setSide] = useState<'LONG' | 'SHORT'>('LONG');
  const [sizeUsdc, setSizeUsdc] = useState('');
  const [leverage, setLeverage] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [balance, setBalance] = useState(10000); // Mock balance

  const selectedMarket = MARKETS.find(m => m.symbol === market)!;
  
  const estimatedMargin = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size / leverage;
  }, [sizeUsdc, leverage]);

  const positionSize = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size / selectedMarket.price;
  }, [sizeUsdc, selectedMarket.price]);

  const liquidationPrice = useMemo(() => {
    const price = selectedMarket.price;
    if (side === 'LONG') {
      return price * (1 - 0.9 / leverage);
    } else {
      return price * (1 + 0.9 / leverage);
    }
  }, [selectedMarket.price, leverage, side]);

  const estimatedFee = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size * 0.0005; // 0.05%
  }, [sizeUsdc]);

  const handleSubmit = async () => {
    if (!sizeUsdc || parseFloat(sizeUsdc) <= 0) {
      setResult({ success: false, message: 'Please enter a valid size' });
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8082/intents', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': 'demo_key' // TODO: Real auth
        },
        body: JSON.stringify({
          agent_id: 'web_user',
          intent_type: side.toLowerCase(),
          asset: market,
          size_usdc: parseFloat(sizeUsdc),
          leverage,
          max_slippage: 0.01,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult({ success: true, message: `Order submitted! 🦞` });
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
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      {/* Header */}
      <div className="border-b border-zinc-800/50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🦞</span>
            <span className="font-bold text-lg">AI Perp DEX</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-xs text-zinc-500">Available Balance</div>
              <div className="font-mono text-[#00D4AA]">${balance.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto mt-8 px-4">
        {/* Market Selector */}
        <div className="bg-[#111] border border-zinc-800/50 rounded-lg p-1 mb-4">
          <div className="flex">
            {MARKETS.map(m => (
              <button
                key={m.symbol}
                onClick={() => setMarket(m.symbol)}
                className={`flex-1 py-2 px-3 rounded-md transition-all ${
                  market === m.symbol
                    ? 'bg-[#1a1a1a] text-white'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <div className="flex items-center justify-center gap-1.5">
                  <span className="text-lg">{m.icon}</span>
                  <span className="font-medium text-sm">{m.symbol.replace('-PERP', '')}</span>
                </div>
                <div className="font-mono text-xs mt-0.5 opacity-60">
                  ${m.price.toLocaleString()}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Trading Card */}
        <div className="bg-[#111] border border-zinc-800/50 rounded-lg p-5">
          {/* Long/Short Toggle */}
          <div className="flex bg-[#0a0a0a] p-1 rounded-lg mb-5">
            <button
              onClick={() => setSide('LONG')}
              className={`flex-1 py-2.5 rounded-md font-semibold text-sm transition-all ${
                side === 'LONG'
                  ? 'bg-[#00D4AA] text-black'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Long
            </button>
            <button
              onClick={() => setSide('SHORT')}
              className={`flex-1 py-2.5 rounded-md font-semibold text-sm transition-all ${
                side === 'SHORT'
                  ? 'bg-[#FF6B35] text-white'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Short
            </button>
          </div>

          {/* Size Input */}
          <div className="mb-4">
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-zinc-500">Size</span>
              <span className="text-zinc-500">
                Max: <span className="text-zinc-300 font-mono">${(balance * leverage * 0.95).toFixed(0)}</span>
              </span>
            </div>
            <div className="relative">
              <input
                type="number"
                value={sizeUsdc}
                onChange={e => setSizeUsdc(e.target.value)}
                placeholder="0.00"
                className="w-full bg-[#0a0a0a] border border-zinc-800 rounded-lg px-4 py-3 text-right font-mono text-lg text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 transition"
              />
              <div className="absolute left-3 top-1/2 -translate-y-1/2 flex gap-1.5">
                <button
                  onClick={() => setSizeUsdc(String(balance * leverage * 0.25))}
                  className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded hover:bg-zinc-700"
                >
                  25%
                </button>
                <button
                  onClick={() => setSizeUsdc(String(balance * leverage * 0.5))}
                  className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded hover:bg-zinc-700"
                >
                  50%
                </button>
                <button
                  onClick={() => setSizeUsdc(String(balance * leverage * 0.95))}
                  className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded hover:bg-zinc-700"
                >
                  MAX
                </button>
              </div>
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 text-sm">USDC</span>
            </div>
          </div>

          {/* Leverage Slider */}
          <div className="mb-5">
            <div className="flex justify-between text-xs mb-2">
              <span className="text-zinc-500">Leverage</span>
              <span className="font-mono text-white">{leverage}x</span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              value={leverage}
              onChange={e => setLeverage(Number(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none bg-zinc-800 cursor-pointer 
                [&::-webkit-slider-thumb]:appearance-none 
                [&::-webkit-slider-thumb]:w-4 
                [&::-webkit-slider-thumb]:h-4 
                [&::-webkit-slider-thumb]:rounded-full 
                [&::-webkit-slider-thumb]:bg-[#00D4AA] 
                [&::-webkit-slider-thumb]:shadow-lg
                [&::-webkit-slider-thumb]:cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-zinc-600 mt-1">
              <span>1x</span>
              <span>5x</span>
              <span>10x</span>
              <span>15x</span>
              <span>20x</span>
            </div>
          </div>

          {/* Order Summary */}
          <div className="border-t border-zinc-800/50 pt-4 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-zinc-500">Entry Price</span>
              <span className="font-mono text-zinc-300">${selectedMarket.price.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Position Size</span>
              <span className="font-mono text-zinc-300">
                {positionSize.toFixed(6)} {market.replace('-PERP', '')}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Required Margin</span>
              <span className="font-mono text-zinc-300">${estimatedMargin.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Est. Liq Price</span>
              <span className={`font-mono ${side === 'LONG' ? 'text-[#FF6B35]' : 'text-[#00D4AA]'}`}>
                ${liquidationPrice.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Fee (0.05%)</span>
              <span className="font-mono text-zinc-400">-${estimatedFee.toFixed(2)}</span>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={loading || !sizeUsdc || parseFloat(sizeUsdc) <= 0}
            className={`w-full mt-5 py-3.5 rounded-lg font-bold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
              side === 'LONG'
                ? 'bg-[#00D4AA] text-black hover:bg-[#00E4BA]'
                : 'bg-[#FF6B35] text-white hover:bg-[#FF7B45]'
            }`}
          >
            {loading ? (
              <span className="animate-pulse">Submitting...</span>
            ) : (
              `${side === 'LONG' ? 'Long' : 'Short'} ${market.replace('-PERP', '')} ${leverage}x`
            )}
          </button>

          {/* Result Message */}
          {result && (
            <div className={`mt-4 p-3 rounded-lg text-sm ${
              result.success 
                ? 'bg-[#00D4AA]/10 border border-[#00D4AA]/30 text-[#00D4AA]' 
                : 'bg-[#FF6B35]/10 border border-[#FF6B35]/30 text-[#FF6B35]'
            }`}>
              {result.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6 text-xs text-zinc-600">
          Trades matched P2P with AI agents 🦞
        </div>
      </div>
    </div>
  );
}
