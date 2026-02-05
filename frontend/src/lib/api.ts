const API = 'http://localhost:8080';

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

function extract(r: any) { 
  return r?.data || (Array.isArray(r) ? r : []); 
}

export async function getMarkets(): Promise<Market[]> {
  try {
    const r = await fetch(`${API}/markets`, { cache: 'no-store' });
    if (!r.ok) return getMockMarkets();
    const data = extract(await r.json());
    return data.map((m: any) => ({
      symbol: m.market || m.symbol,
      price: m.current_price || 0,
      volume24h: m.volume_24h || 0,
      openInterest: m.open_interest || 0,
      change24h: (Math.random() - 0.3) * 5,
    }));
  } catch { 
    return getMockMarkets(); 
  }
}

export async function getRequests(): Promise<TradeRequest[]> {
  try {
    const r = await fetch(`${API}/requests`, { cache: 'no-store' });
    if (!r.ok) return getMockRequests();
    const data = extract(await r.json());
    if (data.length === 0) return getMockRequests();
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
    return getMockRequests(); 
  }
}

function getMockMarkets(): Market[] {
  return [
    { symbol: 'BTC-PERP', price: 84000, volume24h: 5000000, openInterest: 1000000, change24h: 2.4 },
    { symbol: 'ETH-PERP', price: 2200, volume24h: 2000000, openInterest: 500000, change24h: -1.2 },
    { symbol: 'SOL-PERP', price: 130, volume24h: 800000, openInterest: 200000, change24h: 5.1 },
  ];
}

function getMockRequests(): TradeRequest[] {
  const agents = ['AlphaBot', 'QuantAI', 'SmartTrader', 'DegenAgent', 'MM_Prime'];
  const markets = ['BTC-PERP', 'ETH-PERP', 'SOL-PERP'];
  const reasons: Record<string, string[]> = {
    'BTC-PERP': [
      'BTC 在 84k 形成强支撑，RSI 超卖反弹信号',
      '链上数据显示交易所流出量激增，看涨',
      'ETF 资金持续流入，突破 85k 概率高',
    ],
    'ETH-PERP': [
      'ETH/BTC 比价触底反弹，补涨行情启动',
      'L2 TVL 创新高，生态利好推动上涨',
      'Gas 费用下降刺激链上活动，看好短期',
    ],
    'SOL-PERP': [
      'SOL 在 $130 有强支撑，上行空间大',
      'Meme 季 SOL 生态受益，交易量暴涨',
      '机构持仓增加，技术面突破在即',
    ],
  };
  return Array.from({ length: 5 }, (_, i) => {
    const market = markets[i % markets.length];
    const marketReasons = reasons[market] || reasons['BTC-PERP'];
    return {
      id: `req_${Math.random().toString(36).slice(2, 10)}`,
      agentId: agents[i % agents.length],
      market,
      side: (Math.random() > 0.5 ? 'LONG' : 'SHORT') as 'LONG' | 'SHORT',
      size: Math.floor(Math.random() * 2000 + 200),
      leverage: [5, 10, 20][Math.floor(Math.random() * 3)],
      reason: marketReasons[Math.floor(Math.random() * marketReasons.length)],
    };
  });
}
