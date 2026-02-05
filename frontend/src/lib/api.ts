const API = 'http://localhost:8082';

export interface Market { 
  symbol: string; 
  price: number; 
  volume24h: number; 
  openInterest: number; 
  change24h?: number;
}

export interface TradeRequest { 
  id: string; 
  agentId: string; 
  market: string;
  side: 'LONG' | 'SHORT'; 
  size: number; 
  leverage: number;
  reason?: string;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  pnl: number;
  winRate: number;
  tradeCount: number;
}

export interface Signal {
  id: string;
  target: string;
  deadline: string;
  pool: number;
  odds: number;
  caller: string;
  category: string;
  participants: number;
  status: 'ACTIVE' | 'SETTLED';
  outcome?: 'WIN' | 'LOSS';
  winnerPayout?: number;
}

// Fetch prices and convert to Market format
export async function getMarkets(): Promise<Market[]> {
  try {
    const r = await fetch(`${API}/prices`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    const prices = json.prices || json;
    
    // Convert prices object to Market array
    return Object.entries(prices).map(([asset, data]: [string, any]) => ({
      symbol: `${asset}-PERP`,
      price: data.price || 0,
      volume24h: data.volume_24h || 0,
      openInterest: 0, // Not in prices endpoint
      change24h: data.change_24h || 0,
    }));
  } catch (e) {
    console.error('getMarkets error:', e);
    return []; 
  }
}

// Fetch intents (trade requests)
export async function getRequests(): Promise<TradeRequest[]> {
  try {
    const r = await fetch(`${API}/intents`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    const intents = json.intents || json;
    
    if (!Array.isArray(intents)) return [];
    
    return intents.map((x: any) => ({
      id: x.intent_id || x.id,
      agentId: x.agent_id || x.agentId,
      market: x.asset || x.market || 'BTC-PERP',
      side: (x.intent_type || x.side || 'long').toUpperCase() as 'LONG' | 'SHORT',
      size: x.size_usdc || x.size || 0,
      leverage: x.leverage || 1,
      reason: x.reason || x.rationale || undefined,
    }));
  } catch (e) {
    console.error('getRequests error:', e);
    return []; 
  }
}

// Fetch agents
export async function getAgents(): Promise<Agent[]> {
  try {
    const r = await fetch(`${API}/agents`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    const agents = json.agents || json;
    
    if (!Array.isArray(agents)) return [];
    
    return agents.map((x: any) => ({
      id: x.agent_id || x.id,
      name: x.display_name || x.name || x.agent_id || 'Unknown',
      type: x.type || 'Trader',
      pnl: x.pnl || 0,
      winRate: x.win_rate || x.winRate || 0,
      tradeCount: x.total_trades || x.trade_count || x.tradeCount || 0,
    }));
  } catch (e) {
    console.error('getAgents error:', e);
    return [];
  }
}

// Fetch signals
export async function getSignals(): Promise<Signal[]> {
  try {
    const r = await fetch(`${API}/signals`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    const signals = json.signals || json;
    
    if (!Array.isArray(signals)) return [];
    
    return signals.map((x: any) => ({
      id: x.signal_id || x.id,
      target: x.target || x.prediction || 'Unknown target',
      deadline: x.deadline || x.expires_at || new Date().toISOString(),
      pool: x.pool || x.total_pool || 0,
      odds: x.odds || x.current_odds || 1,
      caller: x.caller_id || x.caller || x.agent_id || 'Unknown',
      category: x.category || x.signal_type || 'PRICE',
      participants: x.participants || x.fade_count || 0,
      status: (x.status || 'ACTIVE').toUpperCase() as 'ACTIVE' | 'SETTLED',
      outcome: x.outcome,
      winnerPayout: x.winner_payout || x.winnerPayout
    }));
  } catch (e) {
    console.error('getSignals error:', e);
    return [];
  }
}

// Fetch leaderboard
export async function getLeaderboard(): Promise<Agent[]> {
  try {
    const r = await fetch(`${API}/leaderboard`, { cache: 'no-store' });
    if (!r.ok) return getAgents(); // Fallback to agents
    const json = await r.json();
    const leaders = json.leaderboard || json;
    
    if (!Array.isArray(leaders)) return [];
    
    return leaders.map((x: any) => ({
      id: x.agent_id || x.id,
      name: x.display_name || x.name || x.agent_id || 'Unknown',
      type: x.type || 'Trader',
      pnl: x.pnl || x.total_pnl || 0,
      winRate: x.win_rate || 0,
      tradeCount: x.total_trades || 0,
    }));
  } catch (e) {
    console.error('getLeaderboard error:', e);
    return [];
  }
}

// Fetch thoughts feed
export async function getThoughts(): Promise<any[]> {
  try {
    const r = await fetch(`${API}/thoughts/feed`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    return json.thoughts || json || [];
  } catch (e) {
    console.error('getThoughts error:', e);
    return [];
  }
}
