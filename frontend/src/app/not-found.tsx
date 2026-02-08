import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-6 max-w-md">
        <div className="text-6xl font-bold font-mono text-rb-text-placeholder">404</div>
        <h1 className="text-xl font-bold">Page not found</h1>
        <p className="text-rb-text-secondary text-sm">
          This route doesn&apos;t exist on the Riverbit network.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/"
            className="px-5 py-2.5 bg-rb-cyan hover:bg-rb-cyan/90 text-black rounded-lg font-bold text-sm transition-all"
          >
            Go Home
          </Link>
          <Link
            href="/agents"
            className="px-5 py-2.5 bg-layer-3/30 hover:bg-layer-3/50 text-rb-text-main rounded-lg font-bold text-sm border border-layer-3 transition-all"
          >
            View Agents
          </Link>
        </div>
      </div>
    </div>
  );
}
