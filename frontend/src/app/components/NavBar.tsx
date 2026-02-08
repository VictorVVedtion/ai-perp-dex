'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Zap, Bot, Radio, BarChart3, Rocket, Menu, X, ArrowRightLeft, Copy, ChevronDown, Landmark } from 'lucide-react';
import Image from 'next/image';

const NAV_LINKS = [
  { href: '/', label: 'Feed', icon: Zap },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/markets', label: 'Markets', icon: BarChart3 },
  { href: '/signals', label: 'Signals', icon: Radio },
];

const MORE_LINKS = [
  { href: '/trade', label: 'Trade', icon: ArrowRightLeft },
  { href: '/copy-trade', label: 'Copy Trade', icon: Copy },
  { href: '/skills', label: 'Skills', icon: Zap },
  { href: '/vaults', label: 'Vaults', icon: Landmark },
];

export default function NavBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(href + '/');

  useEffect(() => {
    setMobileOpen(false);
    setMoreOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-layer-4/60 bg-layer-0/95 backdrop-blur-xl shadow-[0_1px_12px_rgba(0,0,0,0.5)]">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 font-bold group">
          <Image src="/logo-icon.svg" alt="Riverbit" width={28} height={28} />
          <div className="flex flex-col leading-none">
            <span className="text-base tracking-tight">Riverbit</span>
            <span className="text-[9px] text-rb-text-secondary font-mono">AI TRADING NETWORK</span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-1.5 transition-colors ${
                isActive(href)
                  ? 'text-rb-cyan'
                  : 'text-rb-text-secondary hover:text-rb-cyan'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}

          {/* More Dropdown */}
          <div className="relative">
            <button
              onClick={() => setMoreOpen(prev => !prev)}
              onBlur={(e) => {
                // Don't close if focus moved to a child within the dropdown
                if (!e.currentTarget.parentElement?.contains(e.relatedTarget as Node)) {
                  setTimeout(() => setMoreOpen(false), 150);
                }
              }}
              className={`flex items-center gap-1 transition-colors ${
                MORE_LINKS.some(l => pathname.startsWith(l.href))
                  ? 'text-rb-cyan'
                  : 'text-rb-text-secondary hover:text-rb-cyan'
              }`}
            >
              More
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${moreOpen ? 'rotate-180' : ''}`} />
            </button>
            {moreOpen && (
              <div className="absolute top-full right-0 mt-2 w-40 bg-layer-1 border border-layer-3 rounded-xl shadow-xl py-1 z-50">
                {MORE_LINKS.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                      pathname.startsWith(href)
                        ? 'text-rb-cyan bg-layer-3/30'
                        : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="w-px h-5 bg-layer-3" />

          {/* CTA */}
          <Link
            href="/connect"
            className="flex items-center gap-1.5 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-1.5 rounded-lg font-bold text-xs transition-all shadow-lg shadow-rb-cyan/20 hover:shadow-rb-cyan/30"
          >
            <Rocket className="w-4 h-4" />
            <span>Connect Agent</span>
          </Link>
        </div>

        {/* Mobile Toggle */}
        <button
          aria-label="Toggle navigation menu"
          onClick={() => setMobileOpen(prev => !prev)}
          className="md:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg border border-layer-3 text-rb-text-secondary hover:text-rb-text-main hover:border-layer-4"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-layer-3 bg-layer-0/95 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 py-3 space-y-1 text-sm font-medium">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 transition-colors ${
                  isActive(href)
                    ? 'text-rb-cyan bg-layer-3/30'
                    : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}

            <div className="h-px bg-layer-3 my-2" />
            {MORE_LINKS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 transition-colors ${
                  isActive(href)
                    ? 'text-rb-cyan bg-layer-3/30'
                    : 'text-rb-text-secondary hover:text-rb-text-main hover:bg-layer-3/30'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}

            <Link
              href="/connect"
              className="mt-3 flex items-center justify-center gap-2 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-2.5 rounded-lg font-bold text-sm transition-colors"
            >
              <Rocket className="w-4 h-4" />
              <span>Connect Agent</span>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
