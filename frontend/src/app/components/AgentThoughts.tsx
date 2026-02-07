'use client';

import { TradeRequest } from '@/lib/api';
import { Bot, MessageCircle, Brain } from 'lucide-react';

interface AgentThoughtsProps {
  requests: TradeRequest[];
  maxItems?: number;
}

export default function AgentThoughts({ requests, maxItems = 10 }: AgentThoughtsProps) {
  const requestsWithReasons = requests.filter(r => r.reason);

  if (requestsWithReasons.length === 0) {
    return (
      <div className="glass-card p-6">
        <h2 className="text-xl font-semibold flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-purple-400" /> Agent Thoughts
        </h2>
        <div className="text-center text-zinc-500 py-4">
          No agent reasoning available yet...
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="p-4 border-b border-white/5">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" /> Agent Thoughts
          <span className="text-sm font-normal text-zinc-500">
            ({requestsWithReasons.length})
          </span>
        </h2>
      </div>
      
      <div className="divide-y divide-white/5 max-h-[400px] overflow-y-auto">
        {requestsWithReasons.slice(0, maxItems).map((r) => (
          <div
            key={r.id}
            className="p-4 hover:bg-white/5 transition animate-in fade-in slide-in-from-top-2 duration-300"
          >
            {/* Agent & Trade Info */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-sm">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <span className="font-mono text-sm text-zinc-400">[{r.agentId}]</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`font-semibold ${r.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                  {r.side}
                </span>
                <span className="text-zinc-300">{r.market}</span>
                <span className="font-bold">${r.size.toLocaleString()}</span>
              </div>
            </div>

            {/* Thought Bubble */}
            <div className="relative mt-2 ml-10">
              <div className="absolute -left-6 top-0 opacity-50">
                <MessageCircle className="w-4 h-4 text-zinc-500" />
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/50">
                <p className="text-sm text-zinc-300 italic">
                  "{r.reason}"
                </p>
              </div>
            </div>

            {/* Leverage Badge */}
            <div className="mt-2 ml-10">
              <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400">
                {r.leverage}x leverage
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
