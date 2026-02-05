/**
 * AI Perp DEX Frontend Configuration
 * All environment-dependent values should be here
 */

// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8082';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8082/ws';

// Feature Flags
export const ENABLE_DEBUG_MODE = process.env.NEXT_PUBLIC_DEBUG === 'true';

// Trading Limits (client-side validation)
export const MAX_LEVERAGE = 20;
export const MIN_POSITION_SIZE = 1; // $1 USDC
export const MAX_POSITION_SIZE = 100000; // $100k USDC

// Supported Assets
export const SUPPORTED_ASSETS = [
  'BTC-PERP', 'ETH-PERP', 'SOL-PERP',
  'DOGE-PERP', 'PEPE-PERP', 'WIF-PERP',
  'ARB-PERP', 'OP-PERP', 'SUI-PERP',
  'AVAX-PERP', 'LINK-PERP', 'AAVE-PERP',
] as const;

export type SupportedAsset = typeof SUPPORTED_ASSETS[number];

// API Endpoints
export const ENDPOINTS = {
  health: `${API_BASE_URL}/health`,
  prices: `${API_BASE_URL}/prices`,
  agents: {
    register: `${API_BASE_URL}/agents/register`,
    list: `${API_BASE_URL}/agents`,
    get: (id: string) => `${API_BASE_URL}/agents/${id}`,
    positions: (id: string) => `${API_BASE_URL}/agents/${id}/positions`,
  },
  trading: {
    intent: `${API_BASE_URL}/intents`,
    closePosition: (id: string) => `${API_BASE_URL}/positions/${id}/close`,
  },
  signals: {
    create: `${API_BASE_URL}/signals`,
    fade: `${API_BASE_URL}/signals/fade`,
    list: `${API_BASE_URL}/signals`,
  },
  deposit: `${API_BASE_URL}/deposit`,
  withdraw: `${API_BASE_URL}/withdraw`,
  leaderboard: `${API_BASE_URL}/leaderboard`,
  stats: `${API_BASE_URL}/stats`,
} as const;
