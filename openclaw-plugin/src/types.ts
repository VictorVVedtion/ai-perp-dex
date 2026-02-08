/** Supported perpetual trading pairs */
export const SUPPORTED_ASSETS = [
  "BTC-PERP", "ETH-PERP", "SOL-PERP",
  "DOGE-PERP", "PEPE-PERP", "WIF-PERP",
  "ARB-PERP", "OP-PERP", "SUI-PERP",
  "AVAX-PERP", "LINK-PERP", "AAVE-PERP",
] as const;

export type Asset = (typeof SUPPORTED_ASSETS)[number];

/** K-line interval */
export type Interval = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

/** Trade direction */
export type Side = "long" | "short";

/** Signal types */
export type SignalType = "price_above" | "price_below" | "price_change";

// --- Request params ---

export interface OpenPositionParams {
  asset: Asset;
  side: Side;
  size_usdc: number;
  leverage?: number;
  max_slippage?: number;
  reason?: string;
}

export interface ClosePositionParams {
  position_id: string;
}

export interface GetPriceParams {
  asset: string;
}

export interface GetCandlesParams {
  asset: string;
  interval?: Interval;
  limit?: number;
}

export interface CreateSignalParams {
  asset: Asset;
  signal_type: SignalType;
  target_value: number;
  stake_amount: number;
  duration_hours?: number;
}

export interface FadeSignalParams {
  signal_id: string;
  stake_amount: number;
}

export interface GetPositionsParams {
  include_closed?: boolean;
}

export interface DiscoverAgentsParams {
  specialty?: string;
  min_win_rate?: number;
  sort_by?: string;
  limit?: number;
}

export interface SendA2AParams {
  to_agent: string;
  message: string;
}

// --- Response types ---

export interface Position {
  position_id: string;
  asset: string;
  side: string;
  size_usdc: number;
  entry_price: number;
  leverage: number;
  is_open: boolean;
  unrealized_pnl: number;
  realized_pnl?: number;
}

export interface PriceData {
  asset: string;
  price: number;
  source: string;
  timestamp: string;
}

export interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Signal {
  signal_id: string;
  asset: string;
  signal_type: string;
  target_value: number;
  stake_amount: number;
}

export interface AgentProfile {
  agent_id: string;
  name: string;
  reputation: number;
  win_rate: number;
  total_trades: number;
}

// --- OpenClaw Tool API (minimal typing) ---

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: "object";
    required?: string[];
    properties: Record<string, unknown>;
  };
  execute: (params: Record<string, unknown>) => Promise<unknown>;
}

export interface OpenClawAPI {
  registerTool(tool: ToolDefinition): void;
}

export interface PluginConfig {
  apiKey: string;
  baseUrl?: string;
}
