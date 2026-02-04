"use client";

import { FC, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";

interface TradeFormProps {
  market: string;
  currentPrice: number;
  maxLeverage: number;
  onSubmit?: (trade: TradeParams) => void;
}

interface TradeParams {
  side: "long" | "short";
  size: number;
  leverage: number;
  orderType: "market" | "limit";
  limitPrice?: number;
}

export const TradeForm: FC<TradeFormProps> = ({
  market,
  currentPrice,
  maxLeverage,
  onSubmit,
}) => {
  const { connected } = useWallet();
  const [side, setSide] = useState<"long" | "short">("long");
  const [size, setSize] = useState("");
  const [leverage, setLeverage] = useState(5);
  const [orderType, setOrderType] = useState<"market" | "limit">("market");
  const [limitPrice, setLimitPrice] = useState("");

  const sizeNum = parseFloat(size) || 0;
  const notionalValue = sizeNum * currentPrice;
  const requiredMargin = notionalValue / leverage;
  const fee = notionalValue * 0.001; // 0.1% fee

  const handleSubmit = () => {
    if (!connected) return;

    const trade: TradeParams = {
      side,
      size: sizeNum,
      leverage,
      orderType,
      limitPrice: orderType === "limit" ? parseFloat(limitPrice) : undefined,
    };

    onSubmit?.(trade);
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">Open Position</h3>

      {/* Side Toggle */}
      <div className="grid grid-cols-2 gap-2 mb-6">
        <button
          onClick={() => setSide("long")}
          className={`py-3 rounded-lg font-medium transition-colors ${
            side === "long"
              ? "bg-green-500 text-white"
              : "bg-gray-700 text-gray-400 hover:text-white"
          }`}
        >
          Long
        </button>
        <button
          onClick={() => setSide("short")}
          className={`py-3 rounded-lg font-medium transition-colors ${
            side === "short"
              ? "bg-red-500 text-white"
              : "bg-gray-700 text-gray-400 hover:text-white"
          }`}
        >
          Short
        </button>
      </div>

      {/* Order Type */}
      <div className="mb-4">
        <label className="text-sm text-gray-400 mb-2 block">Order Type</label>
        <div className="flex space-x-2">
          <button
            onClick={() => setOrderType("market")}
            className={`flex-1 py-2 rounded-lg text-sm ${
              orderType === "market"
                ? "bg-indigo-600 text-white"
                : "bg-gray-700 text-gray-400"
            }`}
          >
            Market
          </button>
          <button
            onClick={() => setOrderType("limit")}
            className={`flex-1 py-2 rounded-lg text-sm ${
              orderType === "limit"
                ? "bg-indigo-600 text-white"
                : "bg-gray-700 text-gray-400"
            }`}
          >
            Limit
          </button>
        </div>
      </div>

      {/* Size Input */}
      <div className="mb-4">
        <label className="text-sm text-gray-400 mb-2 block">Size ({market.split("-")[0]})</label>
        <input
          type="number"
          value={size}
          onChange={(e) => setSize(e.target.value)}
          placeholder="0.00"
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Limit Price (if limit order) */}
      {orderType === "limit" && (
        <div className="mb-4">
          <label className="text-sm text-gray-400 mb-2 block">Limit Price (USD)</label>
          <input
            type="number"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            placeholder={currentPrice.toString()}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
          />
        </div>
      )}

      {/* Leverage Slider */}
      <div className="mb-6">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">Leverage</span>
          <span className="text-white font-medium">{leverage}x</span>
        </div>
        <input
          type="range"
          min={1}
          max={maxLeverage}
          value={leverage}
          onChange={(e) => setLeverage(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1x</span>
          <span>{maxLeverage}x</span>
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-gray-900 rounded-lg p-4 mb-6">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Entry Price</span>
            <span className="text-white">
              ${orderType === "market" ? currentPrice.toLocaleString() : (parseFloat(limitPrice) || currentPrice).toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Notional Value</span>
            <span className="text-white">${notionalValue.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Required Margin</span>
            <span className="text-white">${requiredMargin.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Fee (0.1%)</span>
            <span className="text-white">${fee.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!connected || sizeNum <= 0}
        className={`w-full py-4 rounded-lg font-medium transition-colors ${
          side === "long"
            ? "bg-green-500 hover:bg-green-600"
            : "bg-red-500 hover:bg-red-600"
        } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {!connected
          ? "Connect Wallet"
          : sizeNum <= 0
          ? "Enter Size"
          : `${side === "long" ? "Long" : "Short"} ${market}`}
      </button>
    </div>
  );
};
