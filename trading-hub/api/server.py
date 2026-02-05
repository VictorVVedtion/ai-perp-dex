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

class IntentRequest(BaseModel):
    agent_id: str
    intent_type: str  # "long" | "short"
    asset: str = "BTC-PERP"
    size_usdc: float = 100
    leverage: int = 1
    max_slippage: float = 0.005

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

@app.get("/")
async def root():
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
    
    # 广播新 Agent
    await manager.broadcast({
        "type": "new_agent",
        "data": agent.to_dict()
    })
    
    return {"success": True, "agent": agent.to_dict()}

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
    target_value: float
    stake_amount: float
    duration_hours: int = 24

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
