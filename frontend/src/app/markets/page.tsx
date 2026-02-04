import { getMarkets } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function MarketsPage() {
  const markets = await getMarkets();

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">📈 Markets</h1>
      <div className="grid md:grid-cols-3 gap-6">
        {markets.map(m => (
          <div key={m.symbol} className="glass-card p-6">
            <div className="flex justify-between mb-4">
              <span className="font-bold text-lg">{m.symbol}</span>
              <span className={`text-sm px-2 py-1 rounded ${(m.change24h||0) >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                {(m.change24h||0) >= 0 ? '+' : ''}{(m.change24h||0).toFixed(1)}%
              </span>
            </div>
            <div className="text-3xl font-bold font-mono mb-4">${m.price.toLocaleString()}</div>
            <div className="text-zinc-500 text-sm">
              <div>Volume: ${(m.volume24h/1e6).toFixed(1)}M</div>
              <div>OI: ${(m.openInterest/1e6).toFixed(1)}M</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
