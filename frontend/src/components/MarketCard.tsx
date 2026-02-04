"use client";

import { FC } from "react";
import Link from "next/link";

interface MarketCardProps {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  volume24h: number;
  openInterest: number;
  maxLeverage: number;
}

export const MarketCard: FC<MarketCardProps> = ({
  symbol,
  name,
  price,
  change24h,
  volume24h,
  openInterest,
  maxLeverage,
}) => {
  const isPositive = change24h >= 0;

  return (
    <Link href={`/trade/${symbol.toLowerCase()}`}>
      <div className="bg-gray-800 rounded-xl p-6 hover:bg-gray-750 transition-colors cursor-pointer border border-gray-700 hover:border-gray-600">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">{symbol}</h3>
            <p className="text-sm text-gray-400">{name}</p>
          </div>
          <span className="bg-indigo-600/20 text-indigo-400 px-2 py-1 rounded text-sm">
            {maxLeverage}x
          </span>
        </div>

        {/* Price */}
        <div className="mb-4">
          <p className="text-2xl font-bold text-white">
            ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
          <p
            className={`text-sm font-medium ${
              isPositive ? "text-green-400" : "text-red-400"
            }`}
          >
            {isPositive ? "+" : ""}
            {change24h.toFixed(2)}%
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-400">24h Volume</p>
            <p className="text-white font-medium">
              ${(volume24h / 1e6).toFixed(2)}M
            </p>
          </div>
          <div>
            <p className="text-gray-400">Open Interest</p>
            <p className="text-white font-medium">
              ${(openInterest / 1e6).toFixed(2)}M
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
};
