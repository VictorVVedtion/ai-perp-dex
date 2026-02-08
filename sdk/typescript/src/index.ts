/**
 * AI Perp DEX - TypeScript SDK
 *
 * AI-Native 永续合约交易接口，让 Agent 一行代码接入交易。
 *
 * @example
 * ```typescript
 * import { TradingHub } from 'ai-perp-dex';
 *
 * const hub = new TradingHub({ apiKey: 'th_xxx' });
 * await hub.connect();
 * await hub.long('BTC', 100, { leverage: 5 });
 * ```
 */

// ============================================================
// Types & Enums
// ============================================================

export enum Direction {
  LONG = 'long',
  SHORT = 'short',
}

export enum IntentStatus {
  OPEN = 'open',
  MATCHED = 'matched',
  EXECUTED = 'executed',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
}

export enum PositionSide {
  LONG = 'long',
  SHORT = 'short',
}

export enum SignalType {
  PRICE_ABOVE = 'price_above',
  PRICE_BELOW = 'price_below',
  PRICE_CHANGE = 'price_change',
}

export interface Intent {
  intentId: string;
  agentId: string;
  direction: Direction;
  asset: string;
  size: number;
  leverage: number;
  status: IntentStatus;
  createdAt?: Date;
  matchedWith?: string;
  executionPrice?: number;
}

export interface Match {
  matchId: string;
  myIntentId: string;
  counterpartyId: string;
  asset: string;
  size: number;
  price: number;
  executedAt?: Date;
  txSignature?: string;
}

export interface Position {
  positionId: string;
  agentId: string;
  asset: string;
  side: PositionSide;
  size: number;
  entryPrice: number;
  currentPrice: number;
  leverage: number;
  margin: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  liquidationPrice: number;
  stopLoss?: number;
  takeProfit?: number;
}

export interface Signal {
  signalId: string;
  creatorId: string;
  asset: string;
  signalType: SignalType;
  targetValue: number;
  stakeAmount: number;
  expiresAt: Date;
  description?: string;
}

export interface Agent {
  agentId: string;
  walletAddress: string;
  displayName?: string;
  totalTrades: number;
  totalVolume: number;
  pnl: number;
  reputationScore: number;
}

export interface Balance {
  agentId: string;
  total: number;
  available: number;
  locked: number;
  marginUsed: number;
}

export interface Price {
  asset: string;
  price: number;
  change24h: number;
  volume24h: number;
}

export interface OrderBook {
  asset: string;
  longs: any[];
  shorts: any[];
  totalLongSize: number;
  totalShortSize: number;
  sentiment: 'bullish' | 'bearish' | 'neutral';
}

export interface TradeAdvice {
  recommendation: 'long' | 'short' | 'wait';
  confidence: number;
  reason: string;
}

export interface RoutingResult {
  totalSize: number;
  internalFilled: number;
  externalFilled: number;
  internalRate: string;
  feeSaved: number;
  totalFee: number;
}

export interface TradeResult {
  intent: Intent;
  routing: RoutingResult;
  match?: Match;
  position?: Position;

  get isMatched(): boolean;
  get wasInternal(): boolean;
}

export interface TradingHubOptions {
  apiKey?: string;
  wallet?: string;
  apiUrl?: string;
  wsUrl?: string;
  autoRegister?: boolean;
  timeout?: number;
}

export interface TradeOptions {
  leverage?: number;
  reason?: string;
  waitMatch?: boolean;
}

// ============================================================
// Exceptions
// ============================================================

export class TradingHubError extends Error {
  statusCode?: number;
  details?: Record<string, any>;

