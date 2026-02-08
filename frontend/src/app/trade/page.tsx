'use client';
import { API_BASE_URL } from '@/lib/config';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { getMarkets, Market } from '@/lib/api';
import { formatPrice, formatUsd } from '@/lib/utils';
import AIIntentBar from '@/components/AIIntentBar';

// TradingView symbol mapping — all 12 supported perp markets
const TV_SYMBOLS: Record<string, string> = {
  'BTC-PERP': 'BINANCE:BTCUSDT.P',
  'ETH-PERP': 'BINANCE:ETHUSDT.P',
  'SOL-PERP': 'BINANCE:SOLUSDT.P',
  'DOGE-PERP': 'BINANCE:DOGEUSDT.P',
  'PEPE-PERP': 'BINANCE:PEPEUSDT.P',
  'WIF-PERP': 'BINANCE:WIFUSDT.P',
  'ARB-PERP': 'BINANCE:ARBUSDT.P',
  'OP-PERP': 'BINANCE:OPUSDT.P',
  'SUI-PERP': 'BINANCE:SUIUSDT.P',
  'AVAX-PERP': 'BINANCE:AVAXUSDT.P',
  'LINK-PERP': 'BINANCE:LINKUSDT.P',
  'AAVE-PERP': 'BINANCE:AAVEUSDT.P',
};

const MARKET_ICONS: Record<string, string> = {
  'BTC-PERP': '₿',
  'ETH-PERP': 'Ξ',
  'SOL-PERP': '◎',
  'DOGE-PERP': 'D',
  'PEPE-PERP': 'P',
  'WIF-PERP': 'W',
  'ARB-PERP': '',
  'OP-PERP': '',
  'SUI-PERP': '',
  'AVAX-PERP': 'A',
  'LINK-PERP': '⬡',
  'AAVE-PERP': 'V',
};

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

