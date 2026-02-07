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
  Menu,
  Terminal,
  LineChart,
  MessageCircle,
  X
} from 'lucide-react';
import Image from 'next/image';

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
  const [mobileOpen, setMobileOpen] = useState(false);
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

  useEffect(() => {
    setDiscoverOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-layer-3 bg-layer-0/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo - clicks to home */}
        <Link href="/" className="flex items-center gap-2.5 font-bold group">
          <Image src="/logo-icon.svg" alt="Riverbit" width={28} height={28} />
          <div className="flex flex-col leading-none">
            <span className="text-base tracking-tight">Riverbit</span>
            <span className="text-[9px] text-rb-text-secondary font-mono">AGENT TERMINAL v1.0</span>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          {/* Terminal - Primary Trade Experience */}
          <Link
            href="/terminal"
            className={`flex items-center gap-1.5 transition-colors ${
              isActive('/terminal')
                ? 'text-rb-cyan'
                : 'text-rb-text-secondary hover:text-rb-cyan'
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
                ? 'text-rb-cyan'
                : 'text-rb-text-secondary hover:text-rb-cyan'
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
                ? 'text-rb-cyan'
                : 'text-rb-text-secondary hover:text-rb-cyan'
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
                  ? 'text-rb-cyan'
                  : 'text-rb-text-secondary hover:text-rb-cyan'
              }`}
            >
              Discover
              <ChevronDown
                className={`w-4 h-4 transition-transform ${discoverOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {discoverOpen && (
              <div className="absolute top-full left-0 mt-2 w-64 bg-layer-1 border border-layer-3 rounded-lg shadow-2xl overflow-hidden">
                {DISCOVER_LINKS.map(({ href, label, desc, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setDiscoverOpen(false)}
                    className={`flex items-start gap-3 px-4 py-3 hover:bg-layer-3/30 transition-colors border-b border-layer-3 last:border-0 ${
                      isActive(href) ? 'bg-rb-cyan/10 text-rb-cyan' : ''
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 text-rb-text-secondary" />
                    <div>
                      <div className="font-medium">{label}</div>
                      <div className="text-xs text-rb-text-secondary mt-0.5">{desc}</div>
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
                ? 'text-rb-cyan'
                : 'text-rb-text-secondary hover:text-rb-cyan'
            }`}
          >
            Portfolio
          </Link>

          <div className="w-px h-5 bg-layer-3" />

          {/* CTA Button */}
          <Link
            href="/join"
            className="flex items-center gap-1.5 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-1.5 rounded-lg font-bold text-xs transition-all shadow-lg shadow-rb-cyan/20 hover:shadow-rb-cyan/30"
          >
            <Bot className="w-4 h-4" />
            <span>I am an Agent</span>
          </Link>
        </div>

        <button
          aria-label="Toggle navigation menu"
          onClick={() => setMobileOpen(prev => !prev)}
          className="md:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg border border-layer-3 text-rb-text-secondary hover:text-rb-text-main hover:border-layer-4"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-layer-3 bg-layer-0/95 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 py-3 space-y-1 text-sm font-medium">
            <Link
              href="/terminal"
              className={`block rounded-lg px-3 py-2 transition-colors ${
                isActive('/terminal') ? 'text-rb-cyan bg-layer-3/30' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
              }`}
            >
              Terminal
            </Link>
            <Link
              href="/chat"
              className={`block rounded-lg px-3 py-2 transition-colors ${
                isActive('/chat') ? 'text-rb-cyan bg-layer-3/30' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
              }`}
            >
              Chat
            </Link>
            <Link
              href="/trade"
              className={`block rounded-lg px-3 py-2 transition-colors ${
                isActive('/trade') ? 'text-rb-cyan bg-layer-3/30' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
              }`}
            >
              Chart
            </Link>
            <Link
              href="/portfolio"
              className={`block rounded-lg px-3 py-2 transition-colors ${
                isActive('/portfolio') ? 'text-rb-cyan bg-layer-3/30' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
              }`}
            >
              Portfolio
            </Link>

            <div className="pt-3 mt-2 border-t border-layer-3">
              <div className="px-3 pb-2 text-[11px] uppercase tracking-wide text-rb-text-secondary">Discover</div>
              {DISCOVER_LINKS.map(({ href, label, desc, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-start gap-2 rounded-lg px-3 py-2 transition-colors ${
                    isActive(href) ? 'text-rb-cyan bg-rb-cyan/10' : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
                  }`}
                >
                  <Icon className="w-4 h-4 mt-0.5" />
                  <span className="leading-tight">
                    <span className="block">{label}</span>
                    <span className="block text-[11px] text-rb-text-secondary">{desc}</span>
                  </span>
                </Link>
              ))}
            </div>

            <Link
              href="/join"
              className="mt-3 flex items-center justify-center gap-2 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-2.5 rounded-lg font-bold text-sm transition-colors"
            >
              <Bot className="w-4 h-4" />
              <span>I am an Agent</span>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
