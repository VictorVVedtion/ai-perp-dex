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
    """启动时初始化价格源"""
    await price_feed.start()
    
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
    return store.get_stats()

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
    """发布交易意图"""
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
    
    # 尝试自动匹配
    matches = store.find_matching_intents(intent)
    if matches:
        best_match = matches[0]
        # 获取实时价格
        price = price_feed.get_cached_price(intent.asset)
        match = store.create_match(intent, best_match, price)
        
        # 广播匹配
        await manager.broadcast({
            "type": "new_match",
            "data": match.to_dict()
        })
        
        return {
            "success": True,
            "intent": intent.to_dict(),
            "matched": True,
            "match": match.to_dict()
        }
    
    return {
        "success": True,
        "intent": intent.to_dict(),
        "matched": False
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
