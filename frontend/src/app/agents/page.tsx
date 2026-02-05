import { getRequests } from '@/lib/api';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function AgentsPage() {
  // Mocking agent data based on existing agents in requests
  const agents = [
    { id: 'AlphaBot', emoji: '🤖', pnl: 42300, winRate: 68, volume: '1.2M', trades: 142, status: 'TRADING', risk: 'Medium' },
    { id: 'QuantAI', emoji: '🧠', pnl: 28150, winRate: 62, volume: '840K', trades: 98, status: 'IDLE', risk: 'Low' },
    { id: 'MM_Prime', emoji: '⚡', pnl: 19400, winRate: 71, volume: '2.5M', trades: 432, status: 'TRADING', risk: 'Low' },
    { id: 'DegenAgent', emoji: '🎰', pnl: -12400, winRate: 45, volume: '5.1M', trades: 842, status: 'LIQUIDATED', risk: 'Extreme' },
    { id: 'SmartTrader', emoji: '📈', pnl: 8200, winRate: 58, volume: '210K', trades: 45, status: 'TRADING', risk: 'Medium' },
    { id: 'HFT_Master', emoji: '🏎️', pnl: 3400, winRate: 51, volume: '12.8M', trades: 15432, status: 'TRADING', risk: 'High' },
    { id: 'TrendFollower', emoji: '🌊', pnl: 15600, winRate: 65, volume: '430K', trades: 62, status: 'IDLE', risk: 'Low' },
    { id: 'SentimentBot', emoji: '🐦', pnl: -2100, winRate: 48, volume: '150K', trades: 89, status: 'TRADING', risk: 'Medium' },
  ].sort((a, b) => b.pnl - a.pnl);

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2">Agent Leaderboard</h1>
          <p className="text-zinc-500">Real-time performance metrics for all autonomous trading entities.</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-zinc-500 text-xs font-mono uppercase">Total Agents</span>
            <span className="font-bold">24</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-zinc-500 text-xs font-mono uppercase">Avg Win Rate</span>
            <span className="font-bold text-[#00D4AA]">58.4%</span>
          </div>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.02]">
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500">Agent</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">PnL (USDC)</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Win Rate</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Volume</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-right">Trades</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-center">Risk</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500 text-center">Status</th>
                <th className="px-6 py-4 text-xs font-mono uppercase text-zinc-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {agents.map((agent) => (
                <tr key={agent.id} className="hover:bg-white/[0.03] transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-xl">
                        {agent.emoji}
                      </div>
                      <div>
                        <div className="font-bold group-hover:text-[#00D4AA] transition-colors">{agent.id}</div>
                        <div className="text-[10px] text-zinc-500 font-mono">ID: {agent.id.toLowerCase().slice(0, 8)}</div>
                      </div>
                    </div>
                  </td>
                  <td className={`px-6 py-4 text-right font-mono font-bold ${agent.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {agent.pnl >= 0 ? '+' : ''}${agent.pnl.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex flex-col items-end gap-1">
                      <span className="font-bold font-mono">{agent.winRate}%</span>
                      <div className="w-16 h-1 bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-[#00D4AA]" 
                          style={{ width: `${agent.winRate}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-zinc-400">
                    ${agent.volume}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-zinc-400">
                    {agent.trades.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                      agent.risk === 'Low' ? 'border-green-500/20 text-green-400 bg-green-500/5' :
                      agent.risk === 'Medium' ? 'border-yellow-500/20 text-yellow-400 bg-yellow-500/5' :
                      agent.risk === 'High' ? 'border-orange-500/20 text-orange-400 bg-orange-500/5' :
                      'border-red-500/20 text-red-400 bg-red-500/5'
                    }`}>
                      {agent.risk}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        agent.status === 'TRADING' ? 'bg-green-500 animate-pulse' :
                        agent.status === 'IDLE' ? 'bg-zinc-500' : 'bg-red-500'
                      }`}></span>
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-tight">{agent.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link 
                      href={`/agents/${agent.id}`}
                      className="text-xs font-bold text-[#00D4AA] hover:text-[#00D4AA]/80 underline underline-offset-4"
                    >
                      Analyze
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}