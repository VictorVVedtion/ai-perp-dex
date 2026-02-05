'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { getMarkets, Market } from '@/lib/api';

// TradingView symbol mapping
const TV_SYMBOLS: Record<string, string> = {
  'BTC-PERP': 'BINANCE:BTCUSDT.P',
  'ETH-PERP': 'BINANCE:ETHUSDT.P',
  'SOL-PERP': 'BINANCE:SOLUSDT.P',
};

const MARKET_ICONS: Record<string, string> = {
  'BTC-PERP': '₿',
  'ETH-PERP': 'Ξ',
  'SOL-PERP': '◎',
};

export default function TradePage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [market, setMarket] = useState('BTC-PERP');
  const [side, setSide] = useState<'LONG' | 'SHORT'>('LONG');
  const [sizeUsdc, setSizeUsdc] = useState('');
  const [leverage, setLeverage] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [balance] = useState(10000);
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Fetch markets from API
  useEffect(() => {
    const fetchMarkets = async () => {
      const data = await getMarkets();
      if (data.length > 0) {
        setMarkets(data);
      } else {
        // Fallback if API is down
        setMarkets([
          { symbol: 'BTC-PERP', price: 84000, volume24h: 1200000000, openInterest: 84200000, change24h: 2.4 },
          { symbol: 'ETH-PERP', price: 2200, volume24h: 450000000, openInterest: 32100000, change24h: -1.2 },
          { symbol: 'SOL-PERP', price: 130, volume24h: 200000000, openInterest: 15400000, change24h: 5.7 },
        ]);
      }
    };
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  // Load TradingView widget
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Clear previous widget
    chartContainerRef.current.innerHTML = '';
    
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: TV_SYMBOLS[market] || 'BINANCE:BTCUSDT.P',
      interval: '15',
      timezone: 'America/Los_Angeles',
      theme: 'dark',
      style: '1',
      locale: 'en',
      backgroundColor: '#050505',
      gridColor: 'rgba(255, 255, 255, 0.03)',
      hide_top_toolbar: false,
      hide_legend: false,
      allow_symbol_change: false,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: 'https://www.tradingview.com',
    });
    
    chartContainerRef.current.appendChild(script);
  }, [market]);

  const selectedMarket = markets.find(m => m.symbol === market) || {
    symbol: market,
    price: 0,
    volume24h: 0,
    openInterest: 0,
    change24h: 0,
  };

  const estimatedMargin = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size / leverage;
  }, [sizeUsdc, leverage]);

  const liquidationPrice = useMemo(() => {
    const price = selectedMarket.price;
    if (price === 0) return 0;
    if (side === 'LONG') {
      return price * (1 - 0.9 / leverage);
    } else {
      return price * (1 + 0.9 / leverage);
    }
  }, [selectedMarket.price, leverage, side]);

  const estimatedFee = useMemo(() => {
    const size = parseFloat(sizeUsdc) || 0;
    return size * 0.0005;
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
          'X-API-Key': 'demo_key',
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
        setResult({ success: true, message: `Order submitted successfully! 🦞` });
        setSizeUsdc('');
      } else {
        const error = await response.text();
        setResult({ success: false, message: `Failed: ${error}` });
      }
    } catch (err) {
      setResult({ success: false, message: 'Network error - backend unreachable' });
    } finally {
      setLoading(false);
    }
  };

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return `$${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `$${(vol / 1e6).toFixed(0)}M`;
    return `$${vol.toLocaleString()}`;
  };

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300">
      {/* Market Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-900">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-zinc-900 flex items-center justify-center text-xl border border-zinc-800/50">
            {MARKET_ICONS[selectedMarket.symbol] || '○'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">{selectedMarket.symbol}</h1>
              <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-500 border border-zinc-800">PERP</span>
            </div>
            <div className="flex items-center gap-3 text-sm font-mono mt-0.5">
              <span className="text-white">${selectedMarket.price.toLocaleString()}</span>
              <span className={selectedMarket.change24h >= 0 ? 'text-[#00D4AA]' : 'text-[#FF6B35]'}>
                {selectedMarket.change24h > 0 ? '+' : ''}{selectedMarket.change24h.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-8 text-right hidden sm:flex">
          <div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">24h Volume</div>
            <div className="text-sm font-mono text-zinc-300">{formatVolume(selectedMarket.volume24h)}</div>
          </div>
          <div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Open Interest</div>
            <div className="text-sm font-mono text-zinc-300">{formatVolume(selectedMarket.openInterest)}</div>
          </div>
          <div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Funding / 1h</div>
            <div className="text-sm font-mono text-[#FF6B35]">-0.0024%</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
        {/* TradingView Chart */}
        <div className="lg:col-span-8 h-[500px] rounded-xl overflow-hidden border border-zinc-900">
          <div 
            ref={chartContainerRef}
            className="tradingview-widget-container w-full h-full"
          />
        </div>

        {/* Trading Panel */}
        <div className="lg:col-span-4">
          <div className="bg-[#0A0A0A] border border-zinc-900 rounded-xl overflow-hidden">
            {/* Buy/Sell Tabs */}
            <div className="flex border-b border-zinc-900">
              <button
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  side === 'LONG' ? 'text-[#00D4AA] bg-[#00D4AA]/5' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'
                }`}
                onClick={() => setSide('LONG')}
              >
                Buy / Long
              </button>
              <div className="w-[1px] bg-zinc-900" />
              <button
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  side === 'SHORT' ? 'text-[#FF6B35] bg-[#FF6B35]/5' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'
                }`}
                onClick={() => setSide('SHORT')}
              >
                Sell / Short
              </button>
            </div>

            <div className="p-5 flex flex-col gap-5">
              {/* Order Type */}
              <div className="flex gap-4 text-xs font-medium text-zinc-500">
                <button
                  onClick={() => setOrderType('MARKET')}
                  className={`px-3 py-1.5 rounded-md transition-colors ${
                    orderType === 'MARKET' ? 'bg-zinc-800 text-white' : 'hover:text-zinc-300'
                  }`}
                >
                  Market
                </button>
                <button
                  onClick={() => setOrderType('LIMIT')}
                  className={`px-3 py-1.5 rounded-md transition-colors ${
                    orderType === 'LIMIT' ? 'bg-zinc-800 text-white' : 'hover:text-zinc-300'
                  }`}
                >
                  Limit
                </button>
              </div>

              {/* Market Selector */}
              <div>
                <label className="text-[10px] uppercase text-zinc-500 font-bold tracking-wider mb-2 block">Market</label>
                <div className="grid grid-cols-3 gap-2">
                  {markets.map((m) => (
                    <button
                      key={m.symbol}
                      onClick={() => setMarket(m.symbol)}
                      className={`flex flex-col items-center justify-center p-2 rounded-lg border transition-all ${
                        market === m.symbol
                          ? 'bg-zinc-900 border-zinc-700 text-white shadow-inner'
                          : 'bg-transparent border-zinc-800/50 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-900/50'
                      }`}
                    >
                      <span className="text-lg mb-1">{MARKET_ICONS[m.symbol] || '○'}</span>
                      <span className="text-[10px] font-bold">{m.symbol.split('-')[0]}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Amount Input */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500 font-medium">Amount (USDC)</span>
                  <span className="text-zinc-500">
                    Max: <span className="text-zinc-300 font-mono">${(balance * leverage * 0.95).toFixed(0)}</span>
                  </span>
                </div>
                <div className="relative group">
                  <input
                    type="number"
                    value={sizeUsdc}
                    onChange={(e) => setSizeUsdc(e.target.value)}
                    placeholder="0.00"
                    className="w-full bg-[#050505] border border-zinc-800 group-hover:border-zinc-700 rounded-lg px-4 py-3.5 text-right font-mono text-lg text-white placeholder:text-zinc-700 focus:outline-none focus:border-[#00D4AA] focus:ring-1 focus:ring-[#00D4AA]/20 transition-all"
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 flex gap-1">
                    {['25%', '50%', 'Max'].map((label) => (
                      <button
                        key={label}
                        onClick={() => {
                          const multiplier = label === 'Max' ? 0.95 : parseInt(label) / 100;
                          setSizeUsdc(String(Math.floor(balance * leverage * multiplier)));
                        }}
                        className="text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-400 px-2 py-1 rounded hover:bg-zinc-800 hover:text-white transition-colors"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Leverage Slider */}
              <div className="space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500 font-medium">Leverage</span>
                  <span className="text-white font-mono bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                    {leverage}x
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  value={leverage}
                  onChange={(e) => setLeverage(Number(e.target.value))}
                  className="w-full h-1.5 rounded-full appearance-none bg-zinc-800 cursor-pointer accent-[#00D4AA]"
                />
                <div className="flex justify-between text-[10px] text-zinc-600 font-mono">
                  <span>1x</span>
                  <span>5x</span>
                  <span>10x</span>
                  <span>15x</span>
                  <span>20x</span>
                </div>
              </div>

              {/* Order Info */}
              <div className="space-y-3 pt-4 border-t border-dashed border-zinc-800 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Liquidation Price</span>
                  <span className={`font-mono ${side === 'LONG' ? 'text-[#FF6B35]' : 'text-[#00D4AA]'}`}>
                    ${liquidationPrice > 0 ? liquidationPrice.toFixed(2) : '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Slippage Tolerance</span>
                  <span className="font-mono text-zinc-300">1.00%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Trading Fee</span>
                  <span className="font-mono text-zinc-300">${estimatedFee.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="text-zinc-400 font-medium">Total Margin</span>
                  <span className="font-mono text-white text-sm">${estimatedMargin.toFixed(2)}</span>
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={handleSubmit}
                disabled={loading || !sizeUsdc || parseFloat(sizeUsdc) <= 0}
                className={`w-full py-4 rounded-lg font-bold text-sm tracking-wide transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)] 
                  disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none
                  ${
                    side === 'LONG'
                      ? 'bg-[#00D4AA] text-[#050505] hover:bg-[#00F0C0] hover:shadow-[0_0_15px_rgba(0,212,170,0.3)]'
                      : 'bg-[#FF6B35] text-white hover:bg-[#FF8555] hover:shadow-[0_0_15px_rgba(255,107,53,0.3)]'
                  }`}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : (
                  `${side === 'LONG' ? 'Buy / Long' : 'Sell / Short'} ${market.split('-')[0]}`
                )}
              </button>

              {/* Status Message */}
              {result && (
                <div
                  className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 ${
                    result.success
                      ? 'bg-[#00D4AA]/10 text-[#00D4AA] border border-[#00D4AA]/20'
                      : 'bg-[#FF6B35]/10 text-[#FF6B35] border border-[#FF6B35]/20'
                  }`}
                >
                  <span>{result.success ? '✓' : '!'}</span>
                  {result.message}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
