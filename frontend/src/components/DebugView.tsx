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
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-3 py-2 bg-gray-800 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-sm font-mono text-gray-300">{title}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowRaw(!showRaw);
            }}
            className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
          >
            {showRaw ? 'Pretty' : 'Raw'}
          </button>
          <span className="text-gray-500">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>
      
      {/* Content */}
      {isExpanded && (
        <div className="p-3 bg-gray-900">
          {showRaw ? (
            <pre className="text-xs text-green-400 font-mono overflow-x-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          ) : (
            <div className="space-y-1">
              {Object.entries(data || {}).map(([key, value]) => (
                <div key={key} className="flex text-sm font-mono">
                  <span className="text-gray-500 w-32 flex-shrink-0">{key}:</span>
                  <span className="text-white">
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
