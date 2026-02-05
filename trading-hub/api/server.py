"""
Trading Hub - API Server
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio
import json
import uvicorn

import sys
sys.path.append('..')
from db.store import store
from api.models import IntentType, IntentStatus, AgentStatus
from services.price_feed import PriceFeed, price_feed
from services.pnl_tracker import pnl_tracker
from services.external_router import external_router, RoutingResult

app = FastAPI(title="Trading Hub", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# === Request Models ===

class RegisterRequest(BaseModel):
    wallet_address: str
    display_name: Optional[str] = None
    twitter_handle: Optional[str] = None

from pydantic import Field, field_validator

VALID_ASSETS = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]

class IntentRequest(BaseModel):
    agent_id: str
    intent_type: str  # "long" | "short"
    asset: str = "ETH-PERP"
    size_usdc: float = Field(default=100, gt=0, description="Size must be > 0")
    leverage: int = Field(default=1, ge=1, le=100, description="Leverage 1-100x")
    max_slippage: float = 0.005
    
    @field_validator('asset')
    @classmethod
    def validate_asset(cls, v):
        if v not in VALID_ASSETS:
            raise ValueError(f"Invalid asset. Must be one of: {VALID_ASSETS}")
        return v

class MatchRequest(BaseModel):
    intent_id: str

# === API Endpoints ===

@app.on_event("startup")
async def startup():
    """启动时初始化服务"""
    await price_feed.start()
    await external_router.start()
    
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
    
    return {
        **base_stats,
        "external_routed": router_stats["total_routed"],
        "external_volume": router_stats["total_volume"],
        "external_fees": router_stats["total_fees"],
        "internal_match_rate": f"{internal_rate:.1%}",
        "fee_saved_total": round(total_internal * 0.00025, 4),
    }

# --- Agent ---

@app.post("/agents/register")
async def register_agent(req: RegisterRequest):
    """注册 Agent (钱包签名)"""
    agent = store.create_agent(
        wallet_address=req.wallet_address,
        display_name=req.display_name,
        twitter_handle=req.twitter_handle,
    )
    
    # 同时注册到通讯系统
    agent_comm.register(
        agent_id=agent.agent_id,
        name=req.display_name or agent.agent_id,
        specialties=["trading"],
    )
    
    # 广播新 Agent
    await manager.broadcast({
        "type": "new_agent",
        "data": agent.to_dict()
    })
    
    return {"success": True, "agent": agent.to_dict()}

# 注意: /agents/discover 必须在 /agents/{agent_id} 之前，否则会被拦截
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
    return agent.to_dict()

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

# --- Intent ---

@app.post("/intents")
async def create_intent(req: IntentRequest):
    """
    发布交易意图 - Dark Pool 逻辑
    
    1. 先尝试内部匹配 (0 fee)
    2. 如果部分匹配，剩余路由到外部 (HL fee)
    3. 如果完全没匹配，全部路由到外部
    """
    intent_type = IntentType(req.intent_type)
    
    intent = store.create_intent(
        agent_id=req.agent_id,
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
    
    # === 计算结果 ===
    internal_rate = internal_filled / total_size if total_size > 0 else 0
    fee_saved = internal_filled * 0.00025  # 0.025% HL fee
    total_fee = sum(f.fee for f in external_fills)
    
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
        except ValueError as e:
            # 风控拒绝，但 Intent 已创建
            position_data = {"error": str(e)}
    else:
        position_data = None
    
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
        "internal_match": internal_match.to_dict() if internal_match else None,
        "external_fills": [f.to_dict() for f in external_fills],
        "position": position_data,
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

@app.delete("/intents/{intent_id}")
async def cancel_intent(intent_id: str):
    """取消 Intent"""
    intent = store.update_intent(intent_id, status=IntentStatus.CANCELLED)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
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
    """生成模拟数据"""
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
    duration_hours: int = Field(default=24, ge=1, le=168, description="Duration 1-168 hours")
    
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

@app.post("/signals")
async def create_signal(req: CreateSignalRequest):
    """
    创建预测信号
    
    示例: "ETH 24h 后 > $2200, 押注 $50"
    """
    try:
        signal_type = SignalType(req.signal_type)
    except ValueError:
        raise HTTPException(400, f"Invalid signal_type. Use: price_above, price_below, price_change")
    
    # 验证 Agent
    agent = store.get_agent(req.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    try:
        signal = signal_betting.create_signal(
            creator_id=req.agent_id,
            asset=req.asset,
            signal_type=signal_type,
            target_value=req.target_value,
            stake_amount=req.stake_amount,
            duration_hours=req.duration_hours,
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
async def fade_signal(req: FadeSignalRequest):
    """
    Fade 一个 Signal (对赌)
    
    押注相同金额，认为 Signal 预测错误
    """
    agent = store.get_agent(req.fader_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    try:
        bet = signal_betting.fade_signal(req.signal_id, req.fader_id)
        
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
async def settle_bet(bet_id: str, price: float = None):
    """
    结算对赌
    
    需要提供结算价格，或者使用当前价格
    """
    try:
        # 获取当前价格
        if price is None:
            bet = signal_betting.bets.get(bet_id)
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
    await position_manager.start()

@app.get("/positions/{agent_id}")
async def get_positions(agent_id: str):
    """获取 Agent 的持仓"""
    positions = position_manager.get_positions(agent_id)
    
    # 更新价格 (使用同步缓存方法)
    for pos in positions:
        asset = pos.asset.replace("-PERP", "")
        price = price_feed.get_cached_price(asset)
        pos.update_pnl(price)
    
    return {
        "agent_id": agent_id,
        "positions": [p.to_dict() for p in positions],
    }

@app.get("/portfolio/{agent_id}")
async def get_portfolio(agent_id: str):
    """获取投资组合概览"""
    # 先更新所有价格 (使用同步缓存方法)
    for pos in position_manager.get_positions(agent_id):
        asset = pos.asset.replace("-PERP", "")
        price = price_feed.get_cached_price(asset)
        pos.update_pnl(price)
    
    return position_manager.get_portfolio_value(agent_id)

class StopLossRequest(BaseModel):
    price: float

@app.post("/positions/{position_id}/stop-loss")
async def set_stop_loss(position_id: str, req: StopLossRequest):
    """设置止损"""
    try:
        position_manager.set_stop_loss(position_id, req.price)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/positions/{position_id}/take-profit")
async def set_take_profit(position_id: str, req: StopLossRequest):
    """设置止盈"""
    try:
        position_manager.set_take_profit(position_id, req.price)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/positions/{position_id}/close")
async def close_position(position_id: str):
    """手动平仓"""
    try:
        pos = position_manager.positions.get(position_id)
        if not pos:
            raise ValueError("Position not found")
        
        asset = pos.asset.replace("-PERP", "")
        price = price_feed.get_price(asset)
        pos = position_manager.close_position_manual(position_id, price)
        
        return {
            "success": True,
            "position_id": position_id,
            "close_price": price,
            "pnl": pos.realized_pnl,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))

# ==========================================
# Risk Alerts API (风控告警)
# ==========================================

@app.get("/alerts/{agent_id}")
async def get_alerts(agent_id: str):
    """获取风控告警"""
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
async def acknowledge_alert(alert_id: str):
    """确认告警"""
    position_manager.acknowledge_alert(alert_id)
    return {"success": True}

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
async def share_signal(req: SignalShareRequest):
    """分享交易信号"""
    msg_id = await agent_comm.share_signal(
        from_agent=req.agent_id,
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
# Settlement API
# ==========================================

@app.get("/balance/{agent_id}")
async def get_balance(agent_id: str):
    """获取余额"""
    balance = settlement_engine.get_balance(agent_id)
    return balance.to_dict()

from pydantic import Field

class DepositRequest(BaseModel):
    agent_id: str
    amount: float = Field(..., gt=0, description="Amount must be positive")

@app.post("/deposit")
async def deposit(req: DepositRequest):
    """入金"""
    balance = settlement_engine.deposit(req.agent_id, req.amount)
    return {"success": True, "balance": balance.to_dict()}

@app.post("/withdraw")
async def withdraw(req: DepositRequest):
    """出金"""
    success = settlement_engine.withdraw(req.agent_id, req.amount)
    if not success:
        raise HTTPException(400, "Insufficient balance")
    balance = settlement_engine.get_balance(req.agent_id)
    return {"success": True, "balance": balance.to_dict()}

class TransferRequest(BaseModel):
    from_agent: str
    to_agent: str
    amount: float = Field(..., gt=0, description="Amount must be positive")
    onchain: bool = False

@app.post("/transfer")
async def transfer(req: TransferRequest):
    """转账"""
    # 禁止自转账
    if req.from_agent == req.to_agent:
        raise HTTPException(400, "Cannot transfer to yourself")
    
    try:
        if req.onchain:
            settlement = await settlement_engine.settle_onchain(
                req.from_agent, req.to_agent, req.amount
            )
        else:
            settlement = await settlement_engine.settle_internal(
                req.from_agent, req.to_agent, req.amount
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

from services.rate_limiter import rate_limiter

@app.get("/rate-limit/{agent_id}")
async def get_rate_limit_status(agent_id: str):
    """获取限流状态"""
    return rate_limiter.get_status(agent_id)


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

@app.get("/risk/{agent_id}")
async def get_risk_score(agent_id: str):
    """获取风险评分"""
    return risk_manager.get_risk_score(agent_id)

@app.get("/risk/{agent_id}/limits")
async def get_risk_limits(agent_id: str):
    """获取风险限额"""
    return risk_manager.get_limits(agent_id).to_dict()

class RiskLimitsUpdate(BaseModel):
    max_position_size: Optional[float] = None
    max_total_exposure: Optional[float] = None
    max_leverage: Optional[int] = None
    max_daily_loss: Optional[float] = None

@app.post("/risk/{agent_id}/limits")
async def update_risk_limits(agent_id: str, req: RiskLimitsUpdate):
    """更新风险限额"""
    limits = risk_manager.set_limits(
        agent_id,
        **{k: v for k, v in req.dict().items() if v is not None}
    )
    return {"success": True, "limits": limits.to_dict()}

@app.get("/risk/{agent_id}/violations")
async def get_risk_violations(agent_id: str, limit: int = 50):
    """获取违规记录"""
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
async def create_escrow(req: EscrowCreateRequest):
    """创建托管账户"""
    account = await solana_escrow.create_account(req.agent_id, req.wallet_address)
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
async def escrow_deposit(req: EscrowDepositRequest):
    """托管入金"""
    tx = await solana_escrow.deposit(req.agent_id, req.amount)
    return {"success": True, "tx": tx.to_dict()}

@app.post("/escrow/withdraw")
async def escrow_withdraw(req: EscrowDepositRequest):
    """托管提现"""
    tx = await solana_escrow.withdraw(req.agent_id, req.amount)
    return {"success": True, "tx": tx.to_dict()}

@app.get("/escrow/tvl")
async def get_escrow_tvl():
    """获取总 TVL"""
    return solana_escrow.get_total_tvl()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
