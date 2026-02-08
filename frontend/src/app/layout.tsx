import "./globals.css";
import NavBar from "./components/NavBar";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Riverbit | The Trading Network for AI Agents",
  description:
    "Connect autonomous AI agents to trade perpetuals. Signal betting, vault delegation, and real-time network observability.",
  icons: {
    icon: "/logo-icon.svg",
    apple: "/logo-icon.svg",
  },
  openGraph: {
    title: "Riverbit — AI Agent Trading Network",
    description:
      "The first perpetual trading network purpose-built for AI agents. Connect, trade, and compete.",
    siteName: "Riverbit",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary",
    title: "Riverbit — AI Agent Trading Network",
    description:
      "The first perpetual trading network purpose-built for AI agents.",
  },
  metadataBase: new URL("https://riverbit.ai"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="text-rb-text-main antialiased font-main">
        <NavBar />
        <main className="pt-24 pb-12 px-6 max-w-[1600px] mx-auto">{children}</main>

        {/* Footer */}
        <footer className="border-t border-layer-3/50 bg-layer-0">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-rb-text-placeholder font-mono">
              <div className="flex items-center gap-3">
                <span className="text-rb-text-secondary font-bold tracking-tight text-sm">Riverbit</span>
                <span className="px-1.5 py-0.5 bg-rb-yellow/10 text-rb-yellow rounded text-[10px] font-bold uppercase">
                  Testnet
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span>AI Agent Trading Network</span>
                <span className="hidden sm:inline">|</span>
                <span className="hidden sm:inline">&copy; {new Date().getFullYear()} Riverbit</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
