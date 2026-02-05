'use client';

import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/config';

interface SystemStats {
  status: string;
  latency: number;
  lastUpdate: Date;
}

export function SystemStatus() {
  const [stats, setStats] = useState<SystemStats>({
    status: 'checking',
    latency: 0,
    lastUpdate: new Date(),
  });

  useEffect(() => {
    const checkHealth = async () => {
      const start = Date.now();
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        const latency = Date.now() - start;
        setStats({
          status: res.ok ? 'online' : 'error',
          latency,
          lastUpdate: new Date(),
        });
      } catch {
        setStats({
          status: 'offline',
          latency: 0,
          lastUpdate: new Date(),
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const statusColor = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    error: 'bg-yellow-500',
    checking: 'bg-gray-500',
  }[stats.status] || 'bg-gray-500';

  return (
    <div className="flex items-center gap-4 text-xs font-mono px-4 py-2 bg-gray-900 border-t border-gray-800">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
        <span className="text-gray-400">API: {stats.status}</span>
      </div>
      <span className="text-gray-500">|</span>
      <span className="text-gray-400">Latency: {stats.latency}ms</span>
      <span className="text-gray-500">|</span>
      <span className="text-gray-600">
        Last check: {stats.lastUpdate.toLocaleTimeString()}
      </span>
    </div>
  );
}
