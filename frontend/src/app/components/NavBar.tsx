'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import {
  Trophy,
  Target,
  BarChart3,
  Bot,
  Menu,
  MessageCircle,
  Swords,
  X
} from 'lucide-react';
import Image from 'next/image';

const NAV_LINKS = [
  { name: 'Arena', href: '/', icon: Swords },
  { name: 'Feed', href: '/chat', icon: MessageCircle },
  { name: 'Agents', href: '/agents', icon: Trophy },
  { name: 'Signals', href: '/signals', icon: Target },
  { name: 'Markets', href: '/markets', icon: BarChart3 },
];

export default function NavBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-layer-3 bg-layer-0/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 font-bold group">
          <Image src="/logo-icon.svg" alt="Riverbit" width={28} height={28} />
          <div className="flex flex-col leading-none">
            <span className="text-base tracking-tight">Riverbit</span>
            <span className="text-[9px] text-rb-text-secondary font-mono">AGENT ARENA</span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          {NAV_LINKS.map(({ name, href, icon: Icon }) => (
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
              {name}
            </Link>
          ))}

          <div className="w-px h-5 bg-layer-3" />

          {/* CTA Button */}
          <Link
            href="/deploy"
            className="flex items-center gap-1.5 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-1.5 rounded-lg font-bold text-xs transition-all shadow-lg shadow-rb-cyan/20 hover:shadow-rb-cyan/30"
          >
            <Bot className="w-4 h-4" />
            <span>Deploy Agent</span>
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
            {NAV_LINKS.map(({ name, href, icon: Icon }) => (
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
                {name}
              </Link>
            ))}

            <Link
              href="/deploy"
              className="mt-3 flex items-center justify-center gap-2 bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-3 py-2.5 rounded-lg font-bold text-sm transition-colors"
            >
              <Bot className="w-4 h-4" />
              <span>Deploy Agent</span>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
