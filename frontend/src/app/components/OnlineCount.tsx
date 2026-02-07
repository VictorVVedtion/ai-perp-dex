'use client';

import { useWebSocket } from '@/hooks/useWebSocket';

export default function OnlineCount() {
  const { data } = useWebSocket();
  
  return (
    <div className="flex items-center gap-2 text-[10px] font-mono text-rb-text-secondary">
      <span className="w-2 h-2 rounded-full bg-rb-green animate-pulse"></span>
      {data.onlineCount > 0 ? `${data.onlineCount} AGENTS ONLINE` : 'LIVE'}
    </div>
  );
}
