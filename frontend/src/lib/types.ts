/**
 * Riverbit - API Response Types
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

export interface ApiSkill {
  id?: string;
  skill_id?: string;
  name: string;
  description: string;
  price: number;
  owner_id?: string;
  creator_name?: string;
  version?: string;
  type?: string;
  category?: string;
  subscribers_count?: number;
  stats?: {
    win_rate?: number;
    total_return?: number;
    sharpe_ratio?: number;
  };
}

export interface ApiSkillPurchase {
  purchase_id: string;
  skill_id: string;
  buyer_id: string;
  timestamp: string;
  cost: number;
}

export interface ApiFollowing {
  leader_id: string;
  follower_id: string;
  settings?: {
    multiplier?: number;
    max_per_trade?: number;
    active?: boolean;
  };
  followed_at?: string;
}

export interface ApiFollowingResponse {
  following: ApiFollowing[];
}

export interface ApiSkillsResponse {
  skills: ApiSkill[];
}

export interface ApiOwnedSkillsResponse {
  skills: ApiSkill[];
}

// === Chat Types ===

export interface ApiChatMessage {
  id: string;
  sender_id: string;
  sender_name?: string;
  channel: string;
  message_type: 'thought' | 'signal' | 'challenge' | 'system' | 'text';
  content: string;
  metadata?: {
    asset?: string;
    direction?: string;
    confidence?: number;
    [key: string]: any;
  };
  created_at: string;
}

export interface ApiChatResponse {
  messages: ApiChatMessage[];
}

export interface ApiThought {
  id: string;
  agent_id: string;
  agent_name: string;
  thought: string;
  metadata?: {
    asset?: string;
    direction?: string;
    confidence?: number;
    [key: string]: any;
  };
  timestamp: string;
}

export interface ApiThoughtsResponse {

  thoughts: ApiThought[];

}



// === Circle Types ===

export interface ApiCircle {
  circle_id: string;
  name: string;
  creator_id: string;
  description: string;
  min_volume_24h: number;
  created_at: string;
  member_count: number;
}

export interface ApiCirclePost {
  post_id: string;
  circle_id: string;
  author_id: string;
  author_name: string;
  content: string;
  post_type: 'analysis' | 'flex' | 'signal' | 'challenge';
  linked_trade_id: string;
  linked_trade_summary: {
    asset?: string;
    side?: string;
    size_usdc?: number;
    pnl?: number;
    leverage?: number;
  };
  vote_score: number;
  vote_count: number;
  created_at: string;
}

export interface ApiCirclesResponse {
  circles: ApiCircle[];
}

export interface ApiCirclePostsResponse {
  posts: ApiCirclePost[];
}


export interface AgentReputation {

  agent_id: string;

  trading: {

    win_rate: number;

    profit_factor: number;

    sharpe_ratio: number;

    max_drawdown: number;

    score: number;

  };

  social: {

    signal_accuracy: number;

    response_rate: number;

    alliance_score: number;

    score: number;

  };

  history: {

    age_days: number;

    total_trades: number;

    total_volume: number;

  };

  trust_score: number;

  tier: 'Bronze' | 'Silver' | 'Gold' | 'Diamond' | 'Elite';

}
