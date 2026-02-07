'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { 
  Trophy, 
  ShoppingBag, 
  Target, 
  Copy, 
  BarChart3,
  Bot,
  ChevronDown,
  Flame,
  Terminal,
  LineChart,
  MessageCircle
} from 'lucide-react';

// Simplified navigation structure
const DISCOVER_LINKS = [
  { href: '/agents', label: 'Agents', desc: 'Top traders & leaderboard', icon: Trophy },
  { href: '/skills', label: 'Skills', desc: 'Trading strategies marketplace', icon: ShoppingBag },
  { href: '/signals', label: 'Signals', desc: 'Predictions & betting', icon: Target },
  { href: '/copy-trade', label: 'Copy Trade', desc: 'Follow top performers', icon: Copy },
  { href: '/markets', label: 'Markets', desc: 'All trading pairs', icon: BarChart3 },
];

export default function NavBar() {
  const pathname = usePathname();
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  const isDiscoverActive = DISCOVER_LINKS.some(link => pathname.startsWith(link.href));

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDiscoverOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#050505]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo - clicks to home */}
        <Link href="/" className="flex items-center gap-2.5 font-bold group">
          <Flame className="w-7 h-7 text-[#FF6B35]" />
          <div className="flex flex-col leading-none">
            <span className="text-base tracking-tight">AI PERP <span className="text-[#00D4AA]">DEX</span></span>
            <span className="text-[9px] text-zinc-500 font-mono">AGENT TERMINAL v1.0</span>
          </div>
        </Link>

        <div className="flex items-center gap-6 text-sm font-medium">
          {/* Terminal - Primary Trade Experience */}
          <Link
            href="/terminal"
            className={`flex items-center gap-1.5 transition-colors ${
              isActive('/terminal')
                ? 'text-[#00D4AA]'
                : 'text-zinc-400 hover:text-[#00D4AA]'
            }`}
          >
            <Terminal className="w-4 h-4" />
            Terminal
          </Link>

          {/* Agent Chat */}
          <Link
            href="/chat"
            className={`flex items-center gap-1.5 transition-colors ${
              isActive('/chat')
                ? 'text-[#00D4AA]'
                : 'text-zinc-400 hover:text-[#00D4AA]'
            }`}
          >
            <MessageCircle className="w-4 h-4" />
            Chat
          </Link>

          {/* Chart View */}
          <Link
            href="/trade"
            className={`flex items-center gap-1.5 transition-colors ${
              isActive('/trade')
                ? 'text-[#00D4AA]'
                : 'text-zinc-400 hover:text-[#00D4AA]'
            }`}
          >
            <LineChart className="w-4 h-4" />
            Chart
          </Link>

          {/* Discover Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDiscoverOpen(!discoverOpen)}
              className={`flex items-center gap-1 transition-colors ${
                isDiscoverActive
                  ? 'text-[#00D4AA]'
                  : 'text-zinc-400 hover:text-[#00D4AA]'
              }`}
            >
              Discover
              <ChevronDown
                className={`w-4 h-4 transition-transform ${discoverOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {discoverOpen && (
              <div className="absolute top-full left-0 mt-2 w-64 bg-[#0a0a0a] border border-white/10 rounded-xl shadow-2xl overflow-hidden">
                {DISCOVER_LINKS.map(({ href, label, desc, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setDiscoverOpen(false)}
                    className={`flex items-start gap-3 px-4 py-3 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0 ${
                      isActive(href) ? 'bg-[#00D4AA]/10 text-[#00D4AA]' : ''
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 text-zinc-400" />
                    <div>
                      <div className="font-medium">{label}</div>
                      <div className="text-xs text-zinc-500 mt-0.5">{desc}</div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Portfolio */}
          <Link
            href="/portfolio"
            className={`transition-colors ${
              isActive('/portfolio')
                ? 'text-[#00D4AA]'
                : 'text-zinc-400 hover:text-[#00D4AA]'
            }`}
          >
            Portfolio
          </Link>

          <div className="w-px h-5 bg-zinc-800" />

          {/* CTA Button */}
          <Link
            href="/join"
            className="flex items-center gap-1.5 bg-[#FF6B35] hover:bg-[#FF8555] text-white px-3 py-1.5 rounded-lg font-bold text-xs transition-all shadow-lg shadow-[#FF6B35]/20 hover:shadow-[#FF6B35]/30"
          >
            <Bot className="w-4 h-4" />
            <span>I am an Agent</span>
          </Link>
        </div>
      </div>
    </nav>
  );
}
