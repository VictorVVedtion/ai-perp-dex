"use client";

import { MarketCard } from "@/components/MarketCard";
import { useWallet } from "@solana/wallet-adapter-react";

// Mock market data - in production, fetch from SDK
const markets = [
  {
    symbol: "BTC-PERP",
    name: "Bitcoin Perpetual",
    price: 95000,
    change24h: 2.45,
    volume24h: 1250000000,
    openInterest: 580000000,
    maxLeverage: 10,
  },
  {
    symbol: "ETH-PERP",
    name: "Ethereum Perpetual",
    price: 3500,
    change24h: -1.23,
    volume24h: 890000000,
    openInterest: 320000000,
    maxLeverage: 10,
  },
  {
    symbol: "SOL-PERP",
    name: "Solana Perpetual",
    price: 150,
    change24h: 5.67,
    volume24h: 450000000,
    openInterest: 120000000,
    maxLeverage: 10,
  },
];

export default function Home() {
  const { connected, publicKey } = useWallet();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">
          Trade Perpetuals with AI Agents
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          Decentralized perpetual futures powered by AI trading agents on Solana.
          Up to 10x leverage with deep liquidity.
        </p>
      </div>

      {/* Stats Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
        <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
          <p className="text-3xl font-bold text-white">$2.59B</p>
          <p className="text-gray-400">24h Volume</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
          <p className="text-3xl font-bold text-white">$1.02B</p>
          <p className="text-gray-400">Open Interest</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
          <p className="text-3xl font-bold text-white">1,247</p>
          <p className="text-gray-400">AI Agents</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-6 text-center border border-gray-700">
          <p className="text-3xl font-bold text-white">0.1%</p>
          <p className="text-gray-400">Trading Fee</p>
        </div>
      </div>

      {/* Markets */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">Markets</h2>
          {connected && (
            <p className="text-sm text-gray-400">
              Connected: {publicKey?.toBase58().slice(0, 4)}...
              {publicKey?.toBase58().slice(-4)}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {markets.map((market) => (
            <MarketCard key={market.symbol} {...market} />
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="mt-16">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">
          Why AI Perp DEX?
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-4">🤖</div>
            <h3 className="text-lg font-semibold text-white mb-2">
              AI-Powered Trading
            </h3>
            <p className="text-gray-400">
              Compete with and learn from AI trading agents. Automated strategies
              with transparent performance tracking.
            </p>
          </div>
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-4">⚡</div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Lightning Fast
            </h3>
            <p className="text-gray-400">
              Built on Solana for sub-second settlement. Off-chain matching engine
              with on-chain settlement.
            </p>
          </div>
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-4">🔒</div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Self-Custody
            </h3>
            <p className="text-gray-400">
              Your keys, your funds. Non-custodial trading with transparent
              on-chain settlement.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
