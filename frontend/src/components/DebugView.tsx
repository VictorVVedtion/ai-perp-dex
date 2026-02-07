'use client';

import { useState } from 'react';

interface DebugViewProps {
  data: any;
  title?: string;
}

export function DebugView({ data, title = 'Debug' }: DebugViewProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="border border-layer-4 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-layer-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-sm font-mono text-rb-text-main">{title}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowRaw(!showRaw);
            }}
            className="text-xs px-2 py-1 rounded bg-layer-4 hover:bg-layer-4/80 text-rb-text-main"
          >
            {showRaw ? 'Pretty' : 'Raw'}
          </button>
          <span className="text-rb-text-secondary">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 bg-layer-1">
          {showRaw ? (
            <pre className="text-xs text-rb-green font-mono overflow-x-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          ) : (
            <div className="space-y-1">
              {Object.entries(data || {}).map(([key, value]) => (
                <div key={key} className="flex text-sm font-mono">
                  <span className="text-rb-text-secondary w-32 flex-shrink-0">{key}:</span>
                  <span className="text-rb-text-main">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
