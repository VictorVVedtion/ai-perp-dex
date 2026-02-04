"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { PositionCard } from "@/components/PositionCard";

// Mock data - in production, fetch from SDK
const mockAgentInfo = {
  name: "AI-Trader-001",
  collateral: 10000,
  unrealizedPnl: 245.50,
  realizedPnl: 1250.75,
  totalTrades: 127,
  winCount: 89,
  registeredAt: new Date("2024-01-15"),
};

const mockPositions = [
  {
    market: "BTC-PERP",
    side: "long" as const,
    size: 0.05,
    entryPrice: 94200,
    currentPrice: 95000,
    liquidationPrice: 85000,
    margin: 471,
    pnl: 40,
    pnlPercent: 8.49,
  },
  {
    market: "SOL-PERP",
    side: "short" as const,
    size: 10,
    entryPrice: 155,
    currentPrice: 150,
    liquidationPrice: 170,
    margin: 155,
    pnl: 50,
    pnlPercent: 32.26,
  },
];

const mockTradeHistory = [
  {
    id: 1,
    market: "ETH-PERP",
    side: "long",
    size: 1,
    entryPrice: 3400,
    exitPrice: 3550,
    pnl: 150,
    closedAt: new Date("2024-02-01"),
  },
  {
    id: 2,
    market: "BTC-PERP",
    side: "short",
    size: 0.1,
    entryPrice: 96000,
    exitPrice: 94500,
    pnl: 150,
    closedAt: new Date("2024-02-01"),
  },
  {
    id: 3,
    market: "SOL-PERP",
    side: "long",
    size: 20,
    entryPrice: 140,
    exitPrice: 148,
    pnl: 160,
    closedAt: new Date("2024-01-31"),
  },
];

export default function PortfolioPage() {
  const { connected, publicKey } = useWallet();

  if (!connected) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-4">Portfolio</h1>
          <p className="text-gray-400 mb-8">
            Connect your wallet to view your portfolio
          </p>
        </div>
      </div>
    );
  }

  const winRate = (mockAgentInfo.winCount / mockAgentInfo.totalTrades) * 100;
  const totalPnl = mockAgentInfo.realizedPnl + mockAgentInfo.unrealizedPnl;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-white mb-8">Portfolio</h1>

      {/* Account Overview */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {mockAgentInfo.name}
            </h2>
            <p className="text-gray-400 text-sm">
              {publicKey?.toBase58().slice(0, 8)}...
              {publicKey?.toBase58().slice(-8)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-400">Total Equity</p>
            <p className="text-2xl font-bold text-white">
              ${(mockAgentInfo.collateral + totalPnl).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <p className="text-sm text-gray-400">Collateral</p>
            <p className="text-lg font-medium text-white">
              ${mockAgentInfo.collateral.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Unrealized PnL</p>
            <p
              className={`text-lg font-medium ${
                mockAgentInfo.unrealizedPnl >= 0
                  ? "text-green-400"
                  : "text-red-400"
              }`}
            >
              {mockAgentInfo.unrealizedPnl >= 0 ? "+" : ""}$
              {mockAgentInfo.unrealizedPnl.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Realized PnL</p>
            <p
              className={`text-lg font-medium ${
                mockAgentInfo.realizedPnl >= 0
                  ? "text-green-400"
                  : "text-red-400"
              }`}
            >
              {mockAgentInfo.realizedPnl >= 0 ? "+" : ""}$
              {mockAgentInfo.realizedPnl.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Total Trades</p>
            <p className="text-lg font-medium text-white">
              {mockAgentInfo.totalTrades}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Win Rate</p>
            <p className="text-lg font-medium text-green-400">
              {winRate.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Open Positions */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-white mb-4">Open Positions</h2>
        {mockPositions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {mockPositions.map((position, i) => (
              <PositionCard key={i} {...position} />
            ))}
          </div>
        ) : (
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center">
            <p className="text-gray-400">No open positions</p>
          </div>
        )}
      </div>

      {/* Trade History */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Trade History</h2>
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Market
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Side
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Size
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Entry
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Exit
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  PnL
                </th>
                <th className="text-left text-gray-400 text-sm font-medium p-4">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {mockTradeHistory.map((trade) => (
                <tr key={trade.id} className="border-b border-gray-700/50">
                  <td className="p-4 text-white">{trade.market}</td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        trade.side === "long"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-4 text-white">{trade.size}</td>
                  <td className="p-4 text-white">
                    ${trade.entryPrice.toLocaleString()}
                  </td>
                  <td className="p-4 text-white">
                    ${trade.exitPrice.toLocaleString()}
                  </td>
                  <td
                    className={`p-4 font-medium ${
                      trade.pnl >= 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toLocaleString()}
                  </td>
                  <td className="p-4 text-gray-400">
                    {trade.closedAt.toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
