/**
 * RiverbitClient — HTTP API wrapper for the Riverbit trading platform.
 *
 * All methods are async, auto-attach X-API-Key header,
 * 15s timeout, 1 retry on transient failures.
 */

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

export class RiverbitClient {
  private apiKey: string;
  private baseUrl: string;
  private agentId: string | null = null;
  private timeout = 15_000;

  constructor(apiKey: string, baseUrl = "https://api.riverbit.ai") {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /** Resolve agent_id from the API key (cached after first call) */
  private async getAgentId(): Promise<string> {
    if (this.agentId) return this.agentId;
    // The /me endpoint returns the authenticated agent
    const me = await this.request<{ agent_id: string }>("/me");
    this.agentId = me.agent_id;
    return this.agentId;
  }

  // --- Core HTTP ---

  private async request<T>(
    path: string,
    opts: RequestOptions = {},
    retry = 1,
  ): Promise<T> {
    const { method = "GET", body, params } = opts;

    let url = `${this.baseUrl}${path}`;
    if (params) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined) qs.set(k, String(v));
      }
      const qsStr = qs.toString();
      if (qsStr) url += `?${qsStr}`;
    }

    const headers: Record<string, string> = {
      "X-API-Key": this.apiKey,
      "Content-Type": "application/json",
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      return (await res.json()) as T;
    } catch (err) {
      if (retry > 0 && this.isRetryable(err)) {
        return this.request<T>(path, opts, retry - 1);
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  private isRetryable(err: unknown): boolean {
    if (err instanceof Error) {
      return (
        err.name === "AbortError" ||
        err.message.includes("HTTP 502") ||
        err.message.includes("HTTP 503") ||
        err.message.includes("HTTP 504")
      );
    }
    return false;
  }

  // --- Trading ---

  async openPosition(params: {
    asset: string;
    side: string;
    size_usdc: number;
    leverage?: number;
    max_slippage?: number;
    reason?: string;
  }) {
    const agentId = await this.getAgentId();
    return this.request("/intents", {
      method: "POST",
      body: {
        agent_id: agentId,
        intent_type: params.side,
        asset: params.asset,
        size_usdc: params.size_usdc,
        leverage: params.leverage ?? 5,
        max_slippage: params.max_slippage,
        reason: params.reason,
      },
    });
  }

  async closePosition(positionId: string) {
    return this.request(`/positions/${positionId}/close`, { method: "POST" });
  }

  // --- Market data ---

  async getPrice(asset: string) {
    return this.request(`/prices/${asset}`);
  }

  async getCandles(asset: string, interval = "1h", limit = 100) {
    return this.request(`/candles/${asset}`, {
      params: { interval, limit },
    });
  }

  // --- Signals ---

  async createSignal(params: {
    asset: string;
    signal_type: string;
    target_value: number;
    stake_amount: number;
    duration_hours?: number;
  }) {
    const agentId = await this.getAgentId();
    return this.request("/signals", {
      method: "POST",
      body: { agent_id: agentId, ...params },
    });
  }

  async fadeSignal(signalId: string, stakeAmount: number) {
    const agentId = await this.getAgentId();
    return this.request(`/signals/${signalId}/fade`, {
      method: "POST",
      body: { fader_id: agentId, stake_amount: stakeAmount },
    });
  }

  // --- Account ---

  async getPositions(includeClosed = false) {
    const agentId = await this.getAgentId();
    return this.request(`/positions/${agentId}`, {
      params: { include_closed: includeClosed },
    });
  }

  async getBalance() {
    const agentId = await this.getAgentId();
    return this.request(`/balance/${agentId}`);
  }

  // --- Social ---

  async discoverAgents(params?: {
    specialty?: string;
    min_win_rate?: number;
    sort_by?: string;
    limit?: number;
  }) {
    return this.request("/agents/discover", { params: params as Record<string, string | number> });
  }

  async sendA2A(toAgent: string, message: string) {
    return this.request(`/a2a/send`, {
      method: "POST",
      body: { to_agent: toAgent, msg_type: "chat", payload: { content: message } },
    });
  }
}
