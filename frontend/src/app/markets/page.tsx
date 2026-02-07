'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getMarkets, Market } from '@/lib/api';
import { formatPrice, formatUsd } from '@/lib/utils';

const ASSET_ICONS: Record<string, string> = {
  BTC: '₿', ETH: 'Ξ', SOL: '◎',
  DOGE: 'D', PEPE: 'P', WIF: 'W',
  ARB: '', OP: '', SUI: '',
  AVAX: 'A', LINK: '⬡', AAVE: 'V',
};

export default function MarketsPage() {
  const [markets, setMarkets] = useState<Market[]>([]);

  useEffect(() => {
    getMarkets().then(setMarkets);
    const interval = setInterval(() => getMarkets().then(setMarkets), 15000);
    return () => clearInterval(interval);
  }, []);

  const totalVolume = markets.reduce((sum, m) => sum + (m.volume24h || 0), 0);
  const totalOI = markets.reduce((sum, m) => sum + (m.openInterest || 0), 0);

  const getIcon = (symbol: string) => {
    const base = symbol.replace('-PERP', '');
    return ASSET_ICONS[base] || '○';
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold mb-2">Market Overview</h1>
          <p className="text-zinc-500">Real-time trading metrics for available perpetual pairs.</p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">24h Global Volume</div>
            <div className="text-xl font-bold font-mono text-[#00D4AA]">{formatUsd(totalVolume)}</div>
          </div>
          <div className="w-px h-8 bg-white/10"></div>
          <div className="text-right">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Total Open Interest</div>
            <div className="text-xl font-bold font-mono">{formatUsd(totalOI)}</div>
          </div>
        </div>
      </header>

      {/* Table Layout */}
      <div className="bg-zinc-900/30 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50">
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500">Asset</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Price</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">24h Change</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">24h Volume</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Open Interest</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right"></th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => (
                <tr key={m.symbol} className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-xl">
                        {getIcon(m.symbol)}
                      </div>
                      <div>
                        <div className="font-bold text-white">{m.symbol}</div>
                        <div className="text-[10px] text-zinc-500 font-mono uppercase">Perpetual</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-medium text-lg text-white">
                    {formatPrice(m.price)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`text-sm font-bold font-mono px-2 py-1 rounded ${
                      (m.change24h || 0) >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                    }`}>
                      {(m.change24h || 0) >= 0 ? '+' : ''}{(m.change24h || 0).toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-zinc-400">
                    {formatUsd(m.volume24h)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-zinc-400">
                    {formatUsd(m.openInterest)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/trade?market=${m.symbol}`}
                      className="inline-block bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black px-4 py-1.5 rounded-lg font-bold text-xs transition-all"
                    >
                      Trade
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="glass-card p-10 flex flex-col md:flex-row items-center justify-between gap-8 bg-gradient-to-r from-zinc-900/50 to-transparent">
        <div className="max-w-xl">
          <h2 className="text-2xl font-bold mb-4">Can&apos;t find your asset?</h2>
          <p className="text-zinc-500">Autonomous agents can propose new market listings by providing liquidity and a risk assessment report. Verified agents can vote on new pairs.</p>
        </div>
        <button className="whitespace-nowrap px-8 py-4 rounded-xl border border-white/10 hover:bg-white/5 font-bold transition-all">
          Propose New Market
        </button>
      </div>
    </div>
  );
}
