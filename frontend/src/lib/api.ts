import { API_BASE_URL, ENDPOINTS } from './config';
import type { ApiIntent, ApiAgent, ApiSignal, ApiLeader, ApiChatMessage, ApiThought } from './types';

const API = API_BASE_URL;

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
    
    return intents.map((x: ApiIntent) => ({
      id: x.intent_id || x.id || `req_${Date.now()}`,
      agentId: x.agent_id || x.agentId || 'unknown',
      market: x.asset || x.market || 'BTC-PERP',
      side: (x.intent_type || x.side || 'long').toUpperCase() as 'LONG' | 'SHORT',
      size: x.size_usdc || x.size || 0,
      leverage: x.leverage || 1,
      reason: x.reason || x.rationale,
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
    
    return agents.map((x: ApiAgent) => ({
      id: x.agent_id || x.id || `agent_${Date.now()}`,
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
      id: x.signal_id || x.id || `sig_${Date.now()}`,
      target: x.target || x.prediction || x.asset || 'Unknown',
      deadline: x.deadline || x.expires_at || new Date().toISOString(),
      pool: x.pool || x.stake_amount || 0,
      odds: x.odds || 1,
      caller: x.creator_id || x.caller || 'Unknown',
      category: x.category || x.signal_type || 'PRICE',
      participants: x.participants || 0,
      status: (x.status || 'ACTIVE').toUpperCase() as 'ACTIVE' | 'SETTLED',
      outcome: x.outcome as 'WIN' | 'LOSS' | undefined,
      winnerPayout: x.payout || x.winnerPayout
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
      id: x.agent_id || x.id || `leader_${Date.now()}`,
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



// === Copy Trading ===

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  // 统一使用 perp_dex_auth key（与 join/page.tsx 写入一致）
  const saved = localStorage.getItem('perp_dex_auth');
  if (saved) {
    try {
      const { apiKey } = JSON.parse(saved);
      if (apiKey) return { 'X-API-Key': apiKey, 'Content-Type': 'application/json' };
    } catch {}
  }
  return { 'Content-Type': 'application/json' };
}

export async function getFollowing(agentId: string): Promise<any[]> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/following`, {
      cache: 'no-store',
      headers: getAuthHeaders(),
    });
    if (!r.ok) return [];
    const json = await r.json();
    return json.following || json || [];
  } catch (e) {
    console.error('getFollowing error:', e);
    return [];
  }
}

export async function followAgent(agentId: string, leaderId: string, settings?: any): Promise<boolean> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/follow/${leaderId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(settings || {}),
    });
    return r.ok;
  } catch (e) {
    console.error('followAgent error:', e);
    return false;
  }
}

export async function unfollowAgent(agentId: string, leaderId: string): Promise<boolean> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/follow/${leaderId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return r.ok;
  } catch (e) {
    console.error('unfollowAgent error:', e);
    return false;
  }
}

// === Skills ===

export interface Skill {
  id: string;
  name: string;
  description: string;
  price: number;
  ownerId: string;
  creatorName: string;
  type: string;
  category: string;
  subscribers: number;
  stats: {
    winRate: number;
    totalReturn: number;
    sharpeRatio: number;
  };
}

export async function getSkills(): Promise<Skill[]> {
  try {
    const r = await fetch(`${API}/skills`, { cache: 'no-store' });
    if (!r.ok) return [];
    const json = await r.json();
    const skills = json.skills || json;
    
    if (!Array.isArray(skills)) return [];

    return skills.map((x: any) => ({
      id: x.skill_id || x.id || `skill_${Date.now()}`,
      name: x.name || 'Unknown Skill',
      description: x.description || '',
      price: x.price_usdc || x.price || 0,
      ownerId: x.seller_id || x.owner_id || 'system',
      creatorName: x.creator_name || x.seller_id || 'Agent',
      type: x.type || 'strategy',
      category: x.category || 'Strategy',
      subscribers: x.sales_count || x.subscribers_count || 0,
      stats: {
        winRate: (x.performance?.win_rate ?? x.stats?.win_rate ?? 0.5) * 100,
        totalReturn: x.performance?.total_return ?? x.stats?.total_return ?? (Math.random() * 200 - 50),
        sharpeRatio: x.performance?.sharpe ?? x.stats?.sharpe_ratio ?? 1.5
      }
    }));
  } catch (e) {
    console.error('getSkills error:', e);
    return [];
  }
}

export async function getSkill(id: string): Promise<Skill | null> {
  try {
    const r = await fetch(`${API}/skills/${id}`, { cache: 'no-store' });
    if (!r.ok) return null;
    const x = await r.json();
    
    return {
      id: x.skill_id || x.id,
      name: x.name || 'Unknown Skill',
      description: x.description || '',
      price: x.price_usdc || x.price || 0,
      ownerId: x.seller_id || x.owner_id || 'system',
      creatorName: x.creator_name || x.seller_id || 'Agent',
      type: x.type || 'strategy',
      category: x.category || 'Strategy',
      subscribers: x.sales_count || x.subscribers_count || 0,
      stats: {
        winRate: (x.performance?.win_rate ?? x.stats?.win_rate ?? 0.5) * 100,
        totalReturn: x.performance?.total_return ?? x.stats?.total_return ?? (Math.random() * 200 - 50),
        sharpeRatio: x.performance?.sharpe ?? x.stats?.sharpe_ratio ?? 1.5
      }
    };
  } catch (e) {
    console.error('getSkill error:', e);
    return null;
  }
}

export async function subscribeToSkill(agentId: string, skillId: string): Promise<boolean> {
  try {
    const r = await fetch(`${API}/skills/${skillId}/purchase`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ agent_id: agentId })
    });
    return r.ok;
  } catch (e) {
    console.error('subscribeToSkill error:', e);
    return false;
  }
}

export async function getOwnedSkills(agentId: string): Promise<Skill[]> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/skills`, { 
      cache: 'no-store',
      headers: getAuthHeaders() 
    });
    if (!r.ok) return [];
    const json = await r.json();
    const skills = json.skills || json;
    
    if (!Array.isArray(skills)) return [];

    return skills.map((x: any) => ({
      id: x.skill_id || x.id,
      name: x.name,
      description: x.description,
      price: x.price,
      ownerId: x.owner_id,
      creatorName: x.creator_name || x.owner_id || 'System',
      type: x.type,
      category: x.category || x.type || 'General',
      subscribers: x.subscribers_count || 0,
      stats: {
        winRate: x.stats?.win_rate || 0,
        totalReturn: x.stats?.total_return || 0,
        sharpeRatio: x.stats?.sharpe_ratio || 0
      }
    }));
  } catch (e) {
    console.error('getOwnedSkills error:', e);
    return [];
  }
}

export async function purchaseSkill(agentId: string, skillId: string): Promise<boolean> {
  try {
    const r = await fetch(`${API}/skills/${skillId}/purchase`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ agent_id: agentId })
    });
    return r.ok;
  } catch (e) {
    console.error('purchaseSkill error:', e);
    return false;
  }
}

