"""
Skill Marketplace - 技能市场

让 Agent 发布、购买和使用交易策略/技能
"""

import json
import logging
import uuid
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
            logger.warning(f"SkillMarketplace Redis connection failed: {e}")
            _redis_client = False
    return _redis_client if _redis_client else None


@dataclass
class Skill:
    """可购买的技能/策略"""
    skill_id: str
    seller_id: str
    name: str
    description: str
    price_usdc: float
    category: str = "strategy"  # strategy, signal, indicator
    strategy_code: Optional[str] = None  # 策略代码 (可选)
    performance: dict = field(default_factory=dict)  # 回测表现
    created_at: datetime = field(default_factory=datetime.now)
    sales_count: int = 0
    rating: float = 0.0
    reviews: int = 0
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "seller_id": self.seller_id,
            "name": self.name,
            "description": self.description,
            "price_usdc": self.price_usdc,
            "category": self.category,
            "performance": self.performance,
            "created_at": self.created_at.isoformat(),
            "sales_count": self.sales_count,
            "rating": self.rating,
            "reviews": self.reviews,
            "is_active": self.is_active,
        }


@dataclass  
class Purchase:
    """购买记录"""
    purchase_id: str
    buyer_id: str
    skill_id: str
    price_paid: float
    purchased_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "purchase_id": self.purchase_id,
            "buyer_id": self.buyer_id,
            "skill_id": self.skill_id,
            "price_paid": self.price_paid,
            "purchased_at": self.purchased_at.isoformat(),
        }


