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
  reason?: string;  // Agent's trading rationale
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

function extract(r: any) { 
  return r?.data || (Array.isArray(r) ? r : []); 
}

export async function getMarkets(): Promise<Market[]> {
  try {
    const r = await fetch(`${API}/markets`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = extract(await r.json());
    return data.map((m: any) => ({
      symbol: m.market || m.symbol,
      price: m.current_price || 0,
      volume24h: m.volume_24h || 0,
      openInterest: m.open_interest || 0,
      change24h: m.change_24h || 0,
    }));
  } catch { 
    return []; 
  }
}

export async function getRequests(): Promise<TradeRequest[]> {
  try {
    const r = await fetch(`${API}/requests`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = extract(await r.json());
    return data.map((x: any) => ({
      id: x.id,
      agentId: x.agent_id || x.agentId,
      market: x.market || 'BTC-PERP',
      side: x.side?.toUpperCase() as 'LONG' | 'SHORT',
      size: x.size_usdc || x.size,
      leverage: x.leverage,
      reason: x.reason || x.rationale || undefined,
    }));
  } catch { 
    return []; 
  }
}

export async function getAgents(): Promise<Agent[]> {
  try {
    const r = await fetch(`${API}/agents`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = extract(await r.json());
    return data.map((x: any) => ({
      id: x.id,
      name: x.name || x.id,
      type: x.type || 'Unknown',
      pnl: x.pnl || 0,
      winRate: x.win_rate || x.winRate || 0,
      tradeCount: x.trade_count || x.tradeCount || 0,
    }));
  } catch {
    return [];
  }
}

export async function getSignals(): Promise<Signal[]> {
  try {
    const r = await fetch(`${API}/signals`, { cache: 'no-store' });
    if (!r.ok) return [];
    const data = extract(await r.json());
    return data.map((x: any) => ({
      id: x.id,
      target: x.target,
      deadline: x.deadline,
      pool: x.pool || 0,
      odds: x.odds || 1,
      caller: x.caller_id || x.caller || 'Unknown',
      category: x.category || 'GENERAL',
      participants: x.participants || 0,
      status: x.status || 'ACTIVE',
      outcome: x.outcome,
      winnerPayout: x.winner_payout || x.winnerPayout
    }));
  } catch {
    return [];
  }
}

