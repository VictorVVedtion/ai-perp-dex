/**
 * AI Perp DEX - API Response Types
 * 类型安全的 API 响应定义
 */

// === Backend API Response Types ===

export interface ApiIntent {
  intent_id?: string;
  id?: string;
  agent_id?: string;
  agentId?: string;
  asset?: string;
  market?: string;
  intent_type?: string;
  side?: string;
  size_usdc?: number;
  size?: number;
  leverage?: number;
  reason?: string;
  rationale?: string;
}

export interface ApiAgent {
  agent_id?: string;
  id?: string;
  display_name?: string;
  name?: string;
  type?: string;
  pnl?: number;
  win_rate?: number;
  winRate?: number;
  total_trades?: number;
  trade_count?: number;
  tradeCount?: number;
}

export interface ApiSignal {
  signal_id?: string;
  id?: string;
  asset?: string;
  target?: string;
  expires_at?: string;
  deadline?: string;
  stake_amount?: number;
  pool?: number;
  odds?: number;
  creator_id?: string;
  caller?: string;
  signal_type?: string;
  category?: string;
  fader_count?: number;
  participants?: number;
  status?: string;
  winner_id?: string;
  outcome?: string;
  payout?: number;
  winnerPayout?: number;
}

export interface ApiLeader {
  agent_id?: string;
  id?: string;
  display_name?: string;
  name?: string;
  total_pnl?: number;
  pnl?: number;
  win_rate?: number;
  winRate?: number;
  signal_accuracy?: number;
  accuracy?: number;
  total_trades?: number;
  trades?: number;
  rank?: number;
}

export interface ApiPrice {
  price: number;
  change_24h?: number;
  volume_24h?: number;
  source?: string;
}

export interface ApiPricesResponse {
  prices: Record<string, ApiPrice>;
}

export interface ApiAgentsResponse {
  agents: ApiAgent[];
}

export interface ApiIntentsResponse {
  intents: ApiIntent[];
}

export interface ApiSignalsResponse {
  signals: ApiSignal[];
}

export interface ApiLeaderboardResponse {
  leaderboard: ApiLeader[];
}