export default function TradePage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [marketDataReady, setMarketDataReady] = useState(false);
  const [market, setMarket] = useState('BTC-PERP');
  const [side, setSide] = useState<'LONG' | 'SHORT'>('LONG');
  const [sizeUsdc, setSizeUsdc] = useState('');
  const [leverage, setLeverage] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [balance, setBalance] = useState(0);
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [apiKey, setApiKey] = useState('');
  const [agentId, setAgentId] = useState('');
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartUnavailable, setChartUnavailable] = useState(false);
  const [fundingRate, setFundingRate] = useState<{ rate: number; rate_pct: string } | null>(null);

  // Positions state
  const [positions, setPositions] = useState<Position[]>([]);
  const [closeTarget, setCloseTarget] = useState<Position | null>(null);
  const [slTpTarget, setSlTpTarget] = useState<Position | null>(null);
  const [slInput, setSlInput] = useState('');
  const [tpInput, setTpInput] = useState('');
  const [posFeedback, setPosFeedback] = useState<string | null>(null);

  // Fetch funding rate when market changes
  useEffect(() => {
    let active = true;
    const asset = market.replace('-PERP', '');
    const fetchFunding = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/funding/${asset}-PERP`);
        if (res.ok && active) {
          const data = await res.json();
          if (data.rate !== undefined) {
            setFundingRate({ rate: data.rate, rate_pct: data.rate_pct || `${(data.rate * 100).toFixed(4)}%` });
          }
        }
      } catch { /* non-critical */ }
    };
    fetchFunding();
    const interval = setInterval(fetchFunding, 30000);
    return () => { active = false; clearInterval(interval); };
  }, [market]);

  // 从 localStorage 读取认证信息 + 获取真实余额
  useEffect(() => {
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      try {
        const { apiKey: key, agentId: id } = JSON.parse(saved);
        setApiKey(key);
        setAgentId(id);
        // 获取真实余额
        if (id && key) {
          fetch(`${API_BASE_URL}/balance/${id}`, {
            headers: { 'X-API-Key': key },
          })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
              if (data) setBalance(data.available ?? data.balance ?? 0);
            })
            .catch(() => {
              setResult({ success: false, message: 'Failed to fetch balance. Please refresh.' });
            });
        }
      } catch {}
    }
  }, []);

  // Read ?market= query param from URL (e.g. from Markets page Trade button)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const marketParam = params.get('market');
    if (marketParam && TV_SYMBOLS[marketParam]) {
      setMarket(marketParam);
    }
  }, []);

  // Fetch markets from API
  useEffect(() => {
    let active = true;
    const fetchMarkets = async () => {
      const data = await getMarkets();
      if (!active) return;
      if (data.length > 0) {
        setMarkets(data);
        setMarketDataReady(true);
      } else {
        setMarkets([]);
        setMarketDataReady(false);
        setResult((prev) => prev ?? { success: false, message: 'Price feed unavailable. Please check your backend at :8082.' });
      }
    };
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 10000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  // Load TradingView widget
  useEffect(() => {
    if (!chartContainerRef.current) return;
    if (!marketDataReady) {
      chartContainerRef.current.innerHTML = '';
      setChartUnavailable(true);
      return;
    }
    
    // Clear previous widget
    chartContainerRef.current.innerHTML = '';
    setChartUnavailable(false);
    
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

    const timeout = window.setTimeout(() => {
      const hasWidget = !!chartContainerRef.current?.querySelector('iframe');
      if (!hasWidget) setChartUnavailable(true);
    }, 5000);

    return () => window.clearTimeout(timeout);
  }, [market, marketDataReady]);

  const selectedMarket = markets.find(m => m.symbol === market) || {
    symbol: market,
    price: 0,
    volume24h: 0,
    openInterest: 0,
    change24h: 0,
  };

  const marketOptions: Market[] = markets.length > 0
    ? markets
    : Object.keys(TV_SYMBOLS).map((symbol) => ({
      symbol,
      price: 0,
      volume24h: 0,
      openInterest: 0,
      change24h: 0,
    }));

  const normalizeMarket = (rawMarket: unknown): string | null => {
    if (typeof rawMarket !== 'string') return null;
    const normalized = rawMarket.trim().toUpperCase().replace(/\s+/g, '').replace(/_/g, '-');
    if (!normalized) return null;
    if (TV_SYMBOLS[normalized]) return normalized;
    if (normalized.endsWith('-PERP') && TV_SYMBOLS[normalized]) return normalized;
    const baseAsset = normalized
      .replace(/USDT$/, '')
      .replace(/USD$/, '')
      .replace(/-PERP$/, '');
    const perpAsset = `${baseAsset}-PERP`;
    return TV_SYMBOLS[perpAsset] ? perpAsset : null;
  };

  const applyIntent = async (input: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/intents/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input }),
      });

      if (!res.ok) {
        setResult({ success: false, message: 'Intent parser unavailable. Please check backend connectivity.' });
        return;
      }

      const data = await res.json();
      const parsed = data?.parsed || {};
      const updates: string[] = [];

      const action = String(parsed.action || '').toLowerCase();
      if (action === 'long' || action === 'short') {
        const nextSide = action === 'long' ? 'LONG' : 'SHORT';
        setSide(nextSide);
        updates.push(nextSide === 'LONG' ? 'side: Buy/Long' : 'side: Sell/Short');
      }

      const parsedMarket = normalizeMarket(parsed.market);
      if (parsedMarket) {
        setMarket(parsedMarket);
        updates.push(`market: ${parsedMarket}`);
      }

      const parsedSize = Number(parsed.size);
      if (Number.isFinite(parsedSize) && parsedSize > 0) {
        setSizeUsdc(String(parsedSize));
        updates.push(`size: $${parsedSize}`);
      }

      const parsedLeverage = Number(parsed.leverage);
      if (Number.isFinite(parsedLeverage) && parsedLeverage > 0) {
        const nextLeverage = Math.max(1, Math.min(20, Math.round(parsedLeverage)));
        setLeverage(nextLeverage);
        updates.push(`leverage: ${nextLeverage}x`);
      }

      if (updates.length === 0) {
        setResult({ success: false, message: 'Could not map this intent to trade params. Try "Long BTC with $200 at 5x".' });
        return;
      }

      setResult({ success: true, message: `Intent applied: ${updates.join(' • ')}` });
    } catch {
      setResult({ success: false, message: 'Failed to parse intent. Please retry with a clearer command.' });
    }
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

  // Fetch open positions
  const fetchPositions = useCallback(async () => {
    if (!agentId || !apiKey) return;
    try {
      const res = await fetch(`${API_BASE_URL}/positions/${agentId}`, {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      });
      if (res.ok) {
        const data = await res.json();
        setPositions((data.positions || []).filter((p: Position) => p.is_open));
      }
    } catch { /* non-critical */ }
  }, [agentId, apiKey]);

  useEffect(() => {
    if (agentId && apiKey) {
      fetchPositions();
      const interval = setInterval(fetchPositions, 15000);
      return () => clearInterval(interval);
    }
  }, [agentId, apiKey, fetchPositions]);

  const handleClosePosition = async () => {
    if (!closeTarget || !apiKey) return;
    const target = closeTarget;
    setCloseTarget(null);
    try {
      const res = await fetch(`${API_BASE_URL}/positions/${target.position_id}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
      });
      if (res.ok) {
        setPosFeedback(`Closed ${target.asset} position.`);
        fetchPositions();
      } else {
        const err = await res.json();
        setPosFeedback(`Close failed: ${err.detail || 'Unknown error'}`);
      }
    } catch {
      setPosFeedback('Network error closing position.');
    }
    setTimeout(() => setPosFeedback(null), 4000);
  };

  const handleSetSlTp = async (type: 'stop-loss' | 'take-profit') => {
    if (!slTpTarget || !apiKey) return;
    const priceStr = type === 'stop-loss' ? slInput : tpInput;
    const price = parseFloat(priceStr);
    if (!Number.isFinite(price) || price <= 0) {
      setPosFeedback('Enter a valid price.');
      setTimeout(() => setPosFeedback(null), 3000);
      return;
    }
    // Direction validation: warn if SL/TP is in wrong direction
    const isLong = slTpTarget.side === 'long';
    if (type === 'stop-loss') {
      if (isLong && price >= slTpTarget.entry_price) {
        setPosFeedback('Warning: Stop Loss for LONG should be below entry price.');
        setTimeout(() => setPosFeedback(null), 4000);
        return;
      }
      if (!isLong && price <= slTpTarget.entry_price) {
        setPosFeedback('Warning: Stop Loss for SHORT should be above entry price.');
        setTimeout(() => setPosFeedback(null), 4000);
        return;
      }
    }
    if (type === 'take-profit') {
      if (isLong && price <= slTpTarget.entry_price) {
        setPosFeedback('Warning: Take Profit for LONG should be above entry price.');
        setTimeout(() => setPosFeedback(null), 4000);
        return;
      }
      if (!isLong && price >= slTpTarget.entry_price) {
        setPosFeedback('Warning: Take Profit for SHORT should be below entry price.');
        setTimeout(() => setPosFeedback(null), 4000);
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE_URL}/positions/${slTpTarget.position_id}/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ price }),
      });
      if (res.ok) {
        setPosFeedback(`${type === 'stop-loss' ? 'Stop Loss' : 'Take Profit'} set at $${price}`);
        fetchPositions();
        setSlTpTarget(null);
        setSlInput('');
        setTpInput('');
      } else {
        const err = await res.json();
        setPosFeedback(err.detail || `Failed to set ${type}`);
      }
    } catch {
      setPosFeedback(`Network error setting ${type}.`);
    }
    setTimeout(() => setPosFeedback(null), 4000);
  };

  const handleSubmit = async () => {
    if (!marketDataReady || selectedMarket.price <= 0) {
      setResult({ success: false, message: 'Live market data is required before submitting an order.' });
      return;
    }

    if (!sizeUsdc || parseFloat(sizeUsdc) <= 0) {
      setResult({ success: false, message: 'Please enter a valid size' });
      return;
    }

    setLoading(true);
    setResult(null);

    if (!apiKey || !agentId) {
      setResult({ success: false, message: 'Please connect your agent first. Go to /connect to get started.' });
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/intents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          agent_id: agentId,
          intent_type: side.toLowerCase(),
          asset: market,
          size_usdc: parseFloat(sizeUsdc),
          leverage,
          max_slippage: 0.01,
        }),
      });

      if (response.ok) {
        setResult({ success: true, message: `Order submitted successfully!` });
        setSizeUsdc('');
        fetchPositions(); // Refresh positions after trade
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
    <div className="min-h-screen bg-layer-0 text-rb-text-main">
      {/* Market Header */}
      <div className="flex items-center justify-between p-4 border-b border-layer-3">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-layer-1 flex items-center justify-center text-xl border border-layer-3/70">
            {MARKET_ICONS[selectedMarket.symbol] || '○'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-rb-text-main tracking-tight">{selectedMarket.symbol}</h1>
              <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-layer-2 text-rb-text-secondary border border-layer-3">PERP</span>
            </div>
            <div className="flex items-center gap-3 text-sm font-mono mt-0.5">
              <span className="text-rb-text-main">{formatPrice(selectedMarket.price)}</span>
              <span className={(selectedMarket.change24h ?? 0) >= 0 ? 'text-rb-cyan' : 'text-rb-red'}>
                {(selectedMarket.change24h ?? 0) > 0 ? '+' : ''}{(selectedMarket.change24h ?? 0).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-8 text-right hidden sm:flex">
          <div>
            <div className="text-[10px] text-rb-text-secondary uppercase tracking-wider">24h Volume</div>
            <div className="text-sm font-mono text-rb-text-main">{formatUsd(selectedMarket.volume24h)}</div>
          </div>
          <div>
            <div className="text-[10px] text-rb-text-secondary uppercase tracking-wider">Open Interest</div>
            <div className="text-sm font-mono text-rb-text-main">{formatUsd(selectedMarket.openInterest)}</div>
          </div>
          <div>
            <div className="text-[10px] text-rb-text-secondary uppercase tracking-wider">Funding / 1h</div>
            <div className={`text-sm font-mono ${fundingRate && fundingRate.rate >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
              {fundingRate ? fundingRate.rate_pct : '—'}
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 pt-4">
        <AIIntentBar
          placeholder="Try: long BTC with $200 at 5x leverage"
          suggestions={[
            'Long BTC with $200 at 5x',
            'Short ETH with $80 at 3x',
            'Long SOL 10x with $50',
          ]}
          submitLabel="Parse Intent"
          loadingLabel="Parsing..."
          onSubmit={applyIntent}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
        {/* TradingView Chart */}
        <div className="lg:col-span-8 h-[500px] rounded-xl overflow-hidden border border-layer-3 relative bg-layer-1">
          <div
            ref={chartContainerRef}
            className="tradingview-widget-container w-full h-full"
          />
          {chartUnavailable && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-layer-0/85 backdrop-blur-sm text-center px-6">
              <p className="text-rb-text-main font-bold mb-2">Chart Unavailable</p>
              <p className="text-rb-text-secondary text-sm mb-4">
                TradingView embed did not load. You can still place orders using live price feed.
              </p>
              <a
                href={`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(TV_SYMBOLS[market] || 'BINANCE:BTCUSDT.P')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-outline btn-sm"
              >
                Open External Chart
              </a>
            </div>
          )}
        </div>

        {/* Trading Panel */}
        <div className="lg:col-span-4">
          <div className="bg-layer-1 border border-layer-3 rounded-xl overflow-hidden">
            {/* Buy/Sell Tabs */}
            <div className="flex border-b border-layer-3">
              <button
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  side === 'LONG' ? 'text-rb-cyan bg-rb-cyan/10' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-2'
                }`}
                onClick={() => setSide('LONG')}
              >
                Buy / Long
              </button>
              <div className="w-[1px] bg-layer-3" />
              <button
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  side === 'SHORT' ? 'text-rb-red bg-rb-red/10' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-2'
                }`}
                onClick={() => setSide('SHORT')}
              >
                Sell / Short
              </button>
            </div>

            <div className="p-5 flex flex-col gap-5">
              {/* Order Type */}
              <div className="flex gap-4 text-xs font-medium text-rb-text-secondary">
                <button
                  onClick={() => setOrderType('MARKET')}
                  className={`px-3 py-1.5 rounded-md transition-colors ${
                    orderType === 'MARKET' ? 'bg-layer-3 text-rb-text-main' : 'hover:text-rb-text-main'
                  }`}
                >
                  Market
                </button>
                <button
                  onClick={() => setOrderType('LIMIT')}
                  className={`px-3 py-1.5 rounded-md transition-colors relative ${
                    orderType === 'LIMIT' ? 'bg-layer-3 text-rb-text-main' : 'hover:text-rb-text-main'
                  }`}
                >
                  Limit
                  <span className="absolute -top-1.5 -right-3 text-[8px] text-rb-yellow font-bold">Soon</span>
                </button>
              </div>

              {orderType === 'LIMIT' && (
                <div className="bg-rb-yellow/10 border border-rb-yellow/20 text-rb-yellow text-xs px-3 py-2 rounded-lg">
                  Limit orders are coming soon. Market orders are available now.
                </div>
              )}

              {/* Market Selector */}
              <div>
                <label className="text-[10px] uppercase text-rb-text-secondary font-bold tracking-wider mb-2 block">Market</label>
                <div className="grid grid-cols-3 gap-2">
                  {marketOptions.map((m) => (
                    <button
                      key={m.symbol}
                      onClick={() => setMarket(m.symbol)}
                      className={`flex flex-col items-center justify-center p-2 rounded-lg border transition-all ${
                        market === m.symbol
                          ? 'bg-layer-2 border-layer-4 text-rb-text-main shadow-inner'
                          : 'bg-transparent border-layer-3/80 text-rb-text-secondary hover:border-layer-4 hover:bg-layer-2/50'
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
                  <span className="text-rb-text-secondary font-medium">Amount (USDC)</span>
                  <span className="text-rb-text-secondary">
                    Max: <span className="text-rb-text-main font-mono">${(balance * leverage * 0.95).toFixed(0)}</span>
                  </span>
                </div>
                <div className="relative group">
                  <input
                    type="number"
                    value={sizeUsdc}
                    onChange={(e) => setSizeUsdc(e.target.value)}
                    placeholder="0.00"
                    className="w-full bg-layer-0 border border-layer-3 group-hover:border-layer-4 rounded-lg px-4 py-3.5 text-right font-mono text-lg text-rb-text-main placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan/60 focus:ring-1 focus:ring-rb-cyan/30 transition-all"
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 flex gap-1">
                    {['25%', '50%', 'Max'].map((label) => (
                      <button
                        key={label}
                        onClick={() => {
                          const multiplier = label === 'Max' ? 0.95 : parseInt(label) / 100;
                          setSizeUsdc(String(Math.floor(balance * leverage * multiplier)));
                        }}
                        className="text-[10px] bg-layer-2 border border-layer-3 text-rb-text-secondary px-2 py-1 rounded hover:bg-layer-3 hover:text-rb-text-main transition-colors"
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
                  <span className="text-rb-text-secondary font-medium">Leverage</span>
                  <span className="text-rb-text-main font-mono bg-layer-2 px-2 py-0.5 rounded border border-layer-3">
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
                  className="w-full h-1.5 rounded-full appearance-none bg-layer-3 cursor-pointer accent-rb-cyan"
                />
                <div className="flex justify-between text-[10px] text-rb-text-placeholder font-mono">
                  <span>1x</span>
                  <span>5x</span>
                  <span>10x</span>
                  <span>15x</span>
                  <span>20x</span>
                </div>
              </div>

              {/* Order Info */}
              <div className="space-y-3 pt-4 border-t border-dashed border-layer-3 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-rb-text-secondary">Liquidation Price</span>
                  <span className={`font-mono ${side === 'LONG' ? 'text-rb-red' : 'text-rb-cyan'}`}>
                    {liquidationPrice > 0 ? formatPrice(liquidationPrice) : '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-rb-text-secondary">Slippage Tolerance</span>
                  <span className="font-mono text-rb-text-main">1.00%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-rb-text-secondary">Trading Fee</span>
                  <span className="font-mono text-rb-text-main">${estimatedFee.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="text-rb-text-secondary font-medium">Total Margin</span>
                  <span className="font-mono text-rb-text-main text-sm">${estimatedMargin.toFixed(2)}</span>
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={handleSubmit}
                disabled={loading || !sizeUsdc || parseFloat(sizeUsdc) <= 0 || !marketDataReady || selectedMarket.price <= 0 || orderType === 'LIMIT'}
                className={`w-full py-4 rounded-lg font-bold text-sm tracking-wide transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)] 
                  disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none
                  ${
                    side === 'LONG'
                      ? 'bg-rb-cyan text-layer-0 hover:bg-rb-cyan/90 hover:shadow-[0_0_15px_rgba(14,236,188,0.3)]'
                      : 'bg-rb-red text-rb-text-main hover:bg-rb-red/90 hover:shadow-[0_0_15px_rgba(221,60,65,0.35)]'
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
                      ? 'bg-rb-cyan/10 text-rb-cyan border border-rb-cyan/20'
                      : 'bg-rb-red/10 text-rb-red border border-rb-red/20'
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
      {/* Open Positions Section */}
      {agentId && (
        <div className="px-4 pb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold">My Positions ({positions.length})</h2>
            {posFeedback && (
              <span className="text-xs font-mono px-3 py-1 rounded bg-layer-2 border border-layer-3 text-rb-text-secondary">
                {posFeedback}
              </span>
            )}
          </div>

          {positions.length === 0 ? (
            <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 text-center text-rb-text-secondary text-sm">
              No open positions. Place an order above to get started.
            </div>
          ) : (
            <div className="space-y-3">
              {positions.map((pos) => (
                <div key={pos.position_id} className="bg-layer-1 border border-layer-3 rounded-xl p-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-lg bg-layer-2 flex items-center justify-center text-sm border border-layer-3">
                        {MARKET_ICONS[pos.asset] || '○'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{pos.asset}</span>
                          <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                            pos.side === 'long' ? 'bg-rb-cyan/15 text-rb-cyan' : 'bg-rb-red/15 text-rb-red'
                          }`}>
                            {pos.side.toUpperCase()} {pos.leverage}x
                          </span>
                        </div>
                        <div className="text-xs text-rb-text-secondary font-mono">
                          ${pos.size_usdc} @ {formatPrice(pos.entry_price)}
                          {pos.stop_loss ? ` | SL: ${formatPrice(pos.stop_loss)}` : ''}
                          {pos.take_profit ? ` | TP: ${formatPrice(pos.take_profit)}` : ''}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className={`font-mono font-bold ${pos.unrealized_pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                          {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                        </div>
                        <div className={`text-xs font-mono ${pos.unrealized_pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                          {pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setSlTpTarget(pos);
                            setSlInput(pos.stop_loss?.toString() || '');
                            setTpInput(pos.take_profit?.toString() || '');
                          }}
                          className="text-xs px-3 py-1.5 rounded border border-layer-4 text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-2 transition-colors"
                        >
                          SL/TP
                        </button>
                        <button
                          onClick={() => setCloseTarget(pos)}
                          className="text-xs px-3 py-1.5 rounded border border-rb-red/30 text-rb-red hover:bg-rb-red/10 transition-colors"
                        >
                          Close
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Close Position Confirm Dialog */}
      {closeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-2">Close Position</h3>
            <p className="text-rb-text-secondary text-sm mb-1">
              {closeTarget.asset} {closeTarget.side.toUpperCase()} {closeTarget.leverage}x
            </p>
            <p className={`text-sm font-mono mb-6 ${closeTarget.unrealized_pnl >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
              PnL: {closeTarget.unrealized_pnl >= 0 ? '+' : ''}${closeTarget.unrealized_pnl.toFixed(2)}
            </p>
            <div className="flex gap-3">
              <button onClick={() => setCloseTarget(null)} className="flex-1 btn-secondary-2 btn-md">Cancel</button>
              <button onClick={handleClosePosition} className="flex-1 bg-rb-red hover:bg-rb-red/90 text-rb-text-main px-4 py-2 rounded-lg font-bold transition-colors">
                Close Position
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SL/TP Dialog */}
      {slTpTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-1">Set Stop Loss / Take Profit</h3>
            <p className="text-xs text-rb-text-secondary mb-4 font-mono">
              {slTpTarget.asset} {slTpTarget.side.toUpperCase()} @ {formatPrice(slTpTarget.entry_price)}
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-rb-text-secondary uppercase font-bold mb-1 block">Stop Loss Price</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={slInput}
                    onChange={(e) => setSlInput(e.target.value)}
                    placeholder={slTpTarget.side === 'long' ? 'Below entry' : 'Above entry'}
                    className="flex-1 input-base input-md font-mono"
                  />
                  <button
                    onClick={() => handleSetSlTp('stop-loss')}
                    disabled={!slInput}
                    className="btn-secondary-2 btn-md text-xs disabled:opacity-40"
                  >
                    Set SL
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-rb-text-secondary uppercase font-bold mb-1 block">Take Profit Price</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={tpInput}
                    onChange={(e) => setTpInput(e.target.value)}
                    placeholder={slTpTarget.side === 'long' ? 'Above entry' : 'Below entry'}
                    className="flex-1 input-base input-md font-mono"
                  />
                  <button
                    onClick={() => handleSetSlTp('take-profit')}
                    disabled={!tpInput}
                    className="btn-secondary-2 btn-md text-xs disabled:opacity-40"
                  >
                    Set TP
                  </button>
                </div>
              </div>
            </div>
            <button
              onClick={() => { setSlTpTarget(null); setSlInput(''); setTpInput(''); }}
              className="w-full mt-4 btn-secondary-2 btn-md"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
