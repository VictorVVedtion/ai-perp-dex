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
  const [showProposalToast, setShowProposalToast] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const fetchMarkets = async () => {
      try {
        const data = await getMarkets();
        if (!active) return;
        setMarkets(data);
        setError(data.length === 0 ? 'No live market data yet. Check backend feed connectivity.' : null);
      } catch {
        if (!active) return;
        setError('Failed to fetch market data. Please retry.');
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 15000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  const totalVolume = markets.reduce((sum, m) => sum + (m.volume24h || 0), 0);
  const totalOI = markets.reduce((sum, m) => sum + (m.openInterest || 0), 0);

  const getIcon = (symbol: string) => {
    const base = symbol.replace('-PERP', '');
    return ASSET_ICONS[base] || '○';
  };

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-lg border border-rb-red/30 bg-rb-red/10 text-rb-red px-4 py-3 text-sm flex items-center justify-between gap-3">
          <span>{error}</span>
          <button
            onClick={async () => {
              setLoading(true);
              try {
                const data = await getMarkets();
                setMarkets(data);
                setError(data.length === 0 ? 'No live market data yet. Check backend feed connectivity.' : null);
              } catch {
                setError('Failed to fetch market data. Please retry.');
              } finally {
                setLoading(false);
              }
            }}
            className="btn-danger-outline btn-sm"
          >
            Retry
          </button>
        </div>
      )}

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

      {/* Table Layout */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6 space-y-4">
              <div className="h-12 bg-layer-2 rounded animate-pulse" />
              <div className="h-12 bg-layer-2 rounded animate-pulse" />
              <div className="h-12 bg-layer-2 rounded animate-pulse" />
              <div className="h-12 bg-layer-2 rounded animate-pulse" />
            </div>
          ) : markets.length === 0 ? (
            <div className="p-10 text-center text-rb-text-secondary">
              No markets available yet. Start the price feed and retry.
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-layer-3 bg-layer-2/70">
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
                  <tr key={m.symbol} className="border-b border-layer-3/40 hover:bg-layer-2/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-layer-2 border border-layer-3 flex items-center justify-center text-xl">
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
                      <Link
                        href={`/trade?market=${m.symbol}`}
                        className="inline-block btn-primary btn-sm"
                      >
                        Trade
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="glass-card p-10 flex flex-col md:flex-row items-center justify-between gap-8 bg-gradient-to-r from-rb-cyan/5 to-transparent">
        <div className="max-w-xl">
          <h2 className="text-2xl font-bold mb-4">Can&apos;t find your asset?</h2>
          <p className="text-rb-text-secondary">Market proposals are on the roadmap. Soon, verified agents will be able to propose new pairs by providing liquidity and risk assessments.</p>
        </div>
        <button
          onClick={() => {
            setShowProposalToast(true);
            setTimeout(() => setShowProposalToast(false), 3000);
          }}
          className="whitespace-nowrap btn-outline btn-lg"
        >
          Propose New Market
        </button>
        {showProposalToast && (
          <div className="fixed bottom-6 right-6 bg-layer-2 border border-layer-3 text-rb-text-main px-5 py-3 rounded-xl text-sm font-mono shadow-xl animate-pulse z-50">
            Market proposals coming soon. Join our Discord for updates.
          </div>
        )}
      </div>
    </div>
  );
}
