"""
Copy Trade Service - 跟单系统

让 Agent 自动跟随其他 Agent 的交易
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

# Redis client
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None and os.environ.get("USE_REDIS", "true").lower() == "true":
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"CopyTrade Redis connection failed: {e}")
            _redis_client = False
    return _redis_client if _redis_client else None


@dataclass
class Subscription:
    """跟单订阅"""
    follower_id: str
    leader_id: str
    multiplier: float = 1.0  # 仓位倍数
    max_per_trade: float = 100.0  # 单笔最大金额
    created_at: datetime = field(default_factory=datetime.now)
    total_copied: int = 0  # 复制的交易数
    total_profit: float = 0.0  # 总收益
    
    def to_dict(self) -> dict:
        return {
            "follower_id": self.follower_id,
            "leader_id": self.leader_id,
            "multiplier": self.multiplier,
            "max_per_trade": self.max_per_trade,
            "created_at": self.created_at.isoformat(),
            "total_copied": self.total_copied,
            "total_profit": self.total_profit,
        }


class CopyTradeService:
    """跟单服务"""
    
    REDIS_KEY = "perpdex:copy_trade"
    
    def __init__(self):
        # follower_id -> {leader_id -> Subscription}
        self.subscriptions: Dict[str, Dict[str, Subscription]] = {}
        # 反向索引: leader_id -> [follower_ids]
        self.followers_index: Dict[str, List[str]] = {}
        
        # 加载
        self._load_from_redis()
        
        print("🔄 Copy Trade Service started")
    
    def _save_to_redis(self):
        """保存到 Redis"""
        r = get_redis()
        if r:
            data = {}
            for follower_id, leaders in self.subscriptions.items():
                data[follower_id] = {
                    leader_id: sub.to_dict() 
                    for leader_id, sub in leaders.items()
                }
            r.set(self.REDIS_KEY, json.dumps(data))
    
    def _load_from_redis(self):
        """从 Redis 加载"""
        r = get_redis()
        if r:
            data = r.get(self.REDIS_KEY)
            if data:
                try:
                    loaded = json.loads(data)
                    for follower_id, leaders in loaded.items():
                        self.subscriptions[follower_id] = {}
                        for leader_id, sub_data in leaders.items():
                            sub = Subscription(
                                follower_id=sub_data["follower_id"],
                                leader_id=sub_data["leader_id"],
                                multiplier=sub_data.get("multiplier", 1.0),
                                max_per_trade=sub_data.get("max_per_trade", 100.0),
                                created_at=datetime.fromisoformat(sub_data["created_at"]),
                                total_copied=sub_data.get("total_copied", 0),
                                total_profit=sub_data.get("total_profit", 0.0),
                            )
                            self.subscriptions[follower_id][leader_id] = sub
                            
                            # 更新反向索引
                            if leader_id not in self.followers_index:
                                self.followers_index[leader_id] = []
                            if follower_id not in self.followers_index[leader_id]:
                                self.followers_index[leader_id].append(follower_id)
                    
                    total = sum(len(v) for v in self.subscriptions.values())
                    if total > 0:
                        print(f"🔄 Loaded {total} copy trade subscriptions")
                except Exception as e:
                    logger.warning(f"Failed to load copy trade data: {e}")
    
    def follow(
        self, 
        follower_id: str, 
        leader_id: str, 
        multiplier: float = 1.0, 
        max_per_trade: float = 100.0
    ) -> Subscription:
        """开始跟单"""
        if follower_id == leader_id:
            raise ValueError("Cannot follow yourself")
        
        if follower_id not in self.subscriptions:
            self.subscriptions[follower_id] = {}
        
        sub = Subscription(
            follower_id=follower_id,
            leader_id=leader_id,
            multiplier=min(multiplier, 3.0),  # 最大 3 倍
            max_per_trade=min(max_per_trade, 1000.0),  # 最大 $1000
        )
        self.subscriptions[follower_id][leader_id] = sub
        
        # 更新反向索引
        if leader_id not in self.followers_index:
            self.followers_index[leader_id] = []
        if follower_id not in self.followers_index[leader_id]:
            self.followers_index[leader_id].append(follower_id)
        
        self._save_to_redis()
        logger.info(f"🔄 {follower_id} now following {leader_id}")
        
        return sub
    
    def unfollow(self, follower_id: str, leader_id: str) -> bool:
        """停止跟单"""
        if follower_id in self.subscriptions:
            if leader_id in self.subscriptions[follower_id]:
                del self.subscriptions[follower_id][leader_id]
                
                # 更新反向索引
                if leader_id in self.followers_index:
                    if follower_id in self.followers_index[leader_id]:
                        self.followers_index[leader_id].remove(follower_id)
                
                self._save_to_redis()
                logger.info(f"🔄 {follower_id} unfollowed {leader_id}")
                return True
        return False
    
    def get_followers(self, leader_id: str) -> List[Subscription]:
        """获取 leader 的所有 followers"""
        follower_ids = self.followers_index.get(leader_id, [])
        result = []
        for fid in follower_ids:
            if fid in self.subscriptions and leader_id in self.subscriptions[fid]:
                result.append(self.subscriptions[fid][leader_id])
        return result
    
    def get_following(self, follower_id: str) -> List[Subscription]:
        """获取 follower 关注的所有 leaders"""
        if follower_id not in self.subscriptions:
            return []
        return list(self.subscriptions[follower_id].values())
    
    async def on_trade(self, leader_id: str, trade: dict, open_position_func) -> List[dict]:
        """
        当 leader 开仓时，复制给所有 followers
        
        Args:
            leader_id: 交易发起者
            trade: 交易信息 {asset, side, size_usdc, leverage}
            open_position_func: 开仓函数
        
        Returns:
            复制的交易列表
        """
        followers = self.get_followers(leader_id)
        if not followers:
            return []
        
        copied_trades = []
        
        for sub in followers:
            try:
                # 计算跟单仓位
                size = min(
                    trade["size_usdc"] * sub.multiplier,
                    sub.max_per_trade
                )
                
                if size < 10:  # 最小 $10
                    continue
                
                # 执行跟单
                result = await open_position_func(
                    agent_id=sub.follower_id,
                    asset=trade["asset"],
                    side=trade["side"],
                    size_usdc=size,
                    leverage=trade.get("leverage", 1),
                    reason=f"Copy trade from {leader_id}"
                )
                
                if result:
                    copied_trades.append({
                        "follower_id": sub.follower_id,
                        "position": result,
                        "original_size": trade["size_usdc"],
                        "copied_size": size,
                    })
                    
                    # 更新统计
                    sub.total_copied += 1
                    
                    logger.info(f"🔄 Copied trade: {leader_id} -> {sub.follower_id} (${size})")
                    
            except Exception as e:
                logger.warning(f"Failed to copy trade to {sub.follower_id}: {e}")
        
        if copied_trades:
            self._save_to_redis()
        
        return copied_trades
    
    def get_stats(self) -> dict:
        """获取跟单统计"""
        total_subscriptions = sum(len(v) for v in self.subscriptions.values())
        total_leaders = len(self.followers_index)
        total_followers = len(self.subscriptions)
        
        # Top leaders by follower count
        top_leaders = sorted(
            [(lid, len(fids)) for lid, fids in self.followers_index.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_subscriptions": total_subscriptions,
            "total_leaders": total_leaders,
            "total_followers": total_followers,
            "top_leaders": [
                {"leader_id": lid, "follower_count": cnt}
                for lid, cnt in top_leaders
            ]
        }


# 单例
copy_trade_service = CopyTradeService()
