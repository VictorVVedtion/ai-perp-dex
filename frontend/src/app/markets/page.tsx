import { getMarkets } from '@/lib/api';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function MarketsPage() {
  const markets = await getMarkets();

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold mb-2">Market Overview</h1>
          <p className="text-zinc-500">Real-time trading metrics for available perpetual pairs.</p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">24h Global Volume</div>
            <div className="text-xl font-bold font-mono text-[#00D4AA]">$2.45B</div>
          </div>
          <div className="w-px h-8 bg-white/10"></div>
          <div className="text-right">
            <div className="text-[10px] text-zinc-500 font-mono uppercase">Total Open Interest</div>
            <div className="text-xl font-bold font-mono">$152.8M</div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {markets.map(m => (
          <div key={m.symbol} className="glass-card p-8 flex flex-col group hover:border-[#00D4AA]/30 transition-all">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                  {m.symbol.includes('BTC') ? '₿' : m.symbol.includes('ETH') ? 'Ξ' : '◎'}
                </div>
                <div>
                  <h3 className="font-bold text-lg">{m.symbol}</h3>
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Perpetual</span>
                </div>
              </div>
              <div className={`text-xs font-bold px-2 py-1 rounded-lg font-mono ${
                (m.change24h||0) >= 0 ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }`}>
                {(m.change24h||0) >= 0 ? '+' : ''}{(m.change24h||0).toFixed(2)}%
              </div>
            </div>

            <div className="space-y-1 mb-8">
              <div className="text-[10px] text-zinc-500 uppercase font-mono tracking-tighter">Current Price</div>
              <div className="text-4xl font-bold font-mono tracking-tight">${m.price.toLocaleString()}</div>
            </div>

            <div className="grid grid-cols-2 gap-4 py-6 border-t border-white/5">
              <div>
                <div className="text-[10px] text-zinc-500 uppercase font-mono mb-1">24h Volume</div>
                <div className="font-bold font-mono text-zinc-300">${(m.volume24h/1e6).toFixed(1)}M</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 uppercase font-mono mb-1">Open Interest</div>
                <div className="font-bold font-mono text-zinc-300">${(m.openInterest/1e6).toFixed(1)}M</div>
              </div>
            </div>

            <div className="mt-auto pt-6 flex gap-3">
              <Link 
                href={`/trade?market=${m.symbol}`}
                className="flex-1 py-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-center text-sm font-bold transition-all"
              >
                View Details
              </Link>
              <Link 
                href={`/trade?market=${m.symbol}`}
                className="flex-1 py-3 rounded-lg bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black text-center text-sm font-bold transition-all"
              >
                Trade Now
              </Link>
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card p-10 flex flex-col md:flex-row items-center justify-between gap-8 bg-gradient-to-r from-zinc-900/50 to-transparent">
        <div className="max-w-xl">
          <h2 className="text-2xl font-bold mb-4">Can't find your asset?</h2>
          <p className="text-zinc-500">Autonomous agents can propose new market listings by providing liquidity and a risk assessment report. Verified agents can vote on new pairs.</p>
        </div>
        <button className="whitespace-nowrap px-8 py-4 rounded-xl border border-white/10 hover:bg-white/5 font-bold transition-all">
          Propose New Market
        </button>
      </div>
    </div>
  );
}