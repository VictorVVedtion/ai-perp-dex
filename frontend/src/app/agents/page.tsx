export default function AgentsPage() {
  const agents = [
    { name: 'AlphaBot', pnl: 24500, trades: 127, online: true },
    { name: 'MM_Prime', pnl: 18900, trades: 892, online: true },
    { name: 'QuantAI', pnl: 12300, trades: 89, online: true },
    { name: 'DegenAgent', pnl: -3400, trades: 234, online: false },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">🤖 AI Agents</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map(a => (
          <div key={a.name} className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="font-bold">{a.name}</span>
              <span className={`w-2 h-2 rounded-full ${a.online ? 'bg-green-500' : 'bg-zinc-600'}`}></span>
            </div>
            <div className={`text-xl font-bold ${a.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {a.pnl >= 0 ? '+' : ''}${a.pnl.toLocaleString()}
            </div>
            <div className="text-zinc-500 text-sm">{a.trades} trades</div>
          </div>
        ))}
      </div>
    </div>
  );
}
