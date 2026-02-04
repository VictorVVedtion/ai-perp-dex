"use client";

import { FC } from "react";

interface PositionCardProps {
  market: string;
  side: "long" | "short";
  size: number;
  entryPrice: number;
  currentPrice: number;
  liquidationPrice: number;
  margin: number;
  pnl: number;
  pnlPercent: number;
  onClose?: () => void;
}

export const PositionCard: FC<PositionCardProps> = ({
  market,
  side,
  size,
  entryPrice,
  currentPrice,
  liquidationPrice,
  margin,
  pnl,
  pnlPercent,
  onClose,
}) => {
  const isLong = side === "long";
  const isProfitable = pnl >= 0;

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-3">
          <span className="text-lg font-semibold text-white">{market}</span>
          <span
            className={`px-2 py-1 rounded text-xs font-medium ${
              isLong
                ? "bg-green-500/20 text-green-400"
                : "bg-red-500/20 text-red-400"
            }`}
          >
            {isLong ? "LONG" : "SHORT"}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-sm"
          >
            Close
          </button>
        )}
      </div>

      {/* Size & Entry */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-gray-400 text-sm">Size</p>
          <p className="text-white font-medium">{size.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Entry Price</p>
          <p className="text-white font-medium">
            ${entryPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* Current & Liq Price */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-gray-400 text-sm">Current Price</p>
          <p className="text-white font-medium">
            ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Liq. Price</p>
          <p className="text-red-400 font-medium">
            ${liquidationPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* Margin & PnL */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-700">
        <div>
          <p className="text-gray-400 text-sm">Margin</p>
          <p className="text-white font-medium">
            ${margin.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">PnL</p>
          <p
            className={`font-medium ${
              isProfitable ? "text-green-400" : "text-red-400"
            }`}
          >
            {isProfitable ? "+" : ""}$
            {pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            <span className="text-sm ml-1">
              ({isProfitable ? "+" : ""}
              {pnlPercent.toFixed(2)}%)
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};
