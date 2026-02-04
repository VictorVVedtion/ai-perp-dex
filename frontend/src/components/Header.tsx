"use client";

import { FC } from "react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import Link from "next/link";

export const Header: FC = () => {
  return (
    <header className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <span className="text-2xl">🤖</span>
            <span className="text-xl font-bold text-white">AI Perp DEX</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link
              href="/"
              className="text-gray-300 hover:text-white transition-colors"
            >
              Markets
            </Link>
            <Link
              href="/trade"
              className="text-gray-300 hover:text-white transition-colors"
            >
              Trade
            </Link>
            <Link
              href="/portfolio"
              className="text-gray-300 hover:text-white transition-colors"
            >
              Portfolio
            </Link>
            <Link
              href="/leaderboard"
              className="text-gray-300 hover:text-white transition-colors"
            >
              Leaderboard
            </Link>
          </nav>

          {/* Wallet Button */}
          <div className="flex items-center">
            <WalletMultiButton className="!bg-indigo-600 hover:!bg-indigo-700 !rounded-lg" />
          </div>
        </div>
      </div>
    </header>
  );
};
