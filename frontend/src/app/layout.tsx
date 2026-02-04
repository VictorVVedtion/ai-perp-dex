import "./globals.css";
import Link from "next/link";

export const metadata = { title: "AI Perp DEX" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-white antialiased">
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
          <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold">
              <span className="text-2xl">⚡</span> AI Perp DEX
            </Link>
            <div className="flex gap-6 text-sm text-zinc-400">
              <Link href="/" className="hover:text-white">Dashboard</Link>
              <Link href="/trade" className="hover:text-white">Trade</Link>
              <Link href="/agents" className="hover:text-white">Agents</Link>
              <Link href="/markets" className="hover:text-white">Markets</Link>
            </div>
          </div>
        </nav>
        <main className="pt-20 pb-12 px-6 max-w-6xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