class SkillMarketplace:
    """技能市场服务"""
    
    SKILLS_KEY = "perpdex:skills"
    PURCHASES_KEY = "perpdex:skill_purchases"
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.purchases: Dict[str, List[Purchase]] = {}  # buyer_id -> purchases
        
        self._load_from_redis()
        print("🛒 Skill Marketplace started")
    
    def _save_to_redis(self):
        """保存到 Redis"""
        r = get_redis()
        if r:
            # 保存技能
            skills_data = {sid: s.to_dict() for sid, s in self.skills.items()}
            r.set(self.SKILLS_KEY, json.dumps(skills_data))
            
            # 保存购买记录
            purchases_data = {
                buyer_id: [p.to_dict() for p in purchases]
                for buyer_id, purchases in self.purchases.items()
            }
            r.set(self.PURCHASES_KEY, json.dumps(purchases_data))
    
    def _load_from_redis(self):
        """从 Redis 加载"""
        r = get_redis()
        if r:
            # 加载技能
            skills_data = r.get(self.SKILLS_KEY)
            if skills_data:
                try:
                    loaded = json.loads(skills_data)
                    for sid, data in loaded.items():
                        self.skills[sid] = Skill(
                            skill_id=data["skill_id"],
                            seller_id=data["seller_id"],
                            name=data["name"],
                            description=data["description"],
                            price_usdc=data["price_usdc"],
                            category=data.get("category", "strategy"),
                            strategy_code=data.get("strategy_code"),
                            performance=data.get("performance", {}),
                            created_at=datetime.fromisoformat(data["created_at"]),
                            sales_count=data.get("sales_count", 0),
                            rating=data.get("rating", 0.0),
                            reviews=data.get("reviews", 0),
                            is_active=data.get("is_active", True),
                        )
                    if self.skills:
                        print(f"🛒 Loaded {len(self.skills)} skills from Redis")
                except Exception as e:
                    logger.warning(f"Failed to load skills: {e}")
            
            # 加载购买记录
            purchases_data = r.get(self.PURCHASES_KEY)
            if purchases_data:
                try:
                    loaded = json.loads(purchases_data)
                    for buyer_id, purchases in loaded.items():
                        self.purchases[buyer_id] = [
                            Purchase(
                                purchase_id=p["purchase_id"],
                                buyer_id=p["buyer_id"],
                                skill_id=p["skill_id"],
                                price_paid=p["price_paid"],
                                purchased_at=datetime.fromisoformat(p["purchased_at"]),
                            )
                            for p in purchases
                        ]
                except Exception as e:
                    logger.warning(f"Failed to load purchases: {e}")
    
    def publish_skill(
        self,
        seller_id: str,
        name: str,
        description: str,
        price_usdc: float,
        category: str = "strategy",
        strategy_code: Optional[str] = None,
        performance: Optional[dict] = None,
    ) -> Skill:
        """发布新技能"""
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        
        skill = Skill(
            skill_id=skill_id,
            seller_id=seller_id,
            name=name,
            description=description,
            price_usdc=max(1.0, min(price_usdc, 1000.0)),  # $1 - $1000
            category=category,
            strategy_code=strategy_code,
            performance=performance or {},
        )
        
        self.skills[skill_id] = skill
        self._save_to_redis()
        
        logger.info(f"🛒 New skill published: {name} by {seller_id} (${price_usdc})")
        return skill
    
    def list_skills(
        self,
        category: Optional[str] = None,
        seller_id: Optional[str] = None,
        sort_by: str = "sales",  # sales, rating, price, newest
        limit: int = 50,
    ) -> List[Skill]:
        """列出技能"""
        skills = [s for s in self.skills.values() if s.is_active]
        
        if category:
            skills = [s for s in skills if s.category == category]
        if seller_id:
            skills = [s for s in skills if s.seller_id == seller_id]
        
        # 排序
        if sort_by == "sales":
            skills.sort(key=lambda s: s.sales_count, reverse=True)
        elif sort_by == "rating":
            skills.sort(key=lambda s: s.rating, reverse=True)
        elif sort_by == "price":
            skills.sort(key=lambda s: s.price_usdc)
        elif sort_by == "newest":
            skills.sort(key=lambda s: s.created_at, reverse=True)
        
        return skills[:limit]
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能详情"""
        return self.skills.get(skill_id)
    
    def purchase_skill(
        self,
        buyer_id: str,
        skill_id: str,
        deduct_balance_func=None,  # 扣款函数
    ) -> Purchase:
        """购买技能"""
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        if not skill.is_active:
            raise ValueError("Skill is no longer available")
        
        if skill.seller_id == buyer_id:
            raise ValueError("Cannot buy your own skill")
        
        # 检查是否已购买
        if buyer_id in self.purchases:
            for p in self.purchases[buyer_id]:
                if p.skill_id == skill_id:
                    raise ValueError("Already purchased this skill")
        
        # 扣款
        if deduct_balance_func:
            success = deduct_balance_func(buyer_id, skill.price_usdc, skill.seller_id)
            if not success:
                raise ValueError("Insufficient balance")
        
        # 记录购买
        purchase = Purchase(
            purchase_id=f"pur_{uuid.uuid4().hex[:8]}",
            buyer_id=buyer_id,
            skill_id=skill_id,
            price_paid=skill.price_usdc,
        )
        
        if buyer_id not in self.purchases:
            self.purchases[buyer_id] = []
        self.purchases[buyer_id].append(purchase)
        
        # 更新销量
        skill.sales_count += 1
        
        self._save_to_redis()
        
        logger.info(f"🛒 Skill purchased: {skill.name} by {buyer_id}")
        return purchase
    
    def get_my_skills(self, agent_id: str) -> List[dict]:
        """获取已购买的技能"""
        purchases = self.purchases.get(agent_id, [])
        result = []
        
        for p in purchases:
            skill = self.skills.get(p.skill_id)
            if skill:
                result.append({
                    "purchase": p.to_dict(),
                    "skill": skill.to_dict(),
                })
        
        return result
    
    def get_stats(self) -> dict:
        """获取市场统计"""
        total_skills = len(self.skills)
        active_skills = len([s for s in self.skills.values() if s.is_active])
        total_sales = sum(s.sales_count for s in self.skills.values())
        total_volume = sum(
            p.price_paid 
            for purchases in self.purchases.values() 
            for p in purchases
        )
        
        # Top sellers
        seller_sales = {}
        for s in self.skills.values():
            if s.seller_id not in seller_sales:
                seller_sales[s.seller_id] = 0
            seller_sales[s.seller_id] += s.sales_count
        
        top_sellers = sorted(
            seller_sales.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_skills": total_skills,
            "active_skills": active_skills,
            "total_sales": total_sales,
            "total_volume_usdc": total_volume,
            "unique_buyers": len(self.purchases),
            "top_sellers": [
                {"seller_id": sid, "sales": cnt}
                for sid, cnt in top_sellers
            ]
        }


# 单例
skill_marketplace = SkillMarketplace()
