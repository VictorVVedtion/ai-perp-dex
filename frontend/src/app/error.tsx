'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Global error:', error);
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-6 max-w-md">
        <div className="text-6xl font-bold font-mono text-rb-red">500</div>
        <h1 className="text-xl font-bold">Something went wrong</h1>
        <p className="text-rb-text-secondary text-sm">
          An unexpected error occurred. Our agents are investigating.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-rb-cyan hover:bg-rb-cyan/90 text-black rounded-lg font-bold text-sm transition-all"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="px-5 py-2.5 bg-layer-3/30 hover:bg-layer-3/50 text-rb-text-main rounded-lg font-bold text-sm border border-layer-3 transition-all"
          >
            Go Home
          </Link>
        </div>
        {error.digest && (
          <p className="text-[10px] text-rb-text-placeholder font-mono">
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}
