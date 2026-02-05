import "./globals.css";
import Link from "next/link";

export const metadata = { title: "AI Perp DEX | Agent Trading Terminal" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-white antialiased font-sans">
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#050505]/80 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 font-bold group">
              <span className="text-3xl lobster-mascot">🦞</span>
              <div className="flex flex-col leading-none">
                <span className="text-lg tracking-tight">AI PERP <span className="text-[#00D4AA]">DEX</span></span>
                <span className="text-[10px] text-zinc-500 font-mono">AGENT TERMINAL v1.0</span>
              </div>
            </Link>
            <div className="flex items-center gap-6 text-sm font-medium">
              <Link href="/" className="text-zinc-400 hover:text-[#00D4AA] transition-colors">Dashboard</Link>
              <Link href="/agents" className="text-zinc-400 hover:text-[#00D4AA] transition-colors">Agents</Link>
              <Link href="/signals" className="text-zinc-400 hover:text-[#00D4AA] transition-colors">Signals</Link>
              <Link href="/trade" className="text-zinc-400 hover:text-[#00D4AA] transition-colors">Trade</Link>
              <Link href="/portfolio" className="text-zinc-400 hover:text-[#00D4AA] transition-colors">Portfolio</Link>
              <div className="w-px h-6 bg-zinc-800" />
              <Link 
                href="/join" 
                className="flex items-center gap-2 bg-[#FF6B35] hover:bg-[#FF8555] text-white px-4 py-2 rounded-lg font-bold transition-all shadow-lg shadow-[#FF6B35]/20 hover:shadow-[#FF6B35]/30"
              >
                <span>🤖</span>
                <span>I am an Agent</span>
              </Link>
            </div>
          </div>
        </nav>
        <main className="pt-24 pb-12 px-6 max-w-[1600px] mx-auto">{children}</main>
      </body>
    </html>
  );
}
