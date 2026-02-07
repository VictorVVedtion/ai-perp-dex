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
    online: 'bg-rb-green',
    offline: 'bg-rb-red',
    error: 'bg-rb-yellow',
    checking: 'bg-layer-4',
  }[stats.status] || 'bg-layer-4';

  return (
    <div className="flex items-center gap-4 text-xs font-mono px-4 py-2 bg-layer-1 border-t border-layer-3">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
        <span className="text-rb-text-secondary">API: {stats.status}</span>
      </div>
      <span className="text-rb-text-placeholder">|</span>
      <span className="text-rb-text-secondary">Latency: {stats.latency}ms</span>
      <span className="text-rb-text-placeholder">|</span>
      <span className="text-rb-text-placeholder">
        Last check: {stats.lastUpdate.toLocaleTimeString()}
      </span>
    </div>
  );
}
