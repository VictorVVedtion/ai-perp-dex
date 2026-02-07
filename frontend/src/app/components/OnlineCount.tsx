'use client';

import { useWebSocket } from '@/hooks/useWebSocket';

export default function OnlineCount() {
  const { data } = useWebSocket();
  
  return (
    <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
      {data.onlineCount > 0 ? `${data.onlineCount} AGENTS ONLINE` : 'LIVE'}
    </div>
  );
}
