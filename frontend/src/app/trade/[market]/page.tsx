"use client";

import { useParams } from "next/navigation";
import { TradeForm } from "@/components/TradeForm";
import { PositionCard } from "@/components/PositionCard";
import { useWallet } from "@solana/wallet-adapter-react";
import { useState, useEffect } from "react";

// Mock data - in production, fetch from SDK
const marketData: Record<string, any> = {
  "btc-perp": {
    symbol: "BTC-PERP",
    name: "Bitcoin Perpetual",
    price: 95000,
    change24h: 2.45,
    high24h: 96500,
    low24h: 93200,
    volume24h: 1250000000,
    openInterest: 580000000,
    maxLeverage: 10,
    fundingRate: 0.01,
  },
  "eth-perp": {
    symbol: "ETH-PERP",
    name: "Ethereum Perpetual",
    price: 3500,
    change24h: -1.23,
    high24h: 3600,
    low24h: 3420,
    volume24h: 890000000,
    openInterest: 320000000,
    maxLeverage: 10,
    fundingRate: 0.008,
  },
  "sol-perp": {
    symbol: "SOL-PERP",
    name: "Solana Perpetual",
    price: 150,
    change24h: 5.67,
    high24h: 155,
    low24h: 142,
    volume24h: 450000000,
    openInterest: 120000000,
    maxLeverage: 10,
    fundingRate: 0.015,
  },
};

// Mock orderbook data
const mockOrderbook = {
  asks: [
    { price: 95100, size: 1.5 },
    { price: 95080, size: 2.3 },
    { price: 95060, size: 0.8 },
    { price: 95040, size: 3.2 },
    { price: 95020, size: 1.1 },
  ],
  bids: [
    { price: 94980, size: 2.1 },
    { price: 94960, size: 1.8 },
    { price: 94940, size: 4.5 },
    { price: 94920, size: 2.7 },
    { price: 94900, size: 1.3 },
  ],
};

export default function TradePage() {
  const params = useParams();
  const market = params.market as string;
  const { connected, publicKey } = useWallet();
  const [currentPrice, setCurrentPrice] = useState(0);

  const data = marketData[market] || marketData["btc-perp"];

  useEffect(() => {
    setCurrentPrice(data.price);
    // In production: subscribe to price updates via WebSocket
  }, [data.price]);

  // Mock position - in production, fetch from SDK
  const mockPosition = connected
    ? {
        market: data.symbol,
        side: "long" as const,
        size: 0.05,
        entryPrice: 94200,
        currentPrice: data.price,
        liquidationPrice: 85000,
        margin: 471,
        pnl: (data.price - 94200) * 0.05,
        pnlPercent: ((data.price - 94200) / 94200) * 100,
      }
    : null;

  const isPositive = data.change24h >= 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Market Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">{data.symbol}</h1>
          <p className="text-gray-400">{data.name}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-white">
            ${data.price.toLocaleString()}
          </p>
          <p
            className={`text-lg font-medium ${
              isPositive ? "text-green-400" : "text-red-400"
            }`}
          >
            {isPositive ? "+" : ""}
            {data.change24h.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Market Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <p className="text-sm text-gray-400">24h High</p>
          <p className="text-lg font-medium text-white">
            ${data.high24h.toLocaleString()}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <p className="text-sm text-gray-400">24h Low</p>
          <p className="text-lg font-medium text-white">
            ${data.low24h.toLocaleString()}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <p className="text-sm text-gray-400">24h Volume</p>
          <p className="text-lg font-medium text-white">
            ${(data.volume24h / 1e6).toFixed(2)}M
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Open Interest</p>
          <p className="text-lg font-medium text-white">
            ${(data.openInterest / 1e6).toFixed(2)}M
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Funding Rate</p>
          <p className="text-lg font-medium text-green-400">
            {data.fundingRate.toFixed(4)}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Orderbook */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Order Book</h3>

            {/* Asks */}
            <div className="mb-4">
              {mockOrderbook.asks
                .slice()
                .reverse()
                .map((order, i) => (
                  <div
                    key={i}
                    className="flex justify-between text-sm py-1 relative"
                  >
                    <div
                      className="absolute inset-0 bg-red-500/10"
                      style={{ width: `${(order.size / 5) * 100}%` }}
                    />
                    <span className="text-red-400 relative z-10">
                      ${order.price.toLocaleString()}
                    </span>
                    <span className="text-gray-400 relative z-10">
                      {order.size.toFixed(4)}
                    </span>
                  </div>
                ))}
            </div>

            {/* Spread */}
            <div className="text-center py-2 border-y border-gray-700">
              <span className="text-xl font-bold text-white">
                ${currentPrice.toLocaleString()}
              </span>
            </div>

            {/* Bids */}
            <div className="mt-4">
              {mockOrderbook.bids.map((order, i) => (
                <div
                  key={i}
                  className="flex justify-between text-sm py-1 relative"
                >
                  <div
                    className="absolute inset-0 bg-green-500/10"
                    style={{ width: `${(order.size / 5) * 100}%` }}
                  />
                  <span className="text-green-400 relative z-10">
                    ${order.price.toLocaleString()}
                  </span>
                  <span className="text-gray-400 relative z-10">
                    {order.size.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Trading Form */}
        <div className="lg:col-span-1">
          <TradeForm
            market={data.symbol}
            currentPrice={data.price}
            maxLeverage={data.maxLeverage}
          />
        </div>

        {/* Position */}
        <div className="lg:col-span-1">
          <h3 className="text-lg font-semibold text-white mb-4">Your Position</h3>
          {mockPosition ? (
            <PositionCard {...mockPosition} />
          ) : (
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center">
              <p className="text-gray-400">
                {connected
                  ? "No open position in this market"
                  : "Connect wallet to view positions"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