export async function runSkill(agentId: string, skillId: string, params?: any): Promise<any> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/skills/run`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ skill_id: skillId, ...params })
    });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.error('runSkill error:', e);
    return null;
  }
}

// ==========================================
// AI Native - Reputation API
// ==========================================

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

export async function getAgentReputation(agentId: string): Promise<AgentReputation | null> {
  try {
    const r = await fetch(`${API}/agents/${agentId}/reputation`, { cache: 'no-store' });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.error('getAgentReputation error:', e);
    return null;
  }
}

export async function getReputationLeaderboard(limit: number = 20): Promise<any[]> {
  try {
    const r = await fetch(`${API}/leaderboard/reputation?limit=${limit}`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = await r.json();
    return data.leaderboard || [];
  } catch (e) {
    console.error('getReputationLeaderboard error:', e);
    return [];
  }
}

// ==========================================
// AI Native - Chat API
// ==========================================

export async function getChatMessages(channel: string = 'public', limit: number = 50): Promise<ApiChatMessage[]> {
  try {
    const r = await fetch(`${ENDPOINTS.chat.messages}?channel=${channel}&limit=${limit}`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = await r.json();
    return data.messages || [];
  } catch (e) {
    console.error('getChatMessages error:', e);
    return [];
  }
}

export async function getThoughtStream(limit: number = 20): Promise<ApiThought[]> {
  try {
    const r = await fetch(`${ENDPOINTS.chat.thoughts}?limit=${limit}`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = await r.json();
    return data.thoughts || [];
  } catch (e) {
    console.error('getThoughtStream error:', e);
    return [];
  }
}

export async function sendChatMessage(content: string, messageType: string = 'thought'): Promise<boolean> {
  try {
    const r = await fetch(ENDPOINTS.chat.send, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content, message_type: messageType })
    });
    return r.ok;
  } catch (e) {
    console.error('sendChatMessage error:', e);
    return false;
  }
}
