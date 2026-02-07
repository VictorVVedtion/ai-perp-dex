/**
 * Price & number formatting utilities for AI Perp DEX frontend.
 *
 * Handles the full range: BTC ($64,325.50) to PEPE ($0.0000035).
 */

/**
 * Format a price for display.
 * - >= $1: comma-separated with 2 decimals ($64,325.50)
 * - $0.01 ~ $1: 4 decimals ($0.1234)
 * - < $0.01: show significant digits ($0.0000035)
 */
export function formatPrice(price: number): string {
  if (price === 0) return '$0.00';

  const abs = Math.abs(price);
  const sign = price < 0 ? '-' : '';

  if (abs >= 1) {
    return `${sign}$${abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  if (abs >= 0.01) {
    return `${sign}$${abs.toFixed(4)}`;
  }

  // Very small prices (meme coins): find first significant digit
  const str = abs.toFixed(20);
  const match = str.match(/^0\.(0*?)([1-9]\d{0,3})/);
  if (match) {
    const zeros = match[1].length;
    const significantDigits = match[2];
    return `${sign}$0.${'0'.repeat(zeros)}${significantDigits}`;
  }

  return `${sign}$${abs.toExponential(2)}`;
}

/**
 * Format USD amounts with K/M/B suffixes.
 * - < 1K: $123
 * - 1K ~ 1M: $12.3K
 * - 1M ~ 1B: $1.2M
 * - >= 1B: $1.5B
 */
export function formatUsd(amount: number): string {
  const abs = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';

  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

/**
 * Format PnL with +/- prefix.
 * Returns formatted string (no $ prefix needed, caller adds it).
 */
export function formatPnl(pnl: number): string {
  const prefix = pnl >= 0 ? '+' : '';
  return `${prefix}${formatPrice(pnl)}`;
}
