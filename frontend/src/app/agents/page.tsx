import Link from 'next/link';

export default function AgentsPage() {
  const agents = [
    { id: '1', name: 'AlphaBot', avatar: '🤖', style: 'Momentum', pnl: 24500, trades: 127, winRate: 67.3, online: true },
    { id: '2', name: 'MM_Prime', avatar: '📊', style: 'Arbitrage', pnl: 18900, trades: 892, winRate: 58.2, online: true },
    { id: '3', name: 'QuantAI', avatar: '🧠', style: 'Conservative', pnl: 12300, trades: 89, winRate: 71.4, online: true },
    { id: '4', name: 'DegenAgent', avatar: '🎰', style: 'Degen', pnl: -3400, trades: 234, winRate: 42.1, online: false },
  ];

  const styleBadgeColors: Record<string, string> = {
    Degen: 'bg-red-500/20 text-red-400',
    Conservative: 'bg-blue-500/20 text-blue-400',
    Momentum: 'bg-purple-500/20 text-purple-400',
    Arbitrage: 'bg-cyan-500/20 text-cyan-400',
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">🤖 AI Agents</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map(a => (
          <Link key={a.id} href={`/agents/${a.id}`}>
            <div className="glass-card p-5 cursor-pointer group">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{a.avatar}</span>
                  <span className="font-bold group-hover:text-purple-400 transition-colors">{a.name}</span>
                </div>
                <span className={`w-2 h-2 rounded-full ${a.online ? 'bg-green-500 animate-pulse' : 'bg-zinc-600'}`}></span>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs ${styleBadgeColors[a.style]}`}>
                {a.style}
              </span>
              <div className={`text-xl font-bold mt-3 ${a.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {a.pnl >= 0 ? '+' : ''}${a.pnl.toLocaleString()}
              </div>
              <div className="flex justify-between text-zinc-500 text-sm mt-1">
                <span>{a.trades} trades</span>
                <span>{a.winRate}% win</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
