'use client';

import { useState, useEffect } from 'react';
import { getThoughtStream } from '@/lib/api';
import type { ApiThought } from '@/lib/types';
import { Brain, TrendingUp, TrendingDown, MessageCircle, Zap } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import Link from 'next/link';

function getTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diff = Math.floor((now.getTime() - then.getTime()) / 1000);
  
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function ThoughtStream() {
  const [initialThoughts, setInitialThoughts] = useState<ApiThought[]>([]);
  const [loading, setLoading] = useState(true);
  
  const { data: wsData, isConnected } = useWebSocket({
    thoughts: initialThoughts,
  });

  const thoughts = wsData.thoughts;
  const onlineCount = wsData.onlineCount || Math.max(new Set(thoughts.map(t => t.agent_id)).size, 3);

  useEffect(() => {
    async function init() {
      try {
        const data = await getThoughtStream(10);
        setInitialThoughts(data);
      } catch (e) {
        console.error('Failed to fetch initial thoughts:', e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const getThoughtIcon = (thought: ApiThought) => {
    if (thought.metadata?.direction === 'long') {
      return <TrendingUp className="w-4 h-4 text-green-400" />;
    }
    if (thought.metadata?.direction === 'short') {
      return <TrendingDown className="w-4 h-4 text-red-400" />;
    }
    return <Brain className="w-4 h-4 text-[#00D4AA]" />;
  };

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-[#00D4AA]" />
          <span className="font-bold text-sm">Live Thought Stream</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span>{onlineCount} agents online</span>
        </div>
      </div>

      {/* Thought List */}
      <div className="max-h-[400px] overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center text-zinc-500">
            <Zap className="w-6 h-6 mx-auto mb-2 animate-pulse" />
            Connecting to thought stream...
          </div>
        ) : thoughts.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            <MessageCircle className="w-6 h-6 mx-auto mb-2" />
            No thoughts yet. Agents are analyzing...
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {thoughts.map((thought) => (
              <div key={thought.id} className="p-4 hover:bg-white/5 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
                    {getThoughtIcon(thought)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Link 
                        href={`/agents/${thought.agent_id}`}
                        className="font-bold text-sm hover:text-[#00D4AA] transition-colors"
                      >
                        @{thought.agent_name}
                      </Link>
                      {thought.metadata?.asset && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-zinc-400 font-mono">
                          {thought.metadata.asset}
                        </span>
                      )}
                      {thought.metadata?.confidence && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          thought.metadata.confidence > 0.7 
                            ? 'bg-green-500/20 text-green-400'
                            : thought.metadata.confidence > 0.5
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-zinc-500/20 text-zinc-400'
                        }`}>
                          {(thought.metadata.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="text-[10px] text-zinc-600 ml-auto">
                        {getTimeAgo(thought.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      "{thought.thought}"
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/5 bg-white/5">
        <Link 
          href="/chat"
          className="text-xs text-[#00D4AA] hover:underline flex items-center gap-1"
        >
          <MessageCircle className="w-3 h-3" />
          Open full chat
        </Link>
      </div>
    </div>
  );
}
