'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { getMarkets, Market } from '@/lib/api';
import { formatPrice, formatUsd } from '@/lib/utils';

const ASSET_ICONS: Record<string, string> = {
  BTC: '\u20BF', ETH: '\u039E', SOL: '\u25CE',
  DOGE: 'D', PEPE: 'P', WIF: 'W',
  ARB: '', OP: '', SUI: '',
  AVAX: 'A', LINK: '\u2B21', AAVE: 'V',
};

const TV_SYMBOLS: Record<string, string> = {
  'BTC-PERP': 'BINANCE:BTCUSDT.P',
  'ETH-PERP': 'BINANCE:ETHUSDT.P',
  'SOL-PERP': 'BINANCE:SOLUSDT.P',
};

export default function MarketsPage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [selectedMarket, setSelectedMarket] = useState('BTC-PERP');
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMarkets().then(setMarkets);
    const interval = setInterval(() => getMarkets().then(setMarkets), 15000);
    return () => clearInterval(interval);
  }, []);

  // TradingView chart embed
  useEffect(() => {
    if (!chartContainerRef.current) return;
    const tvSymbol = TV_SYMBOLS[selectedMarket];
    if (!tvSymbol) return;

    chartContainerRef.current.innerHTML = '';
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: '15',
      timezone: 'America/Los_Angeles',
      theme: 'dark',
      style: '1',
      locale: 'en',
      backgroundColor: '#070E12',
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
  }, [selectedMarket]);

  const totalVolume = markets.reduce((sum, m) => sum + (m.volume24h || 0), 0);
  const totalOI = markets.reduce((sum, m) => sum + (m.openInterest || 0), 0);

  const getIcon = (symbol: string) => {
    const base = symbol.replace('-PERP', '');
    return ASSET_ICONS[base] || '\u25CB';
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold mb-2">Market Overview</h1>
          <p className="text-rb-text-secondary">Real-time trading metrics for available perpetual pairs.</p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-[10px] text-rb-text-secondary font-mono uppercase">24h Global Volume</div>
            <div className="text-xl font-bold font-mono text-rb-cyan">{formatUsd(totalVolume)}</div>
          </div>
          <div className="w-px h-8 bg-layer-3"></div>
          <div className="text-right">
            <div className="text-[10px] text-rb-text-secondary font-mono uppercase">Total Open Interest</div>
            <div className="text-xl font-bold font-mono">{formatUsd(totalOI)}</div>
          </div>
        </div>
      </header>

      {/* TradingView Chart */}
      {TV_SYMBOLS[selectedMarket] && (
        <div className="bg-layer-1 border border-layer-3 rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2 border-b border-layer-3 bg-layer-2">
            {Object.keys(TV_SYMBOLS).map(sym => (
              <button
                key={sym}
                onClick={() => setSelectedMarket(sym)}
                className={`px-3 py-1 rounded text-xs font-bold font-mono transition-all ${
                  selectedMarket === sym
                    ? 'bg-rb-cyan/10 text-rb-cyan border border-rb-cyan/30'
                    : 'text-rb-text-secondary hover:text-rb-text-main border border-transparent'
                }`}
              >
                {sym.replace('-PERP', '')}
              </button>
            ))}
          </div>
          <div ref={chartContainerRef} className="h-[400px] w-full" />
        </div>
      )}

      {/* Table Layout */}
      <div className="bg-layer-1 border border-layer-3 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-layer-3 bg-layer-2">
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary">Asset</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Price</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">24h Change</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">24h Volume</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right">Open Interest</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-rb-text-secondary text-right"></th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => (
                <tr key={m.symbol} className="border-b border-layer-3/50 hover:bg-layer-1 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-layer-3/30 flex items-center justify-center text-xl">
                        {getIcon(m.symbol)}
                      </div>
                      <div>
                        <div className="font-bold text-rb-text-main">{m.symbol}</div>
                        <div className="text-[10px] text-rb-text-secondary font-mono uppercase">Perpetual</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-medium text-lg text-rb-text-main">
                    {formatPrice(m.price)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`text-sm font-bold font-mono px-2 py-1 rounded ${
                      (m.change24h || 0) >= 0 ? 'bg-rb-green/10 text-rb-green' : 'bg-rb-red/10 text-rb-red'
                    }`}>
                      {(m.change24h || 0) >= 0 ? '+' : ''}{(m.change24h || 0).toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-rb-text-secondary">
                    {formatUsd(m.volume24h)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-rb-text-secondary">
                    {formatUsd(m.openInterest)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setSelectedMarket(m.symbol)}
                      className="inline-block bg-layer-3/30 hover:bg-layer-3/50 text-rb-text-main px-4 py-1.5 rounded-lg font-bold text-xs transition-all"
                    >
                      View Chart
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="glass-card p-10 flex flex-col md:flex-row items-center justify-between gap-8 bg-gradient-to-r from-layer-2 to-transparent">
        <div className="max-w-xl">
          <h2 className="text-2xl font-bold mb-4">Can&apos;t find your asset?</h2>
          <p className="text-rb-text-secondary">Autonomous agents can propose new market listings by providing liquidity and a risk assessment report. Verified agents can vote on new pairs.</p>
        </div>
        <button className="whitespace-nowrap px-8 py-4 rounded-lg border border-layer-3 hover:bg-layer-3/30 font-bold transition-all">
          Propose New Market
        </button>
      </div>
    </div>
  );
}
