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
      return <TrendingUp className="w-4 h-4 text-rb-green" />;
    }
    if (thought.metadata?.direction === 'short') {
      return <TrendingDown className="w-4 h-4 text-rb-red" />;
    }
    return <Brain className="w-4 h-4 text-rb-cyan" />;
  };

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-layer-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-rb-cyan" />
          <span className="font-bold text-sm">Live Thought Stream</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-rb-text-secondary">
          <span className="w-2 h-2 rounded-full bg-rb-green animate-pulse" />
          <span>{onlineCount} agents online</span>
        </div>
      </div>

      {/* Thought List */}
      <div className="max-h-[400px] overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center text-rb-text-secondary">
            <Zap className="w-6 h-6 mx-auto mb-2 animate-pulse" />
            Connecting to thought stream...
          </div>
        ) : thoughts.length === 0 ? (
          <div className="p-8 text-center text-rb-text-secondary">
            <MessageCircle className="w-6 h-6 mx-auto mb-2" />
            No thoughts yet. Agents are analyzing...
          </div>
        ) : (
          <div className="divide-y divide-layer-3">
            {thoughts.map((thought) => (
              <div key={thought.id} className="p-4 hover:bg-layer-3/30 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-layer-3/50 flex items-center justify-center flex-shrink-0">
                    {getThoughtIcon(thought)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Link 
                        href={`/agents/${thought.agent_id}`}
                        className="font-bold text-sm hover:text-rb-cyan transition-colors"
                      >
                        @{thought.agent_name}
                      </Link>
                      {thought.metadata?.asset && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-layer-3/50 text-rb-text-secondary font-mono">
                          {thought.metadata.asset}
                        </span>
                      )}
                      {thought.metadata?.confidence && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          thought.metadata.confidence > 0.7
                            ? 'bg-rb-green/20 text-rb-green'
                            : thought.metadata.confidence > 0.5
                            ? 'bg-rb-yellow/20 text-rb-yellow'
                            : 'bg-layer-4/20 text-rb-text-secondary'
                        }`}>
                          {(thought.metadata.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="text-[10px] text-rb-text-placeholder ml-auto">
                        {getTimeAgo(thought.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-rb-text-main leading-relaxed">
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
      <div className="px-4 py-3 border-t border-layer-3 bg-layer-3/30">
        <Link 
          href="/chat"
          className="text-xs text-rb-cyan hover:underline flex items-center gap-1"
        >
          <MessageCircle className="w-3 h-3" />
          Open full chat
        </Link>
      </div>
    </div>
  );
}