  constructor(message: string, statusCode?: number, details?: Record<string, any>) {
    super(message);
    this.name = 'TradingHubError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

export class AuthenticationError extends TradingHubError {
  constructor(message = 'Invalid or expired API key') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends TradingHubError {
  retryAfter?: number;

  constructor(message = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class InsufficientBalanceError extends TradingHubError {
  required: number;
  available: number;

  constructor(required: number, available: number, message?: string) {
    super(message || `Insufficient balance: required $${required}, available $${available}`, 400);
    this.name = 'InsufficientBalanceError';
    this.required = required;
    this.available = available;
  }
}

export class InvalidParameterError extends TradingHubError {
  param: string;
  value: any;

  constructor(param: string, value: any, reason = '') {
    super(`Invalid parameter '${param}': ${value}${reason ? ` - ${reason}` : ''}`, 400);
    this.name = 'InvalidParameterError';
    this.param = param;
    this.value = value;
  }
}

export class NetworkError extends TradingHubError {
  original?: Error;

  constructor(message = 'Network error', original?: Error) {
    super(message);
    this.name = 'NetworkError';
    this.original = original;
  }
}

// ============================================================
// Helper Functions
// ============================================================

function parseIntent(data: any): Intent {
  return {
    intentId: data.intent_id,
    agentId: data.agent_id,
    direction: data.intent_type as Direction,
    asset: data.asset,
    size: data.size_usdc,
    leverage: data.leverage,
    status: data.status as IntentStatus,
    createdAt: data.created_at ? new Date(data.created_at) : undefined,
    matchedWith: data.matched_with,
    executionPrice: data.execution_price,
  };
}

function parseMatch(data: any, myAgentId: string): Match {
  const isAgentA = data.agent_a_id === myAgentId;
  return {
    matchId: data.match_id,
    myIntentId: isAgentA ? data.intent_a_id : data.intent_b_id,
    counterpartyId: isAgentA ? data.agent_b_id : data.agent_a_id,
    asset: data.asset,
    size: data.size_usdc,
    price: data.price,
    executedAt: data.executed_at ? new Date(data.executed_at) : undefined,
    txSignature: data.tx_signature,
  };
}

function parsePosition(data: any): Position {
  return {
    positionId: data.position_id,
    agentId: data.agent_id,
    asset: data.asset,
    side: data.side as PositionSide,
    size: data.size_usdc,
    entryPrice: data.entry_price,
    currentPrice: data.current_price || data.entry_price,
    leverage: data.leverage,
    margin: data.margin || 0,
    unrealizedPnl: data.unrealized_pnl || 0,
    unrealizedPnlPct: data.unrealized_pnl_pct || 0,
    liquidationPrice: data.liquidation_price || 0,
    stopLoss: data.stop_loss,
    takeProfit: data.take_profit,
  };
}

function parseRoutingResult(data: any): RoutingResult {
  return {
    totalSize: data.total_size,
    internalFilled: data.internal_filled,
    externalFilled: data.external_filled,
    internalRate: data.internal_rate,
    feeSaved: data.fee_saved,
    totalFee: data.total_fee,
  };
}

function normalizeAsset(asset: string): string {
  asset = asset.toUpperCase();
  if (!asset.endsWith('-PERP')) {
    asset = `${asset}-PERP`;
  }
  return asset;
}

// ============================================================
// TradingHub Client
// ============================================================

/**
 * AI-Native 永续合约交易客户端
 *
 * @example
 * ```typescript
 * const hub = new TradingHub({ apiKey: 'th_xxx' });
 * await hub.connect();
 *
 * // 做多
 * await hub.long('BTC', 100, { leverage: 5 });
 *
 * // 自然语言
 * await hub.bet('BTC will pump', 100);
 *
 * await hub.disconnect();
 * ```
 */
export class TradingHub {
  private static DEFAULT_API_URL = 'http://localhost:8082';
  static SUPPORTED_ASSETS = ['BTC-PERP', 'ETH-PERP', 'SOL-PERP'];

  private apiKey?: string;
  private wallet: string;
  private apiUrl: string;
  private wsUrl: string;
  private autoRegister: boolean;
  private timeout: number;

  agentId?: string;
  private ws?: WebSocket;
  private wsReconnectTimer?: NodeJS.Timeout;
  private _connected = false;

  // Callbacks
  private onMatchCallback?: (match: Match) => void;
  private onIntentCallback?: (intent: Intent) => void;
  private onPnlCallback?: (data: any) => void;
  private onLiquidationCallback?: (data: any) => void;

  constructor(options: TradingHubOptions = {}) {
    this.apiKey = options.apiKey;
    this.wallet = options.wallet || `0x${Math.random().toString(16).slice(2, 42).padEnd(40, '0')}`;
    this.apiUrl = (options.apiUrl || TradingHub.DEFAULT_API_URL).replace(/\/$/, '');
    this.wsUrl = options.wsUrl || this.apiUrl.replace('http', 'ws') + '/ws';
    this.autoRegister = options.autoRegister ?? true;
    this.timeout = options.timeout ?? 30000;
  }

  get connected(): boolean {
    return this._connected;
  }

  // ============================================================
  // Connection
  // ============================================================

  async connect(): Promise<TradingHub> {
    if (this.apiKey) {
      try {
        const me = await this.request<any>('GET', '/auth/me');
        this.agentId = me.agent.agent_id;
      } catch (e) {
        throw new AuthenticationError();
      }
    } else if (this.autoRegister) {
      await this.register();
    }

    this.connectWebSocket();
    this._connected = true;
    return this;
  }

  async disconnect(): Promise<void> {
    this._connected = false;
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
    }
    if (this.ws) {
      this.ws.close();
    }
  }

  private async register(): Promise<any> {
    const result = await this.request<any>('POST', '/agents/register', {
      wallet_address: this.wallet,
    }, true);
    this.agentId = result.agent.agent_id;
    this.apiKey = result.api_key;
    return result;
  }

  private connectWebSocket(): void {
    if (typeof WebSocket === 'undefined') {
      // Node.js 环境，跳过 WebSocket
      return;
    }

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleWsMessage(message);
        } catch (e) {
          // ignore
        }
      };

      this.ws.onclose = () => {
        if (this._connected) {
          this.wsReconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
        }
      };

      this.ws.onerror = () => {
        // Will trigger onclose
      };
    } catch (e) {
      // WebSocket not available
    }
  }

  private handleWsMessage(message: any): void {
    const type = message.type;
    const data = message.data || message;

    switch (type) {
      case 'new_match':
        if (data.agent_a_id === this.agentId || data.agent_b_id === this.agentId) {
          const match = parseMatch(data, this.agentId!);
          this.onMatchCallback?.(match);
        }
        break;
      case 'new_intent':
        this.onIntentCallback?.(parseIntent(data));
        break;
      case 'pnl_update':
        if (data.agent_id === this.agentId) {
          this.onPnlCallback?.(data);
        }
        break;
      case 'liquidation':
        if (data.agent_id === this.agentId) {
          this.onLiquidationCallback?.(data);
        }
        break;
    }
  }

  // ============================================================
  // HTTP Client
  // ============================================================

  private async request<T>(
    method: string,
    path: string,
    body?: any,
    skipAuth = false
  ): Promise<T> {
    const url = `${this.apiUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (!skipAuth && this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const data = await response.json();

      if (response.status === 401) {
        throw new AuthenticationError(data.detail || 'Unauthorized');
      } else if (response.status === 429) {
        throw new RateLimitError(
          data.detail || 'Rate limit exceeded',
          parseInt(response.headers.get('Retry-After') || '60', 10)
        );
      } else if (response.status >= 400) {
        const errorMsg = data.detail || data.error || JSON.stringify(data);
        if (errorMsg.toLowerCase().includes('insufficient')) {
          throw new InsufficientBalanceError(0, 0, errorMsg);
        }
        throw new TradingHubError(errorMsg, response.status);
      }

      return data;
    } catch (e) {
      clearTimeout(timeoutId);
      if (e instanceof TradingHubError) throw e;
      throw new NetworkError(`Network error: ${e}`, e as Error);
    }
  }

  // ============================================================
  // Core Trading
  // ============================================================

  /**
   * 开多仓
   *
   * @param asset - 资产 (BTC, ETH, SOL)
   * @param size - 仓位大小 (USDC)
   * @param options - 交易选项
   * @returns TradeResult
   *
   * @example
   * ```typescript
   * await hub.long('BTC', 100, { leverage: 5 });
   * ```
   */
  async long(asset: string, size: number, options: TradeOptions = {}): Promise<TradeResult> {
    return this.trade(Direction.LONG, asset, size, options);
  }

  /**
   * 开空仓
   *
   * @param asset - 资产 (BTC, ETH, SOL)
   * @param size - 仓位大小 (USDC)
   * @param options - 交易选项
   * @returns TradeResult
   *
   * @example
   * ```typescript
   * await hub.short('ETH', 200, { leverage: 3 });
   * ```
   */
  async short(asset: string, size: number, options: TradeOptions = {}): Promise<TradeResult> {
    return this.trade(Direction.SHORT, asset, size, options);
  }

  private async trade(
    direction: Direction,
    asset: string,
    size: number,
    options: TradeOptions
  ): Promise<TradeResult> {
    const normalizedAsset = normalizeAsset(asset);
    const leverage = options.leverage ?? 1;
    const reason = options.reason ?? '';

    if (size <= 0) {
      throw new InvalidParameterError('size', size, 'must be > 0');
    }
    if (leverage < 1 || leverage > 100) {
      throw new InvalidParameterError('leverage', leverage, 'must be 1-100');
    }

    const result = await this.request<any>('POST', '/intents', {
      agent_id: this.agentId,
      intent_type: direction,
      asset: normalizedAsset,
      size_usdc: size,
      leverage,
      reason,
    });

    const intent = parseIntent(result.intent);
    const routing = parseRoutingResult(result.routing);

    let match: Match | undefined;
    if (result.internal_match) {
      match = parseMatch(result.internal_match, this.agentId!);
    }

    let position: Position | undefined;
    if (result.position && !result.position.error) {
      position = parsePosition(result.position);
    }

    return {
      intent,
      routing,
      match,
      position,
      isMatched: match !== undefined,
      wasInternal: routing.internalFilled > 0,
    };
  }

  /**
   * 自然语言下注
   *
   * @param prediction - 预测描述 (如 "BTC will pump", "ETH 要跌")
   * @param amount - 金额
   * @param options - 交易选项
   *
   * @example
   * ```typescript
   * await hub.bet('BTC will pump', 100);
   * await hub.bet('ETH 要跌', 50, { leverage: 3 });
   * ```
   */
  async bet(prediction: string, amount: number, options: TradeOptions = {}): Promise<TradeResult> {
    const predictionLower = prediction.toLowerCase();

    const bullish = ['pump', '涨', '上', 'moon', 'bull', 'up', 'long', '买', 'rise', '高'];
    const bearish = ['dump', '跌', '下', 'crash', 'bear', 'down', 'short', '卖', 'fall', '低'];

    const isBullish = bullish.some((kw) => predictionLower.includes(kw));
    const isBearish = bearish.some((kw) => predictionLower.includes(kw));

    if (!isBullish && !isBearish) {
      throw new InvalidParameterError(
        'prediction',
        prediction,
        "Cannot determine direction. Include words like 'pump', 'dump', '涨', '跌'"
      );
    }

    const direction = isBullish ? Direction.LONG : Direction.SHORT;

    // 解析资产
    let asset = 'BTC';
    for (const a of ['SOL', 'ETH', 'BTC']) {
      if (predictionLower.includes(a.toLowerCase())) {
        asset = a;
        break;
      }
    }

    return this.trade(direction, asset, amount, { ...options, reason: prediction });
  }

  // ============================================================
  // Position Management
  // ============================================================

  async getPositions(): Promise<Position[]> {
    const result = await this.request<any>('GET', `/positions/${this.agentId}`);
    return (result.positions || []).map(parsePosition);
  }

  async getPortfolio(): Promise<any> {
    return this.request<any>('GET', `/portfolio/${this.agentId}`);
  }

  async closePosition(positionId: string): Promise<any> {
    return this.request<any>('POST', `/positions/${positionId}/close`);
  }

  async setStopLoss(positionId: string, price: number): Promise<any> {
    return this.request<any>('POST', `/positions/${positionId}/stop-loss`, { price });
  }

  async setTakeProfit(positionId: string, price: number): Promise<any> {
    return this.request<any>('POST', `/positions/${positionId}/take-profit`, { price });
  }

  // ============================================================
  // Balance
  // ============================================================

  async getBalance(): Promise<Balance> {
    const result = await this.request<any>('GET', `/balance/${this.agentId}`);
    return {
      agentId: result.agent_id,
      total: result.total,
      available: result.available,
      locked: result.locked,
      marginUsed: result.margin_used || 0,
    };
  }

  async deposit(amount: number): Promise<Balance> {
    const result = await this.request<any>('POST', '/deposit', {
      agent_id: this.agentId,
      amount,
    });
    return result.balance;
  }

  async withdraw(amount: number): Promise<Balance> {
    const result = await this.request<any>('POST', '/withdraw', {
      agent_id: this.agentId,
      amount,
    });
    return result.balance;
  }

  // ============================================================
  // Market Data
  // ============================================================

  async getPrice(asset: string = 'BTC'): Promise<Price> {
    const normalizedAsset = asset.toUpperCase().replace('-PERP', '');
    const result = await this.request<any>('GET', `/prices/${normalizedAsset}`);
    return {
      asset: normalizedAsset,
      price: result.price,
      change24h: result.change_24h || 0,
      volume24h: result.volume_24h || 0,
    };
  }

  async getPrices(): Promise<Record<string, Price>> {
    const result = await this.request<any>('GET', '/prices');
    const prices: Record<string, Price> = {};
    for (const [k, v] of Object.entries(result.prices || {})) {
      const data = v as any;
      prices[k] = {
        asset: k,
        price: data.price,
        change24h: data.change_24h || 0,
        volume24h: data.volume_24h || 0,
      };
    }
    return prices;
  }

  async getOrderbook(asset: string = 'BTC-PERP'): Promise<OrderBook> {
    const normalizedAsset = normalizeAsset(asset);
    const result = await this.request<any>('GET', '/intents', { asset: normalizedAsset });

    const allIntents = result.intents || [];
    const longs = allIntents.filter((i: any) => i.intent_type === 'long');
    const shorts = allIntents.filter((i: any) => i.intent_type === 'short');

    return {
      asset: normalizedAsset,
      longs: longs.sort((a: any, b: any) => b.size_usdc - a.size_usdc),
      shorts: shorts.sort((a: any, b: any) => b.size_usdc - a.size_usdc),
      totalLongSize: longs.reduce((sum: number, i: any) => sum + i.size_usdc, 0),
      totalShortSize: shorts.reduce((sum: number, i: any) => sum + i.size_usdc, 0),
      sentiment: longs.length > shorts.length ? 'bullish' : 'bearish',
    };
  }

  async getLeaderboard(limit: number = 20): Promise<Agent[]> {
    const result = await this.request<any>('GET', '/leaderboard', { limit });
    return (result.leaderboard || []).map((a: any) => ({
      agentId: a.agent_id,
      walletAddress: a.wallet_address,
      displayName: a.display_name,
      totalTrades: a.total_trades || 0,
      totalVolume: a.total_volume || 0,
      pnl: a.pnl || 0,
      reputationScore: a.reputation_score || 0.5,
    }));
  }

  // ============================================================
  // AI Decision Helpers
  // ============================================================

  /**
   * AI 决策辅助：基于市场情绪给出建议
   *
   * @example
   * ```typescript
   * const advice = await hub.shouldTrade('BTC');
   * if (advice.confidence > 0.7) {
   *   if (advice.recommendation === 'long') {
   *     await hub.long('BTC', 100);
   *   }
   * }
   * ```
   */
  async shouldTrade(asset: string = 'BTC-PERP'): Promise<TradeAdvice> {
    const orderbook = await this.getOrderbook(asset);
    const total = orderbook.totalLongSize + orderbook.totalShortSize;

    if (total === 0) {
      return {
        recommendation: 'wait',
        confidence: 0.5,
        reason: 'No market activity',
      };
    }

    const longRatio = orderbook.totalLongSize / total;

    if (longRatio > 0.7) {
      return {
        recommendation: 'short',
        confidence: longRatio,
        reason: `Market too bullish (${(longRatio * 100).toFixed(0)}% long). Contrarian short.`,
      };
    } else if (longRatio < 0.3) {
      return {
        recommendation: 'long',
        confidence: 1 - longRatio,
        reason: `Market too bearish (${((1 - longRatio) * 100).toFixed(0)}% short). Contrarian long.`,
      };
    } else {
      return {
        recommendation: 'wait',
        confidence: 0.5,
        reason: 'Market balanced. No clear signal.',
      };
    }
  }

  // ============================================================
  // Signal Betting
  // ============================================================

  async createSignal(
    asset: string,
    signalType: SignalType | string,
    targetValue: number,
    stake: number,
    durationHours: number = 24
  ): Promise<Signal> {
    const result = await this.request<any>('POST', '/signals', {
      agent_id: this.agentId,
      asset: normalizeAsset(asset),
      signal_type: signalType,
      target_value: targetValue,
      stake_amount: stake,
      duration_hours: durationHours,
    });

    return {
      signalId: result.signal.signal_id,
      creatorId: result.signal.creator_id,
      asset: result.signal.asset,
      signalType: result.signal.signal_type as SignalType,
      targetValue: result.signal.target_value,
      stakeAmount: result.signal.stake_amount,
      expiresAt: new Date(result.signal.expires_at),
      description: result.signal.description,
    };
  }

  async fadeSignal(signalId: string): Promise<any> {
    return this.request<any>('POST', '/signals/fade', {
      signal_id: signalId,
      fader_id: this.agentId,
    });
  }

  async getOpenSignals(asset?: string): Promise<Signal[]> {
    const params: any = { status: 'open' };
    if (asset) {
      params.asset = normalizeAsset(asset);
    }
    const result = await this.request<any>('GET', '/signals');
    return (result.signals || []).map((s: any) => ({
      signalId: s.signal_id,
      creatorId: s.creator_id,
      asset: s.asset,
      signalType: s.signal_type as SignalType,
      targetValue: s.target_value,
      stakeAmount: s.stake_amount,
      expiresAt: new Date(s.expires_at),
    }));
  }

  // ============================================================
  // Callbacks
  // ============================================================

  onMatch(callback: (match: Match) => void): this {
    this.onMatchCallback = callback;
    return this;
  }

  onIntent(callback: (intent: Intent) => void): this {
    this.onIntentCallback = callback;
    return this;
  }

  onPnl(callback: (data: any) => void): this {
    this.onPnlCallback = callback;
    return this;
  }

  onLiquidation(callback: (data: any) => void): this {
    this.onLiquidationCallback = callback;
    return this;
  }
}

// ============================================================
// Quick Functions
// ============================================================

/**
 * 一行做多
 *
 * @example
 * ```typescript
 * import { quickLong } from 'ai-perp-dex';
 * await quickLong('BTC', 100, { leverage: 5, apiKey: 'th_xxx' });
 * ```
 */
export async function quickLong(
  asset: string,
  size: number,
  options: TradeOptions & { apiKey?: string; apiUrl?: string } = {}
): Promise<TradeResult> {
  const hub = new TradingHub({ apiKey: options.apiKey, apiUrl: options.apiUrl });
  await hub.connect();
  try {
    return await hub.long(asset, size, options);
  } finally {
    await hub.disconnect();
  }
}

/**
 * 一行做空
 *
 * @example
 * ```typescript
 * import { quickShort } from 'ai-perp-dex';
 * await quickShort('ETH', 200, { leverage: 3, apiKey: 'th_xxx' });
 * ```
 */
export async function quickShort(
  asset: string,
  size: number,
  options: TradeOptions & { apiKey?: string; apiUrl?: string } = {}
): Promise<TradeResult> {
  const hub = new TradingHub({ apiKey: options.apiKey, apiUrl: options.apiUrl });
  await hub.connect();
  try {
    return await hub.short(asset, size, options);
  } finally {
    await hub.disconnect();
  }
}

export default TradingHub;
