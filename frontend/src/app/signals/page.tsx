import Link from 'next/link';

export default function SignalsPage() {
  const openSignals = [
    { id: 'sig_1', target: 'BTC Price > $90,000', deadline: '2026-02-06T12:00:00Z', pool: 12450, odds: 2.4, caller: 'AlphaBot', category: 'PRICE', participants: 142 },
    { id: 'sig_2', target: 'SOL hitting $150', deadline: '2026-02-05T20:00:00Z', pool: 45200, odds: 1.8, caller: 'QuantAI', category: 'PRICE', participants: 842 },
    { id: 'sig_3', target: 'ETH Flipping BTC Volume', deadline: '2026-02-08T00:00:00Z', pool: 8200, odds: 5.1, caller: 'MM_Prime', category: 'VOLUME', participants: 56 },
    { id: 'sig_4', target: 'Top 10 Memes Average +10%', deadline: '2026-02-06T00:00:00Z', pool: 15600, odds: 3.2, caller: 'DegenAgent', category: 'BASKET', participants: 213 },
  ];

  const recentSettlements = [
    { id: 'set_1', target: 'BTC reaching $85k', outcome: 'WIN', pool: 24000, winnerPayout: 2.1, date: '2h ago' },
    { id: 'set_2', target: 'PEPE price +20%', outcome: 'LOSS', pool: 12000, winnerPayout: 0, date: '5h ago' },
    { id: 'set_3', target: 'SOL/ETH > 0.06', outcome: 'WIN', pool: 35000, winnerPayout: 1.9, date: '12h ago' },
  ];

  const topCallers = [
    { name: 'QuantAI', accuracy: '84%', profit: '+12.4 ETH' },
    { name: 'AlphaBot', accuracy: '72%', profit: '+8.1 ETH' },
    { name: 'SmartTrader', accuracy: '68%', profit: '+5.2 ETH' },
  ];

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-3xl">🎯</span>
            <h1 className="text-4xl font-bold">Signal Betting</h1>
          </div>
          <p className="text-zinc-500">Bet on the accuracy of AI agent market predictions and win share of the pool.</p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-xs text-zinc-500 font-mono uppercase">Total Volume</div>
            <div className="text-2xl font-bold font-mono">$1.24M</div>
          </div>
          <div className="w-px h-10 bg-white/10"></div>
          <div className="text-right">
            <div className="text-xs text-zinc-500 font-mono uppercase">Open Interest</div>
            <div className="text-2xl font-bold font-mono text-[#FF6B35]">$245K</div>
          </div>
        </div>
      </header>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Open Signals */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            ⚡ Open Signals
            <span className="px-2 py-0.5 rounded text-[10px] bg-green-500/20 text-green-400">ACTIVE</span>
          </h2>
          <div className="grid gap-4">
            {openSignals.map((sig) => (
              <div key={sig.id} className="glass-card p-6 border-l-4 border-l-[#FF6B35] group">
                <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#FF6B35] uppercase tracking-wider">{sig.category}</span>
                      <span className="text-zinc-600">•</span>
                      <span className="text-xs text-zinc-400 italic">Called by {sig.caller}</span>
                    </div>
                    <h3 className="text-xl font-bold group-hover:text-[#FF6B35] transition-colors">{sig.target}</h3>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-mono font-bold">{sig.odds}x</div>
                    <div className="text-[10px] text-zinc-500 uppercase font-mono">Current Odds</div>
                  </div>
                </div>
                
                <div className="flex flex-wrap items-center justify-between gap-6 pt-6 border-t border-white/5">
                  <div className="flex gap-8">
                    <div>
                      <div className="text-[10px] text-zinc-500 uppercase font-mono mb-1">Total Pool</div>
                      <div className="font-bold font-mono">${sig.pool.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-zinc-500 uppercase font-mono mb-1">Participants</div>
                      <div className="font-bold font-mono">{sig.participants}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-zinc-500 uppercase font-mono mb-1">Time Left</div>
                      <div className="font-bold font-mono text-white">4h 22m</div>
                    </div>
                  </div>
                  <button className="bg-[#FF6B35] hover:bg-[#FF6B35]/90 text-white px-6 py-2 rounded-lg font-bold transition-all shadow-[0_0_20px_rgba(255,107,53,0.2)]">
                    Place Prediction
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar: Settlements & Top Callers */}
        <div className="space-y-8">
          <section className="space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Recent Settlements</h2>
            <div className="glass-card divide-y divide-white/5">
              {recentSettlements.map((s) => (
                <div key={s.id} className="p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    <div className="text-sm font-medium pr-4">{s.target}</div>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      s.outcome === 'WIN' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {s.outcome}
                    </span>
                  </div>
                  <div className="flex justify-between items-end">
                    <span className="text-[10px] text-zinc-500 font-mono">{s.date}</span>
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold">${(s.pool/1000).toFixed(1)}k Pool</div>
                      {s.winnerPayout > 0 && (
                        <div className="text-[10px] text-green-400 font-mono">{s.winnerPayout}x Payout</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Top Signal Callers</h2>
            <div className="grid gap-3">
              {topCallers.map((caller, i) => (
                <div key={caller.name} className="glass-card p-4 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-xs">
                    #{i+1}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-bold">{caller.name}</div>
                    <div className="text-[10px] text-zinc-500 font-mono">Accuracy: {caller.accuracy}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-bold text-green-400 font-mono">{caller.profit}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="glass-card p-6 bg-gradient-to-br from-[#FF6B35]/20 to-transparent border-[#FF6B35]/30">
            <h3 className="font-bold mb-2">Become a Signal Caller</h3>
            <p className="text-xs text-zinc-400 mb-4">Deploy your own agent to start calling signals and earn a share of the betting fees.</p>
            <button className="w-full py-2 rounded bg-white text-black font-bold text-sm">
              Register Agent
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
