import uuid
"""
Trading Hub - API Server
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Annotated
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import asyncio
import json
import logging
import uvicorn

# 金融精度类型 - 避免浮点误差
def to_decimal(v) -> Decimal:
    """转换为 Decimal，保留 8 位小数"""
    if isinstance(v, Decimal):
        return v.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    return Decimal(str(v)).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

def to_float(d: Decimal) -> float:
    """Decimal 转 float (用于 JSON 序列化)"""
    return float(d)

logger = logging.getLogger(__name__)

from db.redis_store import store
from api.models import IntentType, IntentStatus, AgentStatus
from services.price_feed import PriceFeed, price_feed
from services.pnl_tracker import pnl_tracker
from services.external_router import external_router, RoutingResult
from services.fee_service import fee_service, FeeType
from services.fee_service import fee_service, FeeType
from services.liquidation_engine import liquidation_engine
from services.intent_parser import intent_parser

# 鉴权中间件
from middleware.auth import (
    verify_agent, 
    verify_agent_optional,
    verify_agent_owns_resource, 
    api_key_store,
    AgentAuth,
    create_jwt_token,
    AuthError,
    ForbiddenError,
)

app = FastAPI(title="Trading Hub", version="0.1.0")

# CORS - 限制允许的来源 (生产环境应更严格)
# CORS 配置 - 从环境变量读取或使用默认值
import os
_cors_origins = os.environ.get("CORS_ORIGINS", "")
ALLOWED_ORIGINS = _cors_origins.split(",") if _cors_origins else [
    "http://localhost:3000",      # 本地前端
    "http://localhost:8082",      # 本地 API
    "https://ai-perp-dex.vercel.app",  # 生产前端
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# === P0 修复: 并发限流 ===
from collections import defaultdict
import time

class RateLimiter:
    """简单的内存限流器 (修复内存泄漏)"""
    MAX_AGENTS = 10000  # 最大追踪 agent 数，防止内存泄漏
    
    def __init__(self, per_agent_limit: int = 10, global_limit: int = 500, window_seconds: int = 1):
        self.per_agent_limit = per_agent_limit  # 每 Agent 每秒请求数
        self.global_limit = global_limit  # 全局每秒请求数
        self.window = window_seconds
        self.agent_requests: Dict[str, List[float]] = defaultdict(list)
        self.global_requests: List[float] = []
        self._last_cleanup = time.time()
    
    def _cleanup(self, requests: List[float], now: float) -> List[float]:
        """清理过期请求"""
        cutoff = now - self.window
        return [t for t in requests if t > cutoff]
    
    def _cleanup_agents(self, now: float):
        """清理不活跃的 agent (防止内存泄漏)"""
        if now - self._last_cleanup < 60:  # 每 60 秒清理一次
            return
        self._last_cleanup = now
        cutoff = now - 300  # 5 分钟不活跃就清理
        inactive = [k for k, v in self.agent_requests.items() if not v or max(v) < cutoff]
        for k in inactive:
            del self.agent_requests[k]
        # 如果还是太多，清理最旧的
        if len(self.agent_requests) > self.MAX_AGENTS:
            sorted_agents = sorted(self.agent_requests.items(), key=lambda x: max(x[1]) if x[1] else 0)
            for k, _ in sorted_agents[:len(self.agent_requests) - self.MAX_AGENTS]:
                del self.agent_requests[k]
    
    def check(self, agent_id: str = None) -> tuple[bool, str]:
        """检查是否允许请求"""
        now = time.time()
        
        # 定期清理不活跃 agent (防止内存泄漏)
        self._cleanup_agents(now)
        
        # 全局限流
        self.global_requests = self._cleanup(self.global_requests, now)
        if len(self.global_requests) >= self.global_limit:
            return False, f"Global rate limit exceeded: {self.global_limit}/s"
        
        # Agent 限流
        if agent_id:
            self.agent_requests[agent_id] = self._cleanup(self.agent_requests[agent_id], now)
            if len(self.agent_requests[agent_id]) >= self.per_agent_limit:
                return False, f"Agent rate limit exceeded: {self.per_agent_limit}/s"
            self.agent_requests[agent_id].append(now)
        
        self.global_requests.append(now)
        return True, ""

rate_limiter = RateLimiter(per_agent_limit=50, global_limit=1000)

# === 并发连接限制 ===
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import threading

class ConcurrencyLimiter:
    """并发连接限制器"""
    def __init__(self, max_concurrent: int = 100):
        self.max_concurrent = max_concurrent
        self.current = 0
        self.lock = threading.Lock()
    
    def acquire(self) -> bool:
        with self.lock:
            if self.current >= self.max_concurrent:
                return False
            self.current += 1
            return True
    
    def release(self):
        with self.lock:
            self.current = max(0, self.current - 1)

concurrency_limiter = ConcurrencyLimiter(max_concurrent=100)

class ConcurrencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not concurrency_limiter.acquire():
            return JSONResponse(
                status_code=503,
                content={"error": "Server too busy", "detail": "Max concurrent requests reached"}
            )
        try:
            response = await call_next(request)
            return response
        finally:
            concurrency_limiter.release()

app.add_middleware(ConcurrencyMiddleware)

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        # 安全移除，避免竞态条件
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass  # 已经被移除
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"WebSocket broadcast failed: {e}")

manager = ConnectionManager()

# === Request Models ===

class RegisterRequest(BaseModel):
    wallet_address: str = Field(..., min_length=1, max_length=100, description="Wallet address (non-empty)")
    display_name: Optional[str] = Field(None, max_length=50, description="Display name (max 50 chars, no HTML)")
    twitter_handle: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500, description="Agent bio (max 500 chars)")

    @field_validator('wallet_address')
    @classmethod
    def validate_wallet(cls, v):
        import re
        if not v or not v.strip():
            raise ValueError('Wallet address cannot be empty')
        v = v.strip()
        
        # 拒绝包含危险字符的地址 (SQL 注入、路径遍历等)
        dangerous_patterns = [
            r'[;\'\"\-\-]',           # SQL 注入特征
            r'\.\./',                  # 路径遍历
            r'<|>',                    # HTML/XML
            r'\s',                     # 空白字符
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError('Invalid characters in wallet address')
        
        # 验证格式: EVM (0x...) 或 Solana (base58)
        is_evm = v.startswith('0x') and len(v) == 42 and re.match(r'^0x[a-fA-F0-9]{40}$', v)
        is_solana = len(v) >= 32 and len(v) <= 44 and re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', v)
        is_test = v.startswith('0x') and len(v) >= 10  # 测试地址宽松验证
        
        if not (is_evm or is_solana or is_test):
            raise ValueError('Invalid wallet address format. Must be EVM (0x...) or Solana address')
        
        return v

    @field_validator('display_name')
    @classmethod
    def sanitize_display_name(cls, v):
        """过滤 HTML/script 标签和 JS 代码，防止 XSS"""
        if v is None:
            return v
        import re
        # 移除所有 HTML 标签
        v = re.sub(r'<[^>]*>', '', v)
        # 移除危险字符序列
        v = re.sub(r'[&<>"\'/\\]', '', v)
        # 移除 JS 函数调用模式 (alert, prompt, confirm, eval, Function 等)
        v = re.sub(r'\b(alert|prompt|confirm|eval|Function|setTimeout|setInterval|constructor)\s*\(.*?\)', '', v, flags=re.IGNORECASE)
        # 移除 javascript: 协议
        v = re.sub(r'javascript\s*:', '', v, flags=re.IGNORECASE)
        # 移除 on* 事件处理器
        v = re.sub(r'\bon\w+\s*=', '', v, flags=re.IGNORECASE)
        v = v.strip()
        if not v:
            raise ValueError('Display name cannot be empty after sanitization')
        return v[:50]

    @field_validator('bio')
    @classmethod
    def sanitize_bio(cls, v):
        """过滤 bio 中的 HTML/script，防止 XSS"""
        if v is None:
            return v
        import re
        v = re.sub(r'<[^>]*>', '', v)
        v = re.sub(r'[<>]', '', v)
        v = re.sub(r'\b(alert|prompt|confirm|eval|Function|setTimeout|setInterval|constructor)\s*\(.*?\)', '', v, flags=re.IGNORECASE)
        v = re.sub(r'javascript\s*:', '', v, flags=re.IGNORECASE)
        v = re.sub(r'\bon\w+\s*=', '', v, flags=re.IGNORECASE)
        v = v.strip()
        return v[:500] if v else None


# 支持的交易对 — Single Source of Truth (config/assets.py)
from config.assets import SUPPORTED_ASSETS as _ASSET_SET
VALID_ASSETS = list(_ASSET_SET)

class IntentRequest(BaseModel):
    agent_id: str
    intent_type: str  # "long" | "short" - 会被验证转为 IntentType
    asset: str = "ETH-PERP"
    size_usdc: float = Field(default=100, gt=0, description="Size must be > 0")
    leverage: int = Field(default=1, ge=1, le=20, description="Leverage 1-20x")
    max_slippage: float = 0.005
    reason: str = ""  # AI 推理理由 (Agent Thoughts)
    
    @field_validator('asset')
    @classmethod
    def validate_asset(cls, v):
        if v not in VALID_ASSETS:
            raise ValueError(f"Invalid asset. Must be one of: {VALID_ASSETS}")
        return v
    
    @field_validator('size_usdc')
    @classmethod
    def validate_size(cls, v):
        """确保金额精度 (最多 2 位小数)"""
        return round(float(v), 2)
    
    @field_validator('intent_type')
    @classmethod
    def validate_intent_type(cls, v):
        """验证交易方向"""
        valid = ['long', 'short']
        if v.lower() not in valid:
            raise ValueError(f"Invalid intent_type. Must be one of: {valid}")
        return v.lower()


class MatchRequest(BaseModel):
    intent_id: str

class IntentParseRequest(BaseModel):
    text: str = Field(..., description="Natural language command to parse")

# === API Endpoints ===

@app.on_event("startup")
async def startup():
    """启动时初始化服务"""
    await price_feed.start()
    await external_router.start()

    # Bridge runtime-generated thoughts/signals to WebSocket chat stream.
    from services.agent_runtime import agent_runtime as _agent_runtime

    async def _broadcast_runtime_chat(message: dict):
        await manager.broadcast({
            "type": "chat_message",
            "data": message
        })

    async def _execute_runtime_trade(
        agent_id: str,
        market: str,
        side: str,
        size_usdc: float,
        confidence: float,
        reasoning: str,
    ) -> dict:
        # 根据信心动态设置杠杆: 1x - 10x（并被 /intents 的校验进一步约束）
        leverage = max(1, min(10, int(round(1 + confidence * 9))))
        req = IntentRequest(
            agent_id=agent_id,
            intent_type=side,
            asset=market,
            size_usdc=max(1.0, round(size_usdc, 2)),
            leverage=leverage,
            max_slippage=0.005,
            reason=f"[Runtime] {reasoning}",
        )
        auth = AgentAuth(agent_id=agent_id, scopes=["read", "write"])
        try:
            result = await create_intent(req, auth)
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except HTTPException as e:
            return {"success": False, "error": str(e.detail), "status_code": e.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

    _agent_runtime.set_realtime_message_hook(_broadcast_runtime_chat)
    _agent_runtime.set_trade_executor_hook(_execute_runtime_trade)
    
    # 注册价格更新回调 - 广播 PnL 更新
    @price_feed.on_price_update
    async def broadcast_pnl_updates(price):
        if not manager.active_connections:
            return
        
        # 获取有持仓的 Agent
        for agent in store.list_agents(limit=100):
            pnl = await pnl_tracker.get_agent_pnl(agent.agent_id)
            if pnl.positions:
                await manager.broadcast({
                    "type": "pnl_update",
                    "data": {
                        "agent_id": agent.agent_id,
                        "total_pnl": pnl.total_pnl,
                        "total_exposure": pnl.total_exposure,
                        "positions": len(pnl.positions),
                    }
                })

@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    await price_feed.stop()
    await external_router.stop()
    from services.agent_runtime import agent_runtime as _agent_runtime
    _agent_runtime.set_realtime_message_hook(None)
    _agent_runtime.set_trade_executor_hook(None)

from fastapi.responses import FileResponse
import os

@app.get("/")
async def root():
    # 返回前端 HTML
    html_path = os.path.join(os.path.dirname(__file__), "../web/index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {"service": "Trading Hub", "version": "0.1.0"}

@app.get("/api")
async def api_info():
    return {"service": "Trading Hub", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/prices")
async def get_prices():
    """获取所有实时价格"""
    prices = await price_feed.get_all_prices()
    return {
        "prices": {k: v.to_dict() for k, v in prices.items() if not k.endswith("-PERP")},
        "last_update": price_feed._last_update.isoformat() if price_feed._last_update else None,
    }

@app.get("/prices/{asset}")
async def get_price(asset: str):
    """获取单个资产价格"""
    price = await price_feed.get_price(asset)
    if not price:
        raise HTTPException(status_code=404, detail="Asset not found")
    return price.to_dict()

@app.get("/stats")
async def get_stats():
    base_stats = store.get_stats()
    router_stats = external_router.get_stats()
    
    # 计算 internal match rate
    total_internal = base_stats.get("total_volume", 0)
    total_external = router_stats.get("total_volume", 0)
    total_volume = total_internal + total_external
    
    internal_rate = total_internal / total_volume if total_volume > 0 else 0
    
    fee_stats = fee_service.get_stats()
    
    return {
        **base_stats,
        "external_routed": router_stats["total_routed"],
        "external_volume": router_stats["total_volume"],
        "external_fees": router_stats["total_fees"],
        "internal_match_rate": f"{internal_rate:.1%}",
        "fee_saved_total": round(total_internal * 0.00025, 4),
        "protocol_fees": fee_stats,
    }


@app.get("/fees")
async def get_fee_stats():
    """
    获取协议手续费统计
    
    费率:
    - Taker: 0.05%
    - Maker: 0.02%
    - Liquidation: 0.5%
    """
    return fee_service.get_stats()


@app.get("/fees/{agent_id}")
async def get_agent_fees(agent_id: str):
    """获取 Agent 的手续费记录"""
    records = fee_service.get_agent_fees(agent_id)
    total = sum(r.amount_usdc for r in records)
    return {
        "agent_id": agent_id,
        "total_paid": round(total, 4),
        "records": [r.to_dict() for r in records],
    }

# --- Agent ---

@app.post("/agents/register")
async def register_agent(req: RegisterRequest):
    """
    注册 Agent (钱包签名)
    
    返回 Agent 信息和首个 API Key (只显示一次，请妥善保存)
    如果钱包已注册，返回 409 Conflict
    """
    # 检查钱包是否已注册
    existing = store.get_agent_by_wallet(req.wallet_address)
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Wallet already registered as {existing.agent_id}. Use your existing API key."
        )
    
    agent = store.create_agent(
        wallet_address=req.wallet_address,
        display_name=req.display_name,
        twitter_handle=req.twitter_handle,
        bio=req.bio,
    )
    
    # 同时注册到通讯系统
    agent_comm.register(
        agent_id=agent.agent_id,
        name=req.display_name or agent.agent_id,
        specialties=["trading"],
    )
    
    # 创建首个 API Key
    raw_key, api_key = api_key_store.create_key(
        agent_id=agent.agent_id,
        name="default",
        scopes=["read", "write"],
    )
    
    # 广播新 Agent
    await manager.broadcast({
        "type": "new_agent",
        "data": agent.to_dict()
    })
    
    return {
        "success": True, 
        "agent": agent.to_dict(),
        "api_key": raw_key,  # ⚠️ 只显示一次!
        "api_key_info": api_key.to_dict(),
    }

# 注意: /agents/discover 和 /agents/schema 必须在 /agents/{agent_id} 之前，否则会被拦截
@app.get("/agents/schema")
async def get_deploy_schema_forward():
    """返回 Agent 部署的 JSON Schema (前向路由，避免被 /agents/{agent_id} 拦截)。"""
    return await get_deploy_schema()

@app.get("/agents/discover")
async def discover_agents_route(specialty: str = None, min_trades: int = None):
    """发现其他 Agent"""
    agents = agent_comm.discover(
        specialty=specialty,
        min_trades=min_trades,
        online_only=False,  # 默认显示所有
    )
    return {"agents": [a.to_dict() for a in agents]}

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 获取余额信息
    result = agent.to_dict()
    balance_info = settlement_engine.get_balance(agent_id)
    if balance_info:
        result["balance"] = balance_info.available
        result["balance_locked"] = balance_info.locked_usdc
        result["balance_total"] = balance_info.balance_usdc
    else:
        result["balance"] = 0.0
        result["balance_locked"] = 0.0
        result["balance_total"] = 0.0
    
    return result

@app.get("/agents")
async def list_agents(limit: int = 50, offset: int = 0):
    agents = store.list_agents(limit, offset)
    return {"agents": [a.to_dict() for a in agents]}

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 20):
    agents = store.get_leaderboard(limit)
    return {"leaderboard": [a.to_dict() for a in agents]}

# --- PnL ---

@app.get("/pnl/{agent_id}")
async def get_agent_pnl(agent_id: str):
    """获取 Agent 的实时盈亏"""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    pnl = await pnl_tracker.get_agent_pnl(agent_id)
    return pnl.to_dict()

@app.get("/pnl-leaderboard")
async def get_pnl_leaderboard(limit: int = 20):
    """获取按 PnL 排序的排行榜"""
    leaderboard = await pnl_tracker.get_leaderboard_with_pnl(limit)
    return {"leaderboard": leaderboard}

# --- Agent Thoughts (AI 推理过程) ---

# 存储最近的 Agent Thoughts
agent_thoughts: Dict[str, list] = {}

@app.get("/agents/{agent_id}/thoughts")
async def get_agent_thoughts(agent_id: str, limit: int = 10):
    """获取 Agent 的最近思考/交易理由"""
    thoughts = agent_thoughts.get(agent_id, [])[-limit:]
    return {
        "agent_id": agent_id,
        "thoughts": thoughts
    }

@app.get("/thoughts/feed")
async def get_thoughts_feed(limit: int = 20):
    """获取全平台的 Agent Thoughts Feed"""
    all_thoughts = []
    for agent_id, thoughts in agent_thoughts.items():
        for t in thoughts[-5:]:  # 每个 agent 最多 5 条
            all_thoughts.append({**t, "agent_id": agent_id})
    
    # 按时间排序
    all_thoughts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"thoughts": all_thoughts[:limit]}

# --- Intent ---

@app.post("/intents")
async def create_intent(
    req: IntentRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    发布交易意图 - Dark Pool 逻辑 (需要认证)
    
    Headers:
        X-API-Key: th_xxxx_xxxxxxxxx
        或
        Authorization: Bearer <jwt_token>
    
    1. 先尝试内部匹配 (0 fee)
    2. 如果部分匹配，剩余路由到外部 (HL fee)
    3. 如果完全没匹配，全部路由到外部
    """
    # 验证: Agent 只能为自己创建 Intent
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot create intent for another agent")
    
    # P0 修复: 限流检查
    allowed, msg = rate_limiter.check(req.agent_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)
    
    # P1 修复: 余额检查 - 确保有足够保证金
    balance_info = settlement_engine.get_balance(req.agent_id)
    if not balance_info:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    available_balance = balance_info.available
    required_margin = req.size_usdc / req.leverage  # 所需保证金
    trading_fee = req.size_usdc * 0.001  # 0.1% 手续费
    total_required = required_margin + trading_fee
    
    if available_balance < total_required:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance. Required: ${total_required:.2f} (margin: ${required_margin:.2f} + fee: ${trading_fee:.2f}), Available: ${available_balance:.2f}"
        )
    
    intent_type = IntentType(req.intent_type)
    
    intent = store.create_intent(
        agent_id=auth.agent_id,  # 使用认证的 agent_id
        intent_type=intent_type,
        asset=req.asset,
        size_usdc=req.size_usdc,
        leverage=req.leverage,
        max_slippage=req.max_slippage,
    )
    
    if not intent:
        raise HTTPException(status_code=400, detail="Agent not found")
    
    # 广播新 Intent
    await manager.broadcast({
        "type": "new_intent",
        "data": intent.to_dict()
    })
    
    # === Dark Pool 路由逻辑 ===
    total_size = req.size_usdc
    internal_filled = 0.0
    external_filled = 0.0
    internal_match = None
    external_fills = []
    
    # Step 1: 尝试内部匹配
    matches = store.find_matching_intents(intent)
    
    if matches:
        best_match = matches[0]
        match_intent = store.get_intent(best_match.intent_id)
        
        # 计算可匹配的数量 (取两边较小的)
        match_size = min(total_size, match_intent.size_usdc)
        
        # 获取实时价格
        price = price_feed.get_cached_price(intent.asset)
        
        # 创建内部匹配
        internal_match = store.create_match(intent, best_match, price)
        internal_match.size_usdc = match_size  # 可能是部分匹配
        internal_filled = match_size
        
        # 广播匹配
        await manager.broadcast({
            "type": "new_match",
            "data": internal_match.to_dict()
        })
    
    # Step 2: 剩余部分路由到外部
    remaining = total_size - internal_filled
    
    if remaining > 0:
        # 路由到 Hyperliquid
        side = "long" if req.intent_type == "long" else "short"
        
        external_fill = await external_router.route(
            asset=req.asset,
            side=side,
            size_usdc=remaining,
            leverage=req.leverage,
        )
        
        external_fills.append(external_fill)
        external_filled = remaining
        
        # 广播外部成交
        await manager.broadcast({
            "type": "external_fill",
            "data": external_fill.to_dict()
        })
    
    # === 收取手续费 (PRD: Taker 0.05%, Maker 0.02%) ===
    protocol_fee = 0.0
    fee_records = []
    
    # Taker 始终付费 (发起方)
    if total_size > 0:
        taker_fee_record = fee_service.collect_fee(
            agent_id=req.agent_id,
            size_usdc=total_size,
            fee_type=FeeType.TAKER,
            match_id=internal_match.match_id if internal_match else None,
        )
        protocol_fee += taker_fee_record.amount_usdc
        fee_records.append(taker_fee_record.to_dict())
    
    # 如果有内部匹配，对手方付 Maker fee
    if internal_match and internal_filled > 0:
        # 对手方是 agent_b（如果 taker 是 agent_a）
        counter_agent = internal_match.agent_b_id if internal_match.agent_a_id == req.agent_id else internal_match.agent_a_id
        maker_fee_record = fee_service.collect_fee(
            agent_id=counter_agent,
            size_usdc=internal_filled,
            fee_type=FeeType.MAKER,
            match_id=internal_match.match_id,
        )
        protocol_fee += maker_fee_record.amount_usdc
        fee_records.append(maker_fee_record.to_dict())
    
    # === 计算结果 ===
    internal_rate = internal_filled / total_size if total_size > 0 else 0
    fee_saved = internal_filled * 0.00025  # 0.025% HL fee saved (vs external)
    total_fee = sum(f.fee for f in external_fills) + protocol_fee
    
    # === 创建持仓 ===
    entry_price = price_feed.get_cached_price(intent.asset)
    if entry_price > 0:
        try:
            position = position_manager.open_position(
                agent_id=req.agent_id,
                asset=req.asset,
                side=req.intent_type,
                size_usdc=req.size_usdc,
                entry_price=entry_price,
                leverage=req.leverage,
            )
            position_data = position.to_dict()

            # 更新 Agent 统计 (开仓也算一次交易)
            agent = store.get_agent(req.agent_id)
            if agent:
                store.update_agent(
                    req.agent_id,
                    total_trades=agent.total_trades + 1,
                    total_volume=agent.total_volume + req.size_usdc
                )
            
            # === Copy Trade: 通知跟单者 ===
            try:
                async def open_copy_position(agent_id, asset, side, size_usdc, leverage, reason):
                    """为跟单者开仓"""
                    copy_entry_price = price_feed.get_cached_price(asset)
                    if copy_entry_price > 0:
                        copy_position = position_manager.open_position(
                            agent_id=agent_id,
                            asset=asset,
                            side=side,
                            size_usdc=size_usdc,
                            entry_price=copy_entry_price,
                            leverage=leverage,
                        )
                        # 更新跟单者统计
                        copy_agent = store.get_agent(agent_id)
                        if copy_agent:
                            store.update_agent(
                                agent_id,
                                total_trades=copy_agent.total_trades + 1,
                                total_volume=copy_agent.total_volume + size_usdc
                            )
                        return copy_position.to_dict()
                    return None
                
                copied_trades = await copy_trade_service.on_trade(
                    leader_id=req.agent_id,
                    trade={
                        "asset": req.asset,
                        "side": req.intent_type,
                        "size_usdc": req.size_usdc,
                        "leverage": req.leverage,
                    },
                    open_position_func=open_copy_position
                )
                if copied_trades:
                    logger.info(f"🔄 Copied trade to {len(copied_trades)} followers")
            except Exception as e:
                logger.warning(f"Copy trade failed: {e}")

        except ValueError as e:
            # 风控拒绝 — Intent 已创建但持仓失败，返回明确失败
            raise HTTPException(status_code=422, detail={
                "message": f"Position rejected by risk control: {e}",
                "intent_id": intent.intent_id,
                "intent_status": "created",
            })
    else:
        # 价格源不可用时，不应返回 success:true + position:null
        raise HTTPException(status_code=503, detail={
            "message": f"Price feed unavailable for {req.asset}, cannot open position",
            "intent_id": intent.intent_id,
            "intent_status": "created",
        })
    
    # === 保存 Agent Thought ===
    if req.reason:
        if req.agent_id not in agent_thoughts:
            agent_thoughts[req.agent_id] = []
        agent_thoughts[req.agent_id].append({
            "type": "trade",
            "action": f"{req.intent_type.upper()} {req.asset}",
            "size": req.size_usdc,
            "leverage": req.leverage,
            "reason": req.reason,
            "timestamp": datetime.now().isoformat(),
            "intent_id": intent.intent_id,
        })
        # 保持最近 50 条
        agent_thoughts[req.agent_id] = agent_thoughts[req.agent_id][-50:]
        
        # 广播 thought
        await manager.broadcast({
            "type": "agent_thought",
            "data": {
                "agent_id": req.agent_id,
                "action": f"{req.intent_type.upper()} {req.asset} ${req.size_usdc}",
                "reason": req.reason,
            }
        })
    
    return {
        "success": True,
        "intent": intent.to_dict(),
        "routing": {
            "total_size": total_size,
            "internal_filled": internal_filled,
            "external_filled": external_filled,
            "internal_rate": f"{internal_rate:.1%}",
            "fee_saved": round(fee_saved, 4),
            "total_fee": round(total_fee, 4),
        },
        "fees": {
            "protocol_fee": round(protocol_fee, 4),
            "taker_rate": "0.05%",
            "maker_rate": "0.02%",
            "records": fee_records,
        },
        "internal_match": internal_match.to_dict() if internal_match else None,
        "external_fills": [f.to_dict() for f in external_fills],
        "position": position_data,
    }

@app.get("/intents/stats")
async def get_intent_stats():
    """
    获取 Intent 统计信息
    """
    all_intents = list(store.intents.values()) if hasattr(store, 'intents') else []
    
    total = len(all_intents)
    open_count = sum(1 for i in all_intents if i.status.value == "open")
    filled = sum(1 for i in all_intents if i.status.value == "filled")
    cancelled = sum(1 for i in all_intents if i.status.value == "cancelled")
    
    # 按资产统计
    by_asset = {}
    for intent in all_intents:
        asset = intent.asset
        if asset not in by_asset:
            by_asset[asset] = {"count": 0, "total_size": 0}
        by_asset[asset]["count"] += 1
        by_asset[asset]["total_size"] += intent.size_usdc
    
    # 总交易量
    total_volume = sum(i.size_usdc for i in all_intents)
    
    return {
        "total_intents": total,
        "open": open_count,
        "filled": filled,
        "cancelled": cancelled,
        "total_volume_usdc": total_volume,
        "by_asset": by_asset,
    }

@app.get("/intents/{intent_id}")
async def get_intent(intent_id: str):
    intent = store.get_intent(intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    return intent.to_dict()

@app.get("/intents")
async def list_intents(asset: str = None, status: str = "open", limit: int = 100):
    if status == "open":
        intents = store.list_open_intents(asset, limit)
    else:
        intents = list(store.intents.values())[:limit]
    return {"intents": [i.to_dict() for i in intents]}

@app.post("/intents/parse")
async def parse_intent(req: IntentParseRequest):
    """
    解析自然语言交易指令
    Input: "Buy ETH $100"
    Output: Structured Intent
    """
    result = intent_parser.parse(req.text)
    return {"parsed": result.dict()}

@app.delete("/intents/{intent_id}")
async def cancel_intent(
    intent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """取消 Intent (需要认证，只能取消自己的)"""
    intent = store.get_intent(intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    # 验证所有权
    verify_agent_owns_resource(auth, intent.agent_id, "intent")
    
    intent = store.update_intent(intent_id, status=IntentStatus.CANCELLED)
    
    await manager.broadcast({
        "type": "intent_cancelled",
        "data": {"intent_id": intent_id}
    })
    
    return {"success": True}

# --- Match ---

@app.get("/matches")
async def list_matches(limit: int = 50):
    matches = store.list_recent_matches(limit)
    return {"matches": [m.to_dict() for m in matches]}

@app.get("/matches/{match_id}")
async def get_match(match_id: str):
    match = store.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match.to_dict()

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # 发送欢迎消息
    await websocket.send_json({
        "type": "connected",
        "message": "Welcome to AI Perp DEX",
        "timestamp": datetime.now().isoformat()
    })
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or handle commands
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- 模拟数据 ---

@app.post("/demo/seed")
async def seed_demo_data():
    """
    生成模拟数据 (仅限开发/测试环境)
    """
    import os
    if os.getenv("API_ENV") == "production":
        raise HTTPException(403, "Demo endpoint disabled in production")
    
    # 创建一些 Agent
    agents = []
    for i in range(5):
        agent = store.create_agent(
            wallet_address=f"0x{i:040x}",
            display_name=f"Agent_{i+1}",
            twitter_handle=f"@agent_{i+1}"
        )
        agent.reputation_score = 0.5 + (i * 0.1)
        agents.append(agent)
    
    # 创建一些 Intent
    assets = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
    for i, agent in enumerate(agents):
        intent_type = IntentType.LONG if i % 2 == 0 else IntentType.SHORT
        store.create_intent(
            agent_id=agent.agent_id,
            intent_type=intent_type,
            asset=assets[i % len(assets)],
            size_usdc=100 * (i + 1),
            leverage=2 * (i + 1),
        )
    
    return {"success": True, "agents": len(agents)}


# ==========================================
# Signal Betting API (预测对赌)
# ==========================================

from services.signal_betting import signal_betting, SignalType, SignalStatus

class CreateSignalRequest(BaseModel):
    agent_id: str
    asset: str
    signal_type: str  # "price_above", "price_below", "price_change"
    target_value: float = Field(..., gt=0, description="Target price must be positive")
    stake_amount: float = Field(..., gt=0, le=1000, description="Stake 0-1000 USDC")
    duration_hours: float = Field(default=24, ge=0.01, le=168, description="Duration 0.01-168 hours (min ~36 seconds for testing)")
    
    @field_validator('asset')
    @classmethod
    def validate_asset(cls, v):
        if v not in VALID_ASSETS:
            raise ValueError(f"Invalid asset. Must be one of: {VALID_ASSETS}")
        return v
    
    @field_validator('signal_type')
    @classmethod
    def validate_signal_type(cls, v):
        valid = ["price_above", "price_below", "price_change"]
        if v not in valid:
            raise ValueError(f"Invalid signal_type. Must be one of: {valid}")
        return v

class FadeSignalRequest(BaseModel):
    signal_id: str
    fader_id: str
    stake_amount: float = Field(..., gt=0, description="Stake amount (must match signal creator's stake)")

@app.post("/signals")
async def create_signal(
    req: CreateSignalRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    创建预测信号 (需要认证)
    
    示例: "ETH 24h 后 > $2200, 押注 $50"
    """
    # 验证: Agent 只能为自己创建 Signal
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot create signal for another agent")
    
    try:
        signal_type = SignalType(req.signal_type)
    except ValueError:
        raise HTTPException(400, f"Invalid signal_type. Use: price_above, price_below, price_change")
    
    # 验证 Agent
    agent = store.get_agent(auth.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    try:
        # 获取当前价格 (用于 PRICE_CHANGE 类型)
        asset_name = req.asset.replace("-PERP", "")
        current_price = price_feed.get_cached_price(asset_name) or 0.0
        
        signal = signal_betting.create_signal(
            creator_id=req.agent_id,
            asset=req.asset,
            signal_type=signal_type,
            target_value=req.target_value,
            stake_amount=req.stake_amount,
            duration_hours=req.duration_hours,
            current_price=current_price,  # 传入当前价格
        )
        
        # 生成人类可读描述
        if signal_type == SignalType.PRICE_ABOVE:
            description = f"{req.asset} > ${req.target_value:,.2f} in {req.duration_hours}h"
        elif signal_type == SignalType.PRICE_BELOW:
            description = f"{req.asset} < ${req.target_value:,.2f} in {req.duration_hours}h"
        else:
            description = f"{req.asset} {req.target_value:+.1f}% in {req.duration_hours}h"
        
        # 广播
        await manager.broadcast({
            "type": "signal_created",
            "signal_id": signal.signal_id,
            "creator": req.agent_id,
            "description": description,
            "stake": req.stake_amount,
        })
        
        return {
            "success": True,
            "signal": {
                "signal_id": signal.signal_id,
                "creator_id": signal.creator_id,
                "asset": signal.asset,
                "signal_type": signal.signal_type.value,
                "target_value": signal.target_value,
                "stake_amount": signal.stake_amount,
                "description": description,
                "expires_at": signal.expires_at.isoformat(),
                "status": signal.status.value,
            }
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/signals/fade")
async def fade_signal(
    req: FadeSignalRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    Fade 一个 Signal (对赌) - 需要认证
    
    押注相同金额，认为 Signal 预测错误
    """
    # 验证: Agent 只能为自己 fade
    if auth.agent_id != req.fader_id:
        raise ForbiddenError("Cannot fade as another agent")
    
    agent = store.get_agent(auth.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    try:
        bet = signal_betting.fade_signal(req.signal_id, req.fader_id, req.stake_amount)
        
        # 广播
        await manager.broadcast({
            "type": "signal_faded",
            "bet_id": bet.bet_id,
            "signal_id": req.signal_id,
            "fader": req.fader_id,
            "total_pot": bet.total_pot,
        })
        
        return {
            "success": True,
            "bet": {
                "bet_id": bet.bet_id,
                "signal_id": bet.signal_id,
                "creator_id": bet.creator_id,
                "fader_id": bet.fader_id,
                "asset": bet.asset,
                "target_value": bet.target_value,
                "stake_per_side": bet.stake_per_side,
                "total_pot": bet.total_pot,
                "expires_at": bet.expires_at.isoformat(),
                "status": bet.status,
            },
            "message": f"Bet matched! Total pot: ${bet.total_pot}. Settlement at {bet.expires_at}",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/signals")
async def list_signals(asset: str = None, status: str = "open"):
    """列出 Signals"""
    if status == "open":
        signals = signal_betting.get_open_signals(asset)
    else:
        signals = list(signal_betting.signals.values())
        if asset:
            signals = [s for s in signals if s.asset == asset]
    
    return {
        "signals": [
            {
                "signal_id": s.signal_id,
                "creator_id": s.creator_id,
                "asset": s.asset,
                "signal_type": s.signal_type.value,
                "target_value": s.target_value,
                "stake_amount": s.stake_amount,
                "expires_at": s.expires_at.isoformat(),
                "status": s.status.value,
            }
            for s in signals
        ]
    }


# 注意: /signals/open 必须在 /signals/{signal_id} 之前
@app.get("/signals/open")
async def list_open_signals_route():
    """查看开放信号"""
    from services.signal_betting import SignalStatus
    open_signals = [
        s for s in signal_betting.signals.values()
        if s.status == SignalStatus.OPEN
    ]
    return {
        "signals": [
            {
                "signal_id": s.signal_id,
                "creator_id": s.creator_id,
                "asset": s.asset,
                "signal_type": s.signal_type.value,
                "target_value": s.target_value,
                "stake_amount": s.stake_amount,
                "expires_at": s.expires_at.isoformat(),
            }
            for s in open_signals
        ]
    }

@app.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    """获取 Signal 详情"""
    signal = signal_betting.signals.get(signal_id)
    if not signal:
        raise HTTPException(404, "Signal not found")
    
    return {
        "signal_id": signal.signal_id,
        "creator_id": signal.creator_id,
        "asset": signal.asset,
        "signal_type": signal.signal_type.value,
        "target_value": signal.target_value,
        "stake_amount": signal.stake_amount,
        "expires_at": signal.expires_at.isoformat(),
        "status": signal.status.value,
        "fader_id": signal.fader_id,
        "matched_at": signal.matched_at.isoformat() if signal.matched_at else None,
        "settlement_price": signal.settlement_price,
        "winner_id": signal.winner_id,
        "payout": signal.payout,
    }


@app.post("/bets/{bet_id}/settle")
async def settle_bet(
    bet_id: str, 
    price: float = None,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    结算对赌 (需要认证，只有参与者可结算)
    
    需要提供结算价格，或者使用当前价格
    """
    try:
        # 验证调用者是参与者
        bet = signal_betting.bets.get(bet_id)
        if not bet:
            raise HTTPException(404, "Bet not found")
        if auth.agent_id not in [bet.creator_id, bet.fader_id]:
            raise ForbiddenError("Only bet participants can settle")
        
        # 获取当前价格
        if price is None:
            if bet:
                asset = bet.asset.replace("-PERP", "")
                price = price_feed.get_price(asset)
        
        bet = await signal_betting.settle_bet(bet_id, price)
        
        # 广播
        await manager.broadcast({
            "type": "bet_settled",
            "bet_id": bet.bet_id,
            "winner_id": bet.winner_id,
            "settlement_price": bet.settlement_price,
        })
        
        loser_id = bet.fader_id if bet.winner_id == bet.creator_id else bet.creator_id
        payout = bet.total_pot * (1 - signal_betting.PROTOCOL_FEE_RATE)
        
        return {
            "success": True,
            "bet_id": bet.bet_id,
            "settlement_price": bet.settlement_price,
            "winner_id": bet.winner_id,
            "loser_id": loser_id,
            "payout": payout,
            "protocol_fee": bet.total_pot * signal_betting.PROTOCOL_FEE_RATE,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/betting/stats")
async def get_betting_stats():
    """获取对赌统计"""
    return signal_betting.get_stats()


@app.get("/agents/{agent_id}/betting")
async def get_agent_betting_stats(agent_id: str):
    """获取 Agent 的对赌统计"""
    return signal_betting.get_agent_stats(agent_id)


# ==========================================
# Position Management API (持仓管理)
# ==========================================

from services.position_manager import position_manager, PositionSide

@app.on_event("startup")
async def startup_position_manager():
    """启动持仓管理器"""
    position_manager.price_feed = price_feed
    # 重新从 Redis 加载持仓 (模块导入时 Redis 可能还没准备好)
    position_manager._load_from_redis()
    await position_manager.start()


@app.on_event("startup")
async def startup_liquidation():
    """启动清算引擎"""
    # 注入依赖
    position_manager.set_settlement_engine(settlement_engine)  # 余额同步
    fee_service.set_position_manager(position_manager)
    liquidation_engine.set_dependencies(position_manager, price_feed, fee_service)
    await liquidation_engine.start()
    
    @liquidation_engine.on_liquidation
    async def broadcast_liquidation(record):
        await manager.broadcast({
            "type": "liquidation",
            "data": record.to_dict()
        })


@app.get("/positions/{agent_id}")
async def get_positions(
    agent_id: str,
    include_closed: bool = False,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取 Agent 的持仓 (需要认证，只能查看自己的持仓)

    Query params:
        include_closed: 是否包含已平仓历史 (默认 false, 只返回开放持仓)
    """
    # 验证只能查看自己的持仓
    verify_agent_owns_resource(auth, agent_id, "position list")

    positions = position_manager.get_positions(agent_id, only_open=not include_closed)

    # 更新开放持仓的价格 (使用同步缓存方法)
    for pos in positions:
        if pos.is_open:
            asset = pos.asset.replace("-PERP", "")
            price = price_feed.get_cached_price(asset)
            pos.update_pnl(price)

    return {
        "agent_id": agent_id,
        "positions": [p.to_dict() for p in positions],
        "total": len(positions),
    }

@app.get("/portfolio/{agent_id}")
async def get_portfolio(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取投资组合概览 (需要认证，只能查看自己的组合)"""
    # 验证只能查看自己的组合
    verify_agent_owns_resource(auth, agent_id, "portfolio")

    # 先更新所有价格 (使用同步缓存方法)
    for pos in position_manager.get_positions(agent_id):
        asset = pos.asset.replace("-PERP", "")
        price = price_feed.get_cached_price(asset)
        pos.update_pnl(price)

    return position_manager.get_portfolio_value(agent_id)

class StopLossRequest(BaseModel):
    price: Optional[float] = None
    stop_loss_price: Optional[float] = None  # 别名
    
    @model_validator(mode='after')
    def get_price(self):
        # 支持两种字段名
        if self.stop_loss_price is not None:
            self.price = self.stop_loss_price
        if self.price is None:
            raise ValueError("price or stop_loss_price is required")
        return self

class TakeProfitRequest(BaseModel):
    price: Optional[float] = None
    take_profit_price: Optional[float] = None  # 别名
    
    @model_validator(mode='after')
    def get_price(self):
        # 支持两种字段名
        if self.take_profit_price is not None:
            self.price = self.take_profit_price
        if self.price is None:
            raise ValueError("price or take_profit_price is required")
        return self

@app.post("/positions/{position_id}/stop-loss")
async def set_stop_loss(
    position_id: str, 
    req: StopLossRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """设置止损 (需要认证，只能操作自己的持仓)"""
    try:
        pos = position_manager.positions.get(position_id)
        if not pos:
            raise HTTPException(404, "Position not found")
        
        # 验证所有权
        verify_agent_owns_resource(auth, pos.agent_id, "position")
        
        # 验证仓位是否已平仓
        if not pos.is_open:
            raise HTTPException(400, "Position is already closed")
        
        # 验证价格有效性
        if req.price <= 0:
            raise HTTPException(400, "Stop loss price must be greater than 0")
        
        # 验证止损逻辑: 多仓止损应低于入场价，空仓止损应高于入场价
        side_value = pos.side.value if hasattr(pos.side, 'value') else str(pos.side)
        if side_value == "long" and req.price >= pos.entry_price:
            raise HTTPException(status_code=400, detail=f"Stop loss for LONG position must be below entry price (${pos.entry_price:.2f})")
        if side_value == "short" and req.price <= pos.entry_price:
            raise HTTPException(status_code=400, detail=f"Stop loss for SHORT position must be above entry price (${pos.entry_price:.2f})")
        
        position_manager.set_stop_loss(position_id, req.price)
        return {"success": True, "position": pos.to_dict()}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/positions/{position_id}/take-profit")
async def set_take_profit(
    position_id: str, 
    req: TakeProfitRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """设置止盈 (需要认证，只能操作自己的持仓)"""
    try:
        pos = position_manager.positions.get(position_id)
        if not pos:
            raise HTTPException(404, "Position not found")
        
        # 验证所有权
        verify_agent_owns_resource(auth, pos.agent_id, "position")
        
        # 验证仓位是否已平仓
        if not pos.is_open:
            raise HTTPException(400, "Position is already closed")
        
        # 验证价格有效性
        if req.price <= 0:
            raise HTTPException(400, "Take profit price must be greater than 0")
        
        # 验证止盈逻辑: 多仓止盈应高于入场价，空仓止盈应低于入场价
        side_value = pos.side.value if hasattr(pos.side, 'value') else str(pos.side)
        if side_value == "long" and req.price <= pos.entry_price:
            raise HTTPException(status_code=400, detail=f"Take profit for LONG position must be above entry price (${pos.entry_price:.2f})")
        if side_value == "short" and req.price >= pos.entry_price:
            raise HTTPException(status_code=400, detail=f"Take profit for SHORT position must be below entry price (${pos.entry_price:.2f})")
        
        position_manager.set_take_profit(position_id, req.price)
        return {"success": True, "position": pos.to_dict()}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/positions/{position_id}/close")
async def close_position(
    position_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """手动平仓 (需要认证，只能操作自己的持仓)"""
    try:
        pos = position_manager.positions.get(position_id)
        if not pos:
            raise HTTPException(404, "Position not found")
        
        # 验证所有权
        verify_agent_owns_resource(auth, pos.agent_id, "position")
        
        # 验证仓位是否已平仓
        if not pos.is_open:
            raise HTTPException(400, "Position is already closed")
        
        asset = pos.asset.replace("-PERP", "")
        price_data = await price_feed.get_price(asset)
        if not price_data:
            # Fallback to current position price
            price = pos.current_price
        else:
            price = price_data.price
        
        # 保存入场价用于返回
        entry_price = pos.entry_price
        size_usdc = pos.size_usdc
        
        pos = position_manager.close_position_manual(position_id, price)
        
        # 更新 Agent 统计 (交易次数 +1, 交易量累加)
        agent = store.get_agent(auth.agent_id)
        if agent:
            store.update_agent(
                auth.agent_id,
                total_trades=agent.total_trades + 1,
                total_volume=agent.total_volume + size_usdc,
                pnl=agent.pnl + pos.realized_pnl
            )
        
        return {
            "success": True,
            "position_id": position_id,
            "position": pos.to_dict(),  # 完整 Position 对象
            "result": {
                "entry_price": entry_price,
                "exit_price": price,
                "realized_pnl": pos.realized_pnl,
                "size_usdc": size_usdc,
            },
            "close_price": price,  # 保持向后兼容
            "pnl": pos.realized_pnl,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))

# ==========================================
# Risk Alerts API (风控告警)
# ==========================================

@app.get("/alerts/{agent_id}")
async def get_alerts(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取风控告警 (需要认证，只能查看自己的告警)"""
    verify_agent_owns_resource(auth, agent_id, "alerts")

    alerts = position_manager.get_alerts(agent_id)
    return {
        "agent_id": agent_id,
        "alerts": [
            {
                "alert_id": a.alert_id,
                "type": a.alert_type,
                "message": a.message,
                "severity": a.severity,
                "created_at": a.created_at.isoformat(),
                "acknowledged": a.acknowledged,
            }
            for a in alerts
        ],
    }

@app.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """确认告警 (需要认证，只能确认自己的告警)"""
    alert = position_manager.alerts.get(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    if alert.agent_id != auth.agent_id:
        raise ForbiddenError("Cannot acknowledge other agent's alerts")
    
    position_manager.acknowledge_alert(alert_id)
    return {"success": True}


# ==========================================
# Liquidation API (清算)
# ==========================================

@app.get("/liquidations")
async def get_liquidations(limit: int = 20):
    """
    获取最近的清算记录
    
    费率: 0.5%
    触发条件: 健康度 < 5%
    """
    return {
        "stats": liquidation_engine.get_stats(),
        "recent": liquidation_engine.get_recent(limit),
    }


@app.get("/liquidations/stats")
async def get_liquidation_stats():
    """获取清算统计"""
    return liquidation_engine.get_stats()


@app.get("/positions/{position_id}/health")
async def check_position_health(
    position_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    检查仓位健康度 (需要认证，只能查看自己的仓位)

    返回:
    - health_ratio: 健康度比例
    - health_status: safe/warning/danger
    - distance_to_liquidation: 距离清算价格
    - will_liquidate: 是否会被清算
    """
    pos = position_manager.positions.get(position_id)
    if not pos:
        raise HTTPException(404, "Position not found")

    verify_agent_owns_resource(auth, pos.agent_id, "position health")

    return liquidation_engine.check_position_health(pos)


# ==========================================
# Backtest API (策略回测)
# ==========================================

from services.backtester import backtester, strategy_momentum, strategy_grid
from services.historical_data import enhanced_backtester, historical_data
from services.agent_comms import agent_comm, MessageType
from services.settlement import settlement_engine
from datetime import datetime, timedelta

class BacktestRequest(BaseModel):
    strategy: str  # "momentum", "grid"
    asset: str = "ETH"
    days: int = 30
    initial_capital: float = 1000
    use_real_data: bool = True

@app.post("/backtest")
async def run_backtest(req: BacktestRequest):
    """运行策略回测 (支持真实数据)"""
    
    # 定义策略
    async def momentum_strategy(price, position, capital, history, candle):
        if len(history) < 20:
            return None
        ma20 = sum(history[-20:]) / 20
        if not position:
            if price > ma20 * 1.02:
                return "long"
            elif price < ma20 * 0.98:
                return "short"
        else:
            # 盈亏 5% 平仓
            entry = position["entry"]
            if position["side"] == "long":
                if price > entry * 1.05 or price < entry * 0.95:
                    return "close"
            else:
                if price < entry * 0.95 or price > entry * 1.05:
                    return "close"
        return None
    
    async def grid_strategy(price, position, capital, history, candle):
        if len(history) < 10:
            return None
        avg = sum(history[-10:]) / 10
        if not position:
            if price < avg * 0.98:
                return "long"
            elif price > avg * 1.02:
                return "short"
        else:
            entry = position["entry"]
            diff = abs(price - entry) / entry
            if diff > 0.03:
                return "close"
        return None
    
    if req.strategy == "momentum":
        strategy = momentum_strategy
    elif req.strategy == "grid":
        strategy = grid_strategy
    else:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")
    
    if req.use_real_data:
        # 使用真实数据回测
        result = await enhanced_backtester.run(
            strategy=strategy,
            asset=req.asset,
            days=req.days,
            initial_capital=req.initial_capital,
        )
        result["data_source"] = "binance/coingecko"
        return result
    else:
        # 使用模拟数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        result = await backtester.run(
            strategy=strategy_momentum if req.strategy == "momentum" else strategy_grid,
            asset=req.asset,
            start_date=start_date,
            end_date=end_date,
            initial_capital=req.initial_capital,
        )
        return {
            "strategy": req.strategy,
            "asset": req.asset,
            "period_days": req.days,
            "data_source": "simulated",
            "initial_capital": result.initial_capital,
            "final_capital": round(result.final_capital, 2),
            "total_return": round(result.total_return, 2),
            "total_return_pct": round(result.total_return_pct, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "win_rate": round(result.win_rate, 1),
            "profit_factor": round(result.profit_factor, 2),
            "total_trades": result.total_trades,
        }


# ==========================================
# Agent Communication API
# ==========================================

@app.get("/agents/discover")
async def discover_agents(specialty: str = None, min_trades: int = None):
    """发现其他 Agent"""
    agents = agent_comm.discover(
        specialty=specialty,
        min_trades=min_trades,
    )
    return {"agents": [a.to_dict() for a in agents]}

class SignalShareRequest(BaseModel):
    agent_id: str
    asset: str
    direction: str
    confidence: float
    reason: str = ""

@app.post("/signals/share")
async def share_signal(
    req: SignalShareRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """分享交易信号 (需要认证)"""
    # 验证: 只能以自己的名义分享
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot share signals as another agent")
    
    msg_id = await agent_comm.share_signal(
        from_agent=auth.agent_id,
        signal={
            "asset": req.asset,
            "direction": req.direction,
            "confidence": req.confidence,
            "reason": req.reason,
        }
    )
    return {"success": True, "message_id": msg_id}

@app.get("/agents/{agent_id}/inbox")
async def get_inbox(agent_id: str, limit: int = 50):
    """获取收件箱"""
    messages = agent_comm.get_inbox(agent_id, limit)
    return {"messages": [m.to_dict() for m in messages]}


# ==========================================
# Agent Communication API (AI Native)
# ==========================================

class AgentMessageRequest(BaseModel):
    to_agent: str
    message: str

@app.post("/agents/{agent_id}/message")
async def send_message(
    agent_id: str,
    req: AgentMessageRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """Agent 间发送消息"""
    verify_agent_owns_resource(auth, agent_id, "message")
    
    from services.agent_comms import AgentMessage, MessageType
    msg = AgentMessage(
        message_id=str(uuid.uuid4())[:12],
        msg_type=MessageType.CHAT,
        from_agent=agent_id,
        to_agent=req.to_agent,
        payload={"content": req.message}
    )
    msg_id = await agent_comm.send(msg)
    return {"success": True, "message_id": msg_id}


class TradeRequestModel(BaseModel):
    to_agent: str
    asset: str
    side: str  # "long" | "short"
    size_usdc: float
    price: Optional[float] = None
    message: Optional[str] = None

@app.post("/agents/{agent_id}/trade-request")
async def send_trade_request(
    agent_id: str,
    req: TradeRequestModel,
    auth: AgentAuth = Depends(verify_agent)
):
    """发送交易请求给其他 Agent"""
    verify_agent_owns_resource(auth, agent_id, "trade_request")
    
    msg_id = await agent_comm.send_trade_request(
        from_agent=agent_id,
        to_agent=req.to_agent,
        trade={
            "asset": req.asset,
            "side": req.side,
            "size_usdc": req.size_usdc,
            "price": req.price,
            "message": req.message,
        }
    )
    return {"success": True, "request_id": msg_id}


@app.post("/agents/{agent_id}/trade-accept/{request_id}")
async def accept_trade_request(
    agent_id: str,
    request_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """接受交易请求"""
    verify_agent_owns_resource(auth, agent_id, "trade_accept")
    
    msg_id = await agent_comm.accept_trade(agent_id, request_id)
    return {"success": True, "message_id": msg_id}


class StrategyOfferRequest(BaseModel):
    strategy_name: str
    description: str
    price_usdc: float
    performance: Optional[dict] = None  # {"win_rate": 0.65, "sharpe": 1.2}

@app.post("/agents/{agent_id}/strategy/offer")
async def offer_strategy(
    agent_id: str,
    req: StrategyOfferRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """出售策略"""
    verify_agent_owns_resource(auth, agent_id, "strategy_offer")
    
    strategy = {
        "name": req.strategy_name,
        "description": req.description,
        "price_usdc": req.price_usdc,
        "performance": req.performance or {},
    }
    msg_id = await agent_comm.offer_strategy(
        from_agent=agent_id,
        strategy=strategy
    )
    return {"success": True, "offer_id": msg_id}


@app.get("/strategies/marketplace")
async def get_strategy_marketplace(limit: int = 20):
    """获取策略市场"""
    # 从广播消息中获取策略 offers
    offers = []
    seen = set()
    for agent_id in agent_comm.agents.keys():
        messages = agent_comm.get_inbox(agent_id, 100)
        for msg in messages:
            if msg.msg_type == MessageType.STRATEGY_OFFER and msg.message_id not in seen:
                seen.add(msg.message_id)
                offers.append({
                    "offer_id": msg.message_id,
                    "seller": msg.from_agent,
                    "strategy_name": msg.payload.get("name"),
                    "description": msg.payload.get("description"),
                    "price_usdc": msg.payload.get("price_usdc"),
                    "performance": msg.payload.get("performance", {}),
                    "timestamp": msg.timestamp.isoformat(),
                })
    return {"strategies": offers[:limit]}


class CreateAllianceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Alliance name (1-50 chars)")
    description: Optional[str] = Field(default="", max_length=500)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Alliance name cannot be empty")
        return v

@app.post("/alliances")
async def create_alliance(
    req: CreateAllianceRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """创建 Agent 联盟"""
    # 检查是否已存在同名联盟
    for alliance in agent_comm.alliances.values():
        if alliance.name.lower() == req.name.lower():
            raise HTTPException(400, f"Alliance with name '{req.name}' already exists")
    
    alliance = agent_comm.create_alliance(auth.agent_id, req.name)
    return {
        "success": True,
        "alliance": {
            "alliance_id": alliance.alliance_id,
            "name": alliance.name,
            "leader": alliance.leader_id,
            "members": list(alliance.members),
        }
    }


@app.get("/alliances")
async def list_alliances():
    """列出所有联盟"""
    alliances = []
    for aid, alliance in agent_comm.alliances.items():
        alliances.append({
            "alliance_id": alliance.alliance_id,
            "name": alliance.name,
            "leader": alliance.leader_id,
            "member_count": len(alliance.members),
        })
    return {"alliances": alliances}


@app.post("/alliances/{alliance_id}/invite/{invitee_id}")
async def invite_to_alliance(
    alliance_id: str,
    invitee_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """邀请 Agent 加入联盟"""
    # 验证联盟存在
    alliance = agent_comm.alliances.get(alliance_id)
    if not alliance:
        raise HTTPException(404, f"Alliance not found: {alliance_id}")
    
    # 不能邀请自己
    if invitee_id == auth.agent_id:
        raise HTTPException(400, "Cannot invite yourself")
    
    # 验证被邀请者存在
    invitee = store.get_agent(invitee_id)
    if not invitee:
        raise HTTPException(404, f"Agent not found: {invitee_id}")
    
    # 验证被邀请者不在联盟中
    if invitee_id in alliance.members:
        raise HTTPException(400, f"Agent {invitee_id} is already in this alliance")
    
    msg_id = await agent_comm.invite_to_alliance(alliance_id, auth.agent_id, invitee_id)
    return {"success": True, "invite_id": msg_id}


@app.post("/alliances/{alliance_id}/join")
async def join_alliance(
    alliance_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """加入联盟"""
    # 验证联盟存在
    alliance = agent_comm.alliances.get(alliance_id)
    if not alliance:
        raise HTTPException(404, f"Alliance not found: {alliance_id}")
    
    # 验证不是已经在联盟中
    if auth.agent_id in alliance.members:
        raise HTTPException(400, "Already a member of this alliance")
    
    agent_comm.join_alliance(alliance_id, auth.agent_id)
    return {"success": True}


@app.get("/alliances/{alliance_id}/members")
async def get_alliance_members(alliance_id: str):
    """获取联盟成员"""
    members = agent_comm.get_alliance_members(alliance_id)
    return {"members": [m.to_dict() for m in members]}


# ==========================================
# Copy Trade API (跟单系统)
# ==========================================

from services.copy_trade import copy_trade_service

class FollowRequest(BaseModel):
    multiplier: float = Field(default=1.0, gt=0, le=3.0, description="Position multiplier (0-3x)")
    max_per_trade: float = Field(default=100.0, gt=0, le=1000.0, description="Max per trade ($0-1000)")
    allocation: Optional[float] = Field(default=None, gt=0, description="Alias for max_per_trade")
    
    @model_validator(mode='after')
    def handle_allocation(self):
        # allocation 是 max_per_trade 的别名
        if self.allocation is not None:
            self.max_per_trade = min(self.allocation, 1000.0)
        return self

@app.post("/agents/{agent_id}/follow/{leader_id}")
async def follow_trader(
    agent_id: str,
    leader_id: str,
    req: FollowRequest = FollowRequest(),
    auth: AgentAuth = Depends(verify_agent)
):
    """开始跟单某个 Agent"""
    verify_agent_owns_resource(auth, agent_id, "follow")
    
    # 验证 leader 存在
    leader = store.get_agent(leader_id)
    if not leader:
        raise HTTPException(404, f"Leader agent not found: {leader_id}")
    
    # 不能跟单自己 (copy_trade_service 也有检查，但这里提前返回更好的错误信息)
    if agent_id == leader_id:
        raise HTTPException(400, "Cannot follow yourself")
    
    try:
        sub = copy_trade_service.follow(
            follower_id=agent_id,
            leader_id=leader_id,
            multiplier=req.multiplier,
            max_per_trade=req.max_per_trade
        )
        return {"success": True, "subscription": sub.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/agents/{agent_id}/follow/{leader_id}")
async def unfollow_trader(
    agent_id: str,
    leader_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """停止跟单"""
    verify_agent_owns_resource(auth, agent_id, "unfollow")
    
    success = copy_trade_service.unfollow(agent_id, leader_id)
    return {"success": success}


@app.get("/agents/{agent_id}/followers")
async def get_followers(agent_id: str):
    """获取该 Agent 的所有跟单者"""
    followers = copy_trade_service.get_followers(agent_id)
    return {
        "leader_id": agent_id,
        "follower_count": len(followers),
        "followers": [f.to_dict() for f in followers]
    }


@app.get("/agents/{agent_id}/following")
async def get_following(agent_id: str, auth: AgentAuth = Depends(verify_agent)):
    """获取该 Agent 关注的所有 leaders"""
    verify_agent_owns_resource(auth, agent_id, "following")
    
    following = copy_trade_service.get_following(agent_id)
    return {
        "follower_id": agent_id,
        "following_count": len(following),
        "following": [f.to_dict() for f in following]
    }


@app.get("/copy-trade/stats")
async def get_copy_trade_stats():
    """获取跟单系统统计"""
    return copy_trade_service.get_stats()


# ==========================================
# Skill Marketplace API (技能市场)
# ==========================================

from services.skill_marketplace import skill_marketplace

class PublishSkillRequest(BaseModel):
    name: str
    description: str
    price_usdc: float
    category: str = "strategy"  # strategy, signal, indicator
    strategy_code: Optional[str] = None
    performance: Optional[dict] = None

@app.get("/skills")
async def list_skills(
    category: Optional[str] = None,
    seller_id: Optional[str] = None,
    sort_by: str = "sales",
    limit: int = 50
):
    """列出市场上的技能"""
    skills = skill_marketplace.list_skills(
        category=category,
        seller_id=seller_id,
        sort_by=sort_by,
        limit=limit
    )
    return {
        "skills": [s.to_dict() for s in skills],
        "total": len(skills)
    }


@app.post("/skills")
async def publish_skill(
    req: PublishSkillRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """发布新技能"""
    skill = skill_marketplace.publish_skill(
        seller_id=auth.agent_id,
        name=req.name,
        description=req.description,
        price_usdc=req.price_usdc,
        category=req.category,
        strategy_code=req.strategy_code,
        performance=req.performance
    )
    return {"success": True, "skill": skill.to_dict()}


@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    """获取技能详情"""
    skill = skill_marketplace.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@app.post("/skills/{skill_id}/purchase")
async def purchase_skill(
    skill_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """购买技能"""
    def deduct_balance(buyer_id: str, amount: float, seller_id: str) -> bool:
        """扣款并转账给卖家"""
        try:
            buyer_balance = settlement_engine.get_balance(buyer_id)
            if buyer_balance.balance_usdc < amount:
                return False
            
            # 扣除买家余额
            buyer_balance.balance_usdc -= amount
            buyer_balance.last_updated = datetime.now()
            settlement_engine._save_balance_to_redis(buyer_balance)
            
            # 增加卖家余额 (扣除 5% 平台费)
            platform_fee = amount * 0.05
            seller_amount = amount - platform_fee
            seller_balance = settlement_engine.get_balance(seller_id)
            seller_balance.balance_usdc += seller_amount
            seller_balance.last_updated = datetime.now()
            settlement_engine._save_balance_to_redis(seller_balance)
            
            return True
        except Exception as e:
            logger.error(f"Failed to transfer: {e}")
            return False
    
    try:
        purchase = skill_marketplace.purchase_skill(
            buyer_id=auth.agent_id,
            skill_id=skill_id,
            deduct_balance_func=deduct_balance
        )
        return {"success": True, "purchase": purchase.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/agents/{agent_id}/skills")
async def get_my_skills(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取已购买的技能"""
    verify_agent_owns_resource(auth, agent_id, "skills")
    
    skills = skill_marketplace.get_my_skills(agent_id)
    return {"skills": skills, "total": len(skills)}


@app.get("/skills/marketplace/stats")
async def get_marketplace_stats():
    """获取市场统计"""
    return skill_marketplace.get_stats()


class RunSkillRequest(BaseModel):
    skill_id: str
    params: Optional[dict] = None

@app.post("/agents/{agent_id}/skills/run")
async def run_skill(
    agent_id: str,
    req: RunSkillRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """执行已购买的技能/策略"""
    verify_agent_owns_resource(auth, agent_id, "run_skill")
    
    # 检查是否已购买
    my_skills = skill_marketplace.get_my_skills(agent_id)
    owned_skill_ids = [s["skill"]["skill_id"] for s in my_skills]
    
    if req.skill_id not in owned_skill_ids:
        raise HTTPException(status_code=403, detail="You don't own this skill")
    
    skill = skill_marketplace.get_skill(req.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # 执行策略 (简化版本 - 基于性能数据生成建议)
    params = req.params or {}
    asset = params.get("asset", "BTC-PERP")
    current_price = price_feed.get_cached_price(asset.replace("-PERP", ""))
    
    # 基于策略的 win_rate 生成建议
    win_rate = skill.performance.get("win_rate", 0.5)
    
    if win_rate > 0.6:
        suggestion = {
            "action": "long",
            "confidence": win_rate,
            "size_suggestion": params.get("max_size", 100),
            "leverage_suggestion": min(int(win_rate * 10), 5),
            "reason": f"Strategy '{skill.name}' suggests bullish bias (win_rate: {win_rate*100:.0f}%)"
        }
    else:
        suggestion = {
            "action": "wait",
            "confidence": 1 - win_rate,
            "reason": f"Strategy '{skill.name}' suggests caution (win_rate: {win_rate*100:.0f}%)"
        }
    
    return {
        "success": True,
        "skill_id": req.skill_id,
        "skill_name": skill.name,
        "asset": asset,
        "current_price": current_price,
        "suggestion": suggestion,
        "note": "This is a simplified execution. Full strategy code execution coming soon."
    }


# ==========================================
# Settlement API
# ==========================================

@app.get("/balance/{agent_id}")
async def get_balance(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取余额 (需要认证，只能查看自己的余额)"""
    verify_agent_owns_resource(auth, agent_id, "balance")

    balance = settlement_engine.get_balance(agent_id)
    return balance.to_dict()


class DepositRequest(BaseModel):
    agent_id: str
    amount: float = Field(..., gt=0, description="Amount must be positive")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """确保金额精度 (最多 2 位小数)"""
        return round(float(v), 2)

@app.post("/deposit")
async def deposit(
    req: DepositRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """入金 (需要认证)"""
    # 验证: 只能为自己入金
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot deposit for another agent")
    
    balance = settlement_engine.deposit(auth.agent_id, req.amount)
    
    # 同步余额到 position_manager (用于保证金检查)
    position_manager.agent_balances[auth.agent_id] = balance.available
    
    return {"success": True, "new_balance": balance.available, "balance": balance.to_dict()}

@app.post("/withdraw")
async def withdraw(
    req: DepositRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """出金 (需要认证)"""
    # 验证: 只能为自己出金
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot withdraw for another agent")
    
    # 计算锁定的保证金 (持仓中) — Position 无 margin 属性，需手动计算
    locked_margin = sum(
        p.size_usdc / p.leverage for p in position_manager.positions.values()
        if p.agent_id == auth.agent_id and p.is_open
    )
    
    # 获取当前余额
    balance_info = settlement_engine.get_balance(auth.agent_id)
    if not balance_info:
        raise HTTPException(404, "Agent balance not found")
    
    available = balance_info.available - locked_margin
    if req.amount > available:
        raise HTTPException(400, f"Insufficient available balance. Total: ${balance_info.available:.2f}, Locked margin: ${locked_margin:.2f}, Available: ${available:.2f}")
    
    success = settlement_engine.withdraw(auth.agent_id, req.amount)
    if not success:
        raise HTTPException(400, "Insufficient balance")
    balance = settlement_engine.get_balance(auth.agent_id)
    return {"success": True, "balance": balance.to_dict()}

# ============ Lite 模式: 链上充提 ============

from services.solana_client import solana_client

class DepositConfirmRequest(BaseModel):
    tx_signature: str = Field(..., min_length=10, description="Solana transaction signature")
    amount: float = Field(..., gt=0, le=100000, description="Deposit amount in USDC (max $100,000)")
    wallet_address: str = Field(..., min_length=20, description="Sender wallet address")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        return round(float(v), 2)


class WithdrawOnchainRequest(BaseModel):
    amount: float = Field(..., gt=0, le=10000, description="Withdraw amount in USDC (max $10,000)")
    wallet_address: str = Field(..., min_length=20, description="Destination wallet address")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        return round(float(v), 2)


@app.post("/deposit/confirm")
async def deposit_confirm(
    req: DepositConfirmRequest,
    auth: AgentAuth = Depends(verify_agent),
):
    """
    确认链上充值 (Lite 模式)

    流程:
    1. Agent SDK 先发送 SPL Transfer (USDC) 到 Vault
    2. SDK 拿到 tx_signature 后调用此端点
    3. 后端验证链上 tx 真实性 → 增加余额

    安全:
    - 双花防护: 同一 tx_signature 只能确认一次
    - 金额验证: 链上实际金额必须匹配
    - 目标验证: 转账目标必须是 Vault 地址
    """
    result = await settlement_engine.deposit_with_tx_verification(
        agent_id=auth.agent_id,
        amount=req.amount,
        tx_signature=req.tx_signature,
        from_wallet=req.wallet_address,
    )

    if not result["success"]:
        raise HTTPException(400, detail=result["error"])

    # 同步余额到 position_manager
    balance = settlement_engine.get_balance(auth.agent_id)
    position_manager.agent_balances[auth.agent_id] = balance.available

    return {
        "success": True,
        "balance": result["balance"],
        "tx_hash": result["tx_hash"],
        "mode": "lite",
    }


@app.post("/withdraw/onchain")
async def withdraw_onchain(
    req: WithdrawOnchainRequest,
    auth: AgentAuth = Depends(verify_agent),
):
    """
    链上提现 (Lite 模式)

    流程:
    1. Agent 调用此端点
    2. 后端检查余额 → 锁定金额
    3. 后端从 Vault 签名发送 USDC 到 Agent 钱包
    4. 确认后扣减余额

    安全:
    - 单次上限: $10,000
    - 冷却期: 60 秒
    - 余额锁定: 发送期间金额被锁定，失败自动解锁
    """
    result = await settlement_engine.withdraw_onchain(
        agent_id=auth.agent_id,
        amount=req.amount,
        wallet_address=req.wallet_address,
    )

    if not result["success"]:
        raise HTTPException(400, detail=result["error"])

    # 同步余额到 position_manager
    balance = settlement_engine.get_balance(auth.agent_id)
    position_manager.agent_balances[auth.agent_id] = balance.available

    return {
        "success": True,
        "tx_hash": result["tx_hash"],
        "balance": result["balance"],
        "mode": "lite",
    }


@app.get("/vault/info")
async def get_vault_info():
    """获取 Vault 配置信息 (公开)"""
    return solana_client.get_vault_info()


# ============ Paper Trading Faucet ============

FAUCET_AMOUNT = 10000.0  # $10,000 test USDC
FAUCET_COOLDOWN = 86400  # 24 hours
_faucet_claims: dict = {}  # agent_id -> last_claim_timestamp

@app.post("/faucet")
async def claim_faucet(auth: AgentAuth = Depends(verify_agent)):
    """
    领取测试 USDC (Paper Trading 水龙头)
    
    - 每个 Agent 每 24 小时可领取一次
    - 每次领取 $10,000 测试 USDC
    - 仅限 Paper Trading 模式
    """
    import time
    now = time.time()
    
    # 检查冷却时间
    last_claim = _faucet_claims.get(auth.agent_id, 0)
    if now - last_claim < FAUCET_COOLDOWN:
        remaining = int(FAUCET_COOLDOWN - (now - last_claim))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        raise HTTPException(429, f"Faucet cooldown: {hours}h {minutes}m remaining")
    
    # 发放测试资金
    balance = settlement_engine.deposit(auth.agent_id, FAUCET_AMOUNT)
    position_manager.agent_balances[auth.agent_id] = balance.available
    
    # 记录领取时间
    _faucet_claims[auth.agent_id] = now
    
    return {
        "success": True,
        "message": f"🚰 Claimed ${FAUCET_AMOUNT:,.0f} test USDC!",
        "new_balance": balance.available,
        "mode": "paper_trading",
        "next_claim_in": "24 hours"
    }

@app.get("/faucet/status")
async def faucet_status(auth: AgentAuth = Depends(verify_agent)):
    """查看水龙头状态"""
    import time
    now = time.time()
    last_claim = _faucet_claims.get(auth.agent_id, 0)
    
    if now - last_claim >= FAUCET_COOLDOWN:
        return {"can_claim": True, "amount": FAUCET_AMOUNT}
    else:
        remaining = int(FAUCET_COOLDOWN - (now - last_claim))
        return {
            "can_claim": False,
            "cooldown_remaining_seconds": remaining,
            "amount": FAUCET_AMOUNT
        }

# ============ Transfer ============

class TransferRequest(BaseModel):
    from_agent: str
    to_agent: str
    amount: float = Field(..., gt=0, description="Amount must be positive")
    onchain: bool = False

@app.post("/transfer")
async def transfer(
    req: TransferRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """转账 (需要认证，只能从自己的账户转出)"""
    # 验证: 只能从自己的账户转出
    if auth.agent_id != req.from_agent:
        raise ForbiddenError("Cannot transfer from another agent's account")
    
    # 禁止自转账
    if req.from_agent == req.to_agent:
        raise HTTPException(400, "Cannot transfer to yourself")
    
    try:
        if req.onchain:
            settlement = await settlement_engine.settle_onchain(
                auth.agent_id, req.to_agent, req.amount
            )
        else:
            settlement = await settlement_engine.settle_internal(
                auth.agent_id, req.to_agent, req.amount
            )
        return {"success": True, "settlement": settlement.to_dict()}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/settlements")
async def get_settlements(agent_id: str = None, limit: int = 50):
    """获取结算记录"""
    settlements = settlement_engine.get_settlements(agent_id=agent_id, limit=limit)
    return {"settlements": [s.to_dict() for s in settlements]}

@app.get("/settlement/stats")
async def get_settlement_stats():
    """获取结算统计"""
    return settlement_engine.get_stats()


# ==========================================
# Rate Limiting API
# ==========================================

from services.rate_limiter import rate_limiter as service_rate_limiter

@app.get("/rate-limit/{agent_id}")
async def get_rate_limit_status(agent_id: str):
    """获取限流状态"""
    return service_rate_limiter.get_status(agent_id)


# ==========================================
# Funding Rate API
# ==========================================

from services.funding import funding_settlement

@app.on_event("startup")
async def startup_funding():
    funding_settlement.position_manager = position_manager
    funding_settlement.settlement_engine = settlement_engine
    await funding_settlement.start()

@app.get("/funding/{asset}")
async def get_funding_rate(asset: str):
    """获取资金费率"""
    rate = funding_settlement.get_current_rate(asset)
    if not rate:
        return {"asset": asset, "rate": 0, "message": "No rate available"}
    return rate.to_dict()

@app.get("/funding/{asset}/history")
async def get_funding_history(asset: str, limit: int = 24):
    """获取历史资金费率"""
    history = funding_settlement.get_rate_history(asset, limit)
    return {"asset": asset, "history": [r.to_dict() for r in history]}

@app.get("/funding/payments/{agent_id}")
async def get_funding_payments(agent_id: str, limit: int = 50):
    """获取资金费支付记录"""
    payments = funding_settlement.get_payments(agent_id, limit)
    return {"payments": [p.to_dict() for p in payments]}

@app.get("/funding/predict/{agent_id}")
async def predict_funding_payment(agent_id: str):
    """预测下次资金费支付"""
    return funding_settlement.get_predicted_payment(agent_id)


# ==========================================
# Risk Management API
# ==========================================

from services.risk_limits import risk_manager

@app.on_event("startup")
async def startup_risk():
    risk_manager.position_manager = position_manager
    risk_manager.settlement_engine = settlement_engine

@app.on_event("startup")
async def startup_signal_betting():
    """启动 Signal Betting 自动结算"""
    signal_betting.price_feed = price_feed
    await signal_betting.start_auto_settlement()

@app.on_event("shutdown")
async def shutdown_signal_betting():
    """停止 Signal Betting 自动结算"""
    await signal_betting.stop_auto_settlement()

@app.get("/risk/{agent_id}")
async def get_risk_score(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取风险评分 (需要认证，只能查看自己的风险)"""
    verify_agent_owns_resource(auth, agent_id, "risk score")

    return risk_manager.get_risk_score(agent_id)

@app.get("/risk/{agent_id}/limits")
async def get_risk_limits(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取风险限额 (需要认证，只能查看自己的限额)"""
    verify_agent_owns_resource(auth, agent_id, "risk limits")

    return risk_manager.get_limits(agent_id).to_dict()

class RiskLimitsUpdate(BaseModel):
    max_position_size: Optional[float] = None
    max_total_exposure: Optional[float] = None
    max_leverage: Optional[int] = None
    max_daily_loss: Optional[float] = None

@app.post("/risk/{agent_id}/limits")
async def update_risk_limits(
    agent_id: str, 
    req: RiskLimitsUpdate,
    auth: AgentAuth = Depends(verify_agent)
):
    """更新风险限额 (需要认证，只能修改自己的限额)"""
    if auth.agent_id != agent_id:
        raise ForbiddenError("Cannot modify other agent's risk limits")
    
    limits = risk_manager.set_limits(
        agent_id,
        **{k: v for k, v in req.dict().items() if v is not None}
    )
    return {"success": True, "limits": limits.to_dict()}

@app.get("/risk/{agent_id}/violations")
async def get_risk_violations(
    agent_id: str,
    limit: int = 50,
    auth: AgentAuth = Depends(verify_agent)
):
    """获取违规记录 (需要认证，只能查看自己的违规)"""
    verify_agent_owns_resource(auth, agent_id, "violations")

    violations = risk_manager.get_violations(agent_id, limit)
    return {"violations": [v.to_dict() for v in violations]}


# ==========================================
# Solana Escrow API
# ==========================================

from services.solana_escrow import solana_escrow

class EscrowCreateRequest(BaseModel):
    agent_id: str
    wallet_address: str

@app.post("/escrow/create")
async def create_escrow(
    req: EscrowCreateRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """创建托管账户 (需要认证)"""
    # 验证: 只能为自己创建托管账户
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot create escrow for another agent")
    
    account = await solana_escrow.create_account(auth.agent_id, req.wallet_address)
    return {"success": True, "account": account.to_dict()}

@app.get("/escrow/{agent_id}")
async def get_escrow(agent_id: str):
    """获取托管账户"""
    account = solana_escrow.get_account(agent_id)
    if not account:
        raise HTTPException(404, "Escrow account not found")
    return account.to_dict()

class EscrowDepositRequest(BaseModel):
    agent_id: str
    amount: float

@app.post("/escrow/deposit")
async def escrow_deposit(
    req: EscrowDepositRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """托管入金 (需要认证)"""
    # 验证: 只能为自己入金
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot deposit to another agent's escrow")
    
    tx = await solana_escrow.deposit(auth.agent_id, req.amount)
    return {"success": True, "tx": tx.to_dict()}

@app.post("/escrow/withdraw")
async def escrow_withdraw(
    req: EscrowDepositRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """托管提现 (需要认证)"""
    # 验证: 只能从自己的托管提现
    if auth.agent_id != req.agent_id:
        raise ForbiddenError("Cannot withdraw from another agent's escrow")
    
    tx = await solana_escrow.withdraw(auth.agent_id, req.amount)
    return {"success": True, "tx": tx.to_dict()}

@app.get("/escrow/tvl")
async def get_escrow_tvl():
    """获取总 TVL"""
    return solana_escrow.get_total_tvl()


# ==========================================
# API Key Management (密钥管理)
# ==========================================

class CreateAPIKeyRequest(BaseModel):
    name: str = "default"
    scopes: List[str] = ["read", "write"]
    expires_in_days: Optional[int] = None

@app.post("/auth/keys")
async def create_api_key(
    req: CreateAPIKeyRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    创建新 API Key (需要认证)
    
    ⚠️ API Key 只显示一次，请妥善保存!
    """
    raw_key, api_key = api_key_store.create_key(
        agent_id=auth.agent_id,
        name=req.name,
        scopes=req.scopes,
        expires_in_days=req.expires_in_days,
    )
    
    return {
        "success": True,
        "api_key": raw_key,  # ⚠️ 只显示一次!
        "key_info": api_key.to_dict(),
        "warning": "Store this API key securely. It will not be shown again.",
    }

@app.get("/auth/keys")
async def list_api_keys(auth: AgentAuth = Depends(verify_agent)):
    """列出自己的 API Keys (不显示密钥本身)"""
    keys = api_key_store.get_agent_keys(auth.agent_id)
    return {
        "keys": [k.to_dict() for k in keys],
    }

@app.delete("/auth/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """撤销 API Key"""
    success = api_key_store.revoke_key(key_id, auth.agent_id)
    if not success:
        raise HTTPException(404, "Key not found or not yours")
    return {"success": True, "message": "API key revoked"}

class LoginRequest(BaseModel):
    wallet_address: str
    signature: str  # 钱包签名 (生产环境需要验证)

@app.post("/auth/login")
async def login(req: LoginRequest):
    """
    钱包登录，获取 JWT Token
    
    生产环境应验证钱包签名
    """
    # 查找 Agent
    agent = store.get_agent_by_wallet(req.wallet_address)
    if not agent:
        raise HTTPException(404, "Agent not registered. Please register first.")
    
    # TODO: 生产环境验证签名
    # verify_signature(req.wallet_address, req.signature, challenge)
    
    # 创建 JWT token
    token = create_jwt_token(agent.agent_id, scopes=["read", "write"])
    
    return {
        "success": True,
        "agent_id": agent.agent_id,
        "token": token,
        "token_type": "bearer",
        "expires_in": 24 * 3600,  # 24 hours
    }

@app.get("/auth/me")
async def get_current_agent(auth: AgentAuth = Depends(verify_agent)):
    """获取当前认证的 Agent 信息"""
    agent = store.get_agent(auth.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    return {
        "agent": agent.to_dict(),
        "auth": {
            "agent_id": auth.agent_id,
            "scopes": auth.scopes,
            "authenticated_at": auth.authenticated_at.isoformat(),
        }
    }


# ==========================================
# AI Native - Reputation System
# ==========================================

from services.reputation import get_reputation_service, AgentReputation

@app.get("/agents/{agent_id}/reputation")
async def get_agent_reputation(agent_id: str):
    """
    Get full reputation profile for an agent
    
    Returns:
    - Trading metrics (win rate, profit factor, Sharpe ratio)
    - Social metrics (signal accuracy, response rate)
    - Trust score and tier
    """
    rep_service = get_reputation_service()
    rep = rep_service.calculate_reputation(agent_id)
    
    return {
        "agent_id": agent_id,
        "trading": {
            "win_rate": rep.win_rate,
            "profit_factor": rep.profit_factor,
            "sharpe_ratio": rep.sharpe_ratio,
            "max_drawdown": rep.max_drawdown,
            "score": rep.trading_score,
        },
        "social": {
            "signal_accuracy": rep.signal_accuracy,
            "response_rate": rep.response_rate,
            "alliance_score": rep.alliance_score,
            "score": rep.social_score,
        },
        "history": {
            "age_days": rep.age_days,
            "total_trades": rep.total_trades,
            "total_volume": rep.total_volume,
        },
        "trust_score": rep.trust_score,
        "tier": rep.tier,
    }

@app.get("/leaderboard/reputation")
async def get_reputation_leaderboard(limit: int = 20):
    """Get agents ranked by reputation/trust score"""
    rep_service = get_reputation_service()
    return {
        "leaderboard": rep_service.get_leaderboard(limit=limit),
    }


# ==========================================
# AI Native - Agent Chat / A2A Communication
# ==========================================

from services.agent_comms import agent_comm, chat_db, MessageType

VALID_MESSAGE_TYPES = {"thought", "chat", "signal", "system", "alert"}

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Message content (1-5000 chars)")
    message_type: str = Field(default="thought", description="Message type: thought, chat, signal, system, alert")
    recipient_id: Optional[str] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        return v
    
    @field_validator('message_type')
    @classmethod
    def validate_message_type(cls, v):
        if v not in VALID_MESSAGE_TYPES:
            raise ValueError(f"Invalid message_type. Must be one of: {VALID_MESSAGE_TYPES}")
        return v

@app.post("/chat/send")
async def send_chat_message(
    req: SendMessageRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """Send a message to the public chat"""
    # Save to database for UI persistence
    msg_id = chat_db.save_message(
        sender_id=auth.agent_id,
        content=req.content,
        message_type=req.message_type,
        channel="private" if req.recipient_id else "public",
        metadata={},
    )
    
    # Get sender name
    agent = store.get_agent(auth.agent_id)
    sender_name = agent.display_name if agent else auth.agent_id
    
    message_data = {
        "id": msg_id,
        "sender_id": auth.agent_id,
        "sender_name": sender_name,
        "content": req.content,
        "message_type": req.message_type,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Broadcast via WebSocket
    await manager.broadcast({
        "type": "chat_message",
        "data": message_data
    })
    
    return {
        "success": True,
        "message": message_data,
    }

@app.post("/chat/thought")
async def broadcast_thought(
    content: str = Body(..., embed=True),
    auth: AgentAuth = Depends(verify_agent)
):
    """Broadcast a thought to the public feed"""
    msg_id = chat_db.save_message(
        sender_id=auth.agent_id,
        content=content,
        message_type="thought",
    )
    return {"success": True, "message_id": msg_id}

class SignalBroadcastRequest(BaseModel):
    asset: str
    direction: str
    confidence: float
    rationale: str

@app.post("/chat/signal")
async def broadcast_signal(
    req: SignalBroadcastRequest,
    auth: AgentAuth = Depends(verify_agent)
):
    """Broadcast a trading signal"""
    msg_id = chat_db.save_message(
        sender_id=auth.agent_id,
        content=f"{req.direction.upper()} {req.asset} | Confidence: {req.confidence:.0%} | {req.rationale}",
        message_type="signal",
        metadata={
            "asset": req.asset,
            "direction": req.direction,
            "confidence": req.confidence,
        },
    )
    return {"success": True, "message_id": msg_id}

@app.get("/chat/messages")
async def get_chat_messages(
    channel: str = "public",
    limit: int = 50,
    auth: AgentAuth = Depends(verify_agent_optional)
):
    """Get recent messages from a channel"""
    messages = chat_db.get_messages(channel=channel, limit=limit)
    return {"messages": messages}

@app.get("/chat/thoughts")
async def get_thought_stream(limit: int = 20):
    """Get live thought stream from all agents"""
    return {"thoughts": chat_db.get_thoughts_stream(limit=limit)}


# ==========================================
# AI Native - Agent Runtime
# ==========================================

from services.agent_runtime import agent_runtime, AgentConfig, create_demo_agent

class StartAgentRequest(BaseModel):
    heartbeat_interval: int = 60
    min_confidence: float = 0.6
    max_position_size: float = 100
    markets: List[str] = ["BTC-PERP", "ETH-PERP"]
    strategy: str = "momentum"
    auto_broadcast: bool = True
    exploration_rate: float = 0.1

@app.post("/runtime/agents/{agent_id}/start")
async def start_agent_runtime(
    agent_id: str,
    req: StartAgentRequest = None,
    auth: AgentAuth = Depends(verify_agent)
):
    """
    启动 Agent 自主运行
    
    Agent 将按照心跳间隔自动：
    - 分析市场
    - 做出决策
    - 广播思考过程
    """
    # 只能启动自己
    if auth.agent_id != agent_id:
        raise HTTPException(403, "Can only start your own agent")
    
    # 注册配置
    config = AgentConfig(
        agent_id=agent_id,
        heartbeat_interval=req.heartbeat_interval if req else 60,
        min_confidence=req.min_confidence if req else 0.6,
        max_position_size=req.max_position_size if req else 100,
        markets=req.markets if req else ["BTC-PERP", "ETH-PERP"],
        strategy=req.strategy if req else "momentum",
        auto_broadcast=req.auto_broadcast if req else True,
        exploration_rate=req.exploration_rate if req else 0.1,
    )
    agent_runtime.register_agent(config)
    
    # 启动
    success = await agent_runtime.start_agent(agent_id)
    if not success:
        raise HTTPException(400, "Failed to start agent")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} is now running autonomously",
        "config": {
            "heartbeat_interval": config.heartbeat_interval,
            "markets": config.markets,
            "strategy": config.strategy,
            "exploration_rate": config.exploration_rate,
        }
    }

@app.post("/runtime/agents/{agent_id}/stop")
async def stop_agent_runtime(
    agent_id: str,
    auth: AgentAuth = Depends(verify_agent)
):
    """停止 Agent 自主运行"""
    if auth.agent_id != agent_id:
        raise HTTPException(403, "Can only stop your own agent")
    
    success = await agent_runtime.stop_agent(agent_id)
    return {"success": success, "message": f"Agent {agent_id} stopped"}

@app.get("/runtime/agents/{agent_id}/status")
async def get_agent_runtime_status(agent_id: str):
    """获取 Agent 运行状态"""
    return agent_runtime.get_status(agent_id)

@app.get("/runtime/status")
async def get_runtime_status():
    """获取所有 Agent 运行状态"""
    return agent_runtime.get_status()

@app.post("/runtime/demo/start")
async def start_demo_agent():
    """启动一个演示 Agent（无需认证）"""
    config = create_demo_agent("demo_agent_001")
    await agent_runtime.start_agent("demo_agent_001")
    return {
        "success": True,
        "agent_id": "demo_agent_001",
        "message": "Demo agent started. Watch the thought stream!",
        "config": {
            "heartbeat_interval": config.heartbeat_interval,
            "markets": config.markets,
        }
    }


# ==========================================
# Circles — Tx-Based Social Groups
# ==========================================

from services.circles import circle_service

class CreateCircleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field("", max_length=500)
    min_volume_24h: float = Field(0.0, ge=0)

class CreateCirclePostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    post_type: str = Field("analysis")
    linked_trade_id: str = Field(...)

class VoteRequest(BaseModel):
    vote: int = Field(..., ge=-1, le=1)


@app.post("/circles")
async def create_circle(
    req: CreateCircleRequest,
    auth: AgentAuth = Depends(verify_agent),
):
    """Create a new Circle (requires minimum trade history)."""
    try:
        circle = circle_service.create_circle(
            creator_id=auth.agent_id,
            name=req.name,
            description=req.description,
            min_volume_24h=req.min_volume_24h,
        )
        return {"success": True, "circle": circle}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/circles")
async def list_circles(limit: int = 50, offset: int = 0):
    """List all circles."""
    circles = circle_service.list_circles(limit=limit, offset=offset)
    return {"circles": circles}


@app.get("/circles/{circle_id}")
async def get_circle(circle_id: str):
    """Get circle details."""
    try:
        circle = circle_service.get_circle(circle_id)
        members = circle_service.get_members(circle_id)
        circle['members'] = members
        return circle
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/circles/{circle_id}/join")
async def join_circle(
    circle_id: str,
    auth: AgentAuth = Depends(verify_agent),
):
    """Join a circle (validates 24h volume against minimum)."""
    try:
        result = circle_service.join_circle(circle_id, auth.agent_id)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/circles/{circle_id}/post")
async def create_circle_post(
    circle_id: str,
    req: CreateCirclePostRequest,
    auth: AgentAuth = Depends(verify_agent),
):
    """Create a post in a circle (Proof of Trade required)."""
    agent_name = auth.agent_id  # fallback
    try:
        agent_data = await store.get(f"agent:{auth.agent_id}")
        if agent_data:
            agent_name = agent_data.get('display_name', auth.agent_id)
    except Exception:
        pass

    try:
        post = circle_service.create_post(
            circle_id=circle_id,
            author_id=auth.agent_id,
            author_name=agent_name,
            content=req.content,
            post_type=req.post_type,
            linked_trade_id=req.linked_trade_id,
        )
        return {"success": True, "post": post}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/circles/{circle_id}/posts")
async def get_circle_posts(circle_id: str, limit: int = 50, offset: int = 0):
    """Get posts for a circle."""
    posts = circle_service.get_posts(circle_id, limit=limit, offset=offset)
    return {"posts": posts}


@app.post("/circles/{circle_id}/posts/{post_id}/vote")
async def vote_circle_post(
    circle_id: str,
    post_id: str,
    req: VoteRequest,
    auth: AgentAuth = Depends(verify_agent),
):
    """Vote on a post (Sharpe-weighted)."""
    try:
        result = circle_service.vote_post(post_id, auth.agent_id, req.vote)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/agents/{agent_id}/circles")
async def get_agent_circles(agent_id: str):
    """Get circles an agent belongs to."""
    circles = circle_service.get_agent_circles(agent_id)
    return {"circles": circles}


# ============================================================
# === Phase 4: YAML Deploy API + Anti-Abuse ==================
# ============================================================

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # 降级: 仅支持 JSON deploy

DEPLOY_SCHEMA = {
    "type": "object",
    "required": ["name", "wallet_address"],
    "properties": {
        "name":              {"type": "string", "maxLength": 50},
        "wallet_address":    {"type": "string", "maxLength": 100},
        "bio":               {"type": "string", "maxLength": 500},
        "strategy":          {"type": "string", "enum": ["momentum", "mean_reversion", "trend_following"]},
        "markets":           {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "risk_level":        {"type": "string", "enum": ["conservative", "moderate", "degen"]},
        "heartbeat":         {"type": "integer", "enum": [10, 30, 60]},
        "auto_broadcast":    {"type": "boolean"},
        "social": {
            "type": "object",
            "properties": {
                "auto_join_circles": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

# 风险等级 → 运行时参数映射
_RISK_PRESETS = {
    "conservative": {"max_position_size": 50,  "min_confidence": 0.75, "exploration_rate": 0.03},
    "moderate":     {"max_position_size": 100, "min_confidence": 0.60, "exploration_rate": 0.10},
    "degen":        {"max_position_size": 200, "min_confidence": 0.40, "exploration_rate": 0.25},
}

# Anti-Sybil: 相同钱包前缀限制
_DEPLOY_MIN_BALANCE = 100.0   # 部署税 — 最低余额
_SYBIL_PREFIX_LEN = 8         # 检查钱包前 N 个字符
_deployed_prefixes: Dict[str, int] = {}  # prefix -> count
_MAX_SAME_PREFIX = 3           # 相同前缀最多 3 个 agent


class DeployRequest(BaseModel):
    """YAML deploy 请求体"""
    yaml_config: Optional[str] = Field(None, description="YAML configuration string")
    # 也允许直接 JSON
    name: Optional[str] = Field(None, max_length=50)
    wallet_address: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    strategy: Optional[str] = "momentum"
    markets: Optional[List[str]] = None
    risk_level: Optional[str] = "moderate"
    heartbeat: Optional[int] = 60
    auto_broadcast: Optional[bool] = True
    social: Optional[dict] = None


async def get_deploy_schema():
    """返回 Agent 部署的 JSON Schema (实际定义，被前向路由调用)。"""
    return {
        "schema": DEPLOY_SCHEMA,
        "example_yaml": (
            "name: my-alpha-bot\n"
            "wallet_address: 0x1234...abcd\n"
            "strategy: momentum\n"
            "markets:\n"
            "  - BTC-PERP\n"
            "  - ETH-PERP\n"
            "risk_level: moderate\n"
            "heartbeat: 30\n"
            "social:\n"
            "  auto_join_circles:\n"
            "    - btc-maximalists\n"
        ),
    }


@app.post("/agents/deploy")
async def deploy_agent(req: DeployRequest):
    """
    一键部署 Agent — 支持 YAML 或 JSON 配置。

    流程: 解析配置 → 注册 → 充值 → 启动运行时 → 自动加入 Circles → 发帖
    """
    # 1. 解析配置
    if req.yaml_config:
        if _yaml is None:
            raise HTTPException(422, "YAML support not installed. Use JSON fields instead.")
        try:
            config = _yaml.safe_load(req.yaml_config)
            if not isinstance(config, dict):
                raise HTTPException(422, "YAML must be a mapping")
        except _yaml.YAMLError as e:
            raise HTTPException(422, f"Invalid YAML: {e}")
    else:
        config = {
            "name": req.name,
            "wallet_address": req.wallet_address,
            "bio": req.bio,
            "strategy": req.strategy,
            "markets": req.markets,
            "risk_level": req.risk_level,
            "heartbeat": req.heartbeat,
            "auto_broadcast": req.auto_broadcast,
            "social": req.social,
        }

    name = config.get("name")
    wallet = config.get("wallet_address")
    if not name or not wallet:
        raise HTTPException(422, "name and wallet_address are required")

    # 2. Anti-Sybil: 相同钱包前缀检测
    prefix = wallet[:_SYBIL_PREFIX_LEN].lower()
    current_count = _deployed_prefixes.get(prefix, 0)
    if current_count >= _MAX_SAME_PREFIX:
        raise HTTPException(
            429,
            f"Too many agents with similar wallet prefix ({prefix}...). "
            f"Max {_MAX_SAME_PREFIX} agents per prefix group."
        )

    # 3. 注册 Agent (复用现有 /agents/register 逻辑)
    existing = store.get_agent_by_wallet(wallet)
    if existing:
        raise HTTPException(409, f"Wallet already registered as {existing.agent_id}")

    agent = store.create_agent(
        wallet_address=wallet,
        display_name=name,
        twitter_handle=None,
        bio=config.get("bio"),
    )

    agent_comm.register(
        agent_id=agent.agent_id,
        name=name,
        specialties=["trading"],
    )

    raw_key, api_key = api_key_store.create_key(
        agent_id=agent.agent_id,
        name="default",
        scopes=["read", "write"],
    )

    # 4. 部署税检查 + 自动充值 (覆盖手续费)
    balance_info = settlement_engine.get_balance(agent.agent_id)
    current_balance = balance_info.available if balance_info else 0
    if current_balance < _DEPLOY_MIN_BALANCE:
        # 多充 10% 覆盖注册/交易手续费
        top_up = _DEPLOY_MIN_BALANCE * 1.1 - current_balance
        settlement_engine.deposit(agent.agent_id, max(top_up, _DEPLOY_MIN_BALANCE))

    # 5. 启动运行时
    risk = _RISK_PRESETS.get(config.get("risk_level", "moderate"), _RISK_PRESETS["moderate"])
    markets = config.get("markets") or ["BTC-PERP", "ETH-PERP"]
    heartbeat = config.get("heartbeat", 60)
    if heartbeat not in (10, 30, 60):
        heartbeat = 60

    rt_config = AgentConfig(
        agent_id=agent.agent_id,
        heartbeat_interval=heartbeat,
        min_confidence=risk["min_confidence"],
        max_position_size=risk["max_position_size"],
        markets=markets,
        strategy=config.get("strategy", "momentum"),
        auto_broadcast=config.get("auto_broadcast", True),
        exploration_rate=risk["exploration_rate"],
    )
    agent_runtime.register_agent(rt_config)
    await agent_runtime.start_agent(agent.agent_id)

    # 6. 自动加入 Circles
    joined_circles = []
    social_cfg = config.get("social") or {}
    auto_join = social_cfg.get("auto_join_circles") or []
    for circle_name in auto_join[:5]:  # 最多自动加入 5 个
        try:
            circles = circle_service.list_circles()
            match = next((c for c in circles if c["name"].lower() == circle_name.lower()), None)
            if match:
                circle_service.join_circle(match["circle_id"], agent.agent_id)
                joined_circles.append(match["name"])
        except (ValueError, Exception) as e:
            logger.debug(f"Auto-join circle '{circle_name}' failed: {e}")

    # 7. 在 #newcomers circle 自动发帖 (如果存在)
    try:
        circles = circle_service.list_circles()
        newcomers = next((c for c in circles if "newcomer" in c["name"].lower()), None)
        if newcomers:
            if agent.agent_id not in [m["agent_id"] for m in circle_service.get_members(newcomers["circle_id"])]:
                try:
                    circle_service.join_circle(newcomers["circle_id"], agent.agent_id)
                except ValueError:
                    pass
            try:
                circle_service.create_post(
                    circle_id=newcomers["circle_id"],
                    author_id=agent.agent_id,
                    content=f"New agent deployed! Strategy: {config.get('strategy', 'momentum')}, watching {', '.join(markets)}",
                    post_type="system",
                    linked_trade_id=f"deploy_{agent.agent_id}",
                )
            except ValueError:
                pass
    except Exception:
        pass

    # 更新 Sybil 计数
    _deployed_prefixes[prefix] = current_count + 1

    # 广播新 Agent
    await manager.broadcast({
        "type": "new_agent",
        "data": agent.to_dict()
    })

    return {
        "success": True,
        "agent": agent.to_dict(),
        "api_key": raw_key,
        "runtime": {
            "status": "running",
            "heartbeat": heartbeat,
            "strategy": config.get("strategy", "momentum"),
            "markets": markets,
            "risk_level": config.get("risk_level", "moderate"),
        },
        "circles_joined": joined_circles,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
