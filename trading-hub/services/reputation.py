"""
AI Native Reputation System

Calculates and manages Agent reputation based on:
- Trading performance (win rate, PnL, Sharpe ratio)
- Social trust (signal accuracy, response rate, alliance score)
- History (account age, total trades)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import math

from db.database import get_connection


@dataclass
class AgentReputation:
    """Full reputation profile for an Agent"""
    agent_id: str
    
    # Trading Performance (0-100 each)
    win_rate: float = 0.0           # Percentage of winning trades
    profit_factor: float = 0.0       # Gross profit / Gross loss
    sharpe_ratio: float = 0.0        # Risk-adjusted returns
    max_drawdown: float = 0.0        # Worst peak-to-trough decline
    
    # Social Trust (0-100 each)
    signal_accuracy: float = 0.0     # % of signals that hit target
    response_rate: float = 0.0       # % of messages responded to
    alliance_score: float = 0.0      # Contribution to alliances
    
    # History
    age_days: int = 0                # Account age in days
    total_trades: int = 0            # Total number of trades
    total_volume: float = 0.0        # Total trading volume
    
    # Composite Scores
    trading_score: float = 0.0       # Combined trading metrics
    social_score: float = 0.0        # Combined social metrics
    trust_score: float = 0.0         # Overall 0-100 score
    
    # Tier
    tier: str = "Bronze"             # Bronze, Silver, Gold, Diamond, Elite


class ReputationService:
    """
    Calculates and updates Agent reputation scores.
    
    Scoring Philosophy:
    - New agents start with neutral (50) trust score
    - Trust is EARNED through consistent performance
    - Trust can be LOST through bad behavior
    - High trust unlocks privileges
    """
    
    # Weights for composite score
    WEIGHTS = {
        'trading': 0.50,    # 50% from trading performance
        'social': 0.30,     # 30% from social trust
        'history': 0.20,    # 20% from track record length
    }
    
    # Trust tiers
    TIERS = [
        (90, "Elite"),      # Top performers
        (75, "Diamond"),    # Excellent track record
        (60, "Gold"),       # Good standing
        (40, "Silver"),     # Developing
        (0, "Bronze"),      # New/rebuilding
    ]
    
    def __init__(self):
        self.conn = get_connection()
    
    def calculate_reputation(self, agent_id: str) -> AgentReputation:
        """Calculate full reputation profile for an agent"""
        
        # Get agent basic info
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM agents WHERE agent_id = ?
        """, (agent_id,))
        agent = cursor.fetchone()
        
        if not agent:
            return AgentReputation(agent_id=agent_id)
        
        # Calculate trading metrics
        trading_metrics = self._calculate_trading_metrics(agent_id)
        
        # Calculate social metrics
        social_metrics = self._calculate_social_metrics(agent_id)
        
        # Calculate history metrics
        history_metrics = self._calculate_history_metrics(agent_id, agent)
        
        # Combine into composite scores
        trading_score = self._trading_composite(trading_metrics)
        social_score = self._social_composite(social_metrics)
        history_score = self._history_composite(history_metrics)
        
        # Calculate overall trust score
        trust_score = (
            trading_score * self.WEIGHTS['trading'] +
            social_score * self.WEIGHTS['social'] +
            history_score * self.WEIGHTS['history']
        )
        
        # Determine tier
        tier = self._get_tier(trust_score)
        
        return AgentReputation(
            agent_id=agent_id,
            # Trading
            win_rate=trading_metrics.get('win_rate', 0),
            profit_factor=trading_metrics.get('profit_factor', 0),
            sharpe_ratio=trading_metrics.get('sharpe_ratio', 0),
            max_drawdown=trading_metrics.get('max_drawdown', 0),
            # Social
            signal_accuracy=social_metrics.get('signal_accuracy', 0),
            response_rate=social_metrics.get('response_rate', 0),
            alliance_score=social_metrics.get('alliance_score', 0),
            # History
            age_days=history_metrics.get('age_days', 0),
            total_trades=history_metrics.get('total_trades', 0),
            total_volume=history_metrics.get('total_volume', 0),
            # Scores
            trading_score=trading_score,
            social_score=social_score,
            trust_score=trust_score,
            tier=tier,
        )
    
    def _calculate_trading_metrics(self, agent_id: str) -> Dict[str, float]:
        """Calculate trading performance metrics"""
        cursor = self.conn.cursor()
        
        # Get all closed positions
        cursor.execute("""
            SELECT realized_pnl, size_usdc, created_at, closed_at
            FROM positions
            WHERE agent_id = ? AND is_open = 0 AND realized_pnl IS NOT NULL
            ORDER BY closed_at
        """, (agent_id,))
        positions = cursor.fetchall()
        
        if not positions:
            return {'win_rate': 50, 'profit_factor': 1, 'sharpe_ratio': 0, 'max_drawdown': 0}
        
        # Calculate win rate
        wins = sum(1 for p in positions if p['realized_pnl'] > 0)
        total = len(positions)
        win_rate = (wins / total * 100) if total > 0 else 50
        
        # Calculate profit factor
        gross_profit = sum(p['realized_pnl'] for p in positions if p['realized_pnl'] > 0)
        gross_loss = abs(sum(p['realized_pnl'] for p in positions if p['realized_pnl'] < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 2.0
        
        # Calculate Sharpe ratio (simplified)
        returns = [p['realized_pnl'] / p['size_usdc'] for p in positions if p['size_usdc'] > 0]
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for p in positions:
            cumulative += p['realized_pnl']
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        max_drawdown = max_dd * 100
        
        return {
            'win_rate': min(win_rate, 100),
            'profit_factor': min(profit_factor, 5),  # Cap at 5
            'sharpe_ratio': max(min(sharpe_ratio, 3), -3),  # Cap between -3 and 3
            'max_drawdown': min(max_drawdown, 100),
        }
    
    def _calculate_social_metrics(self, agent_id: str) -> Dict[str, float]:
        """Calculate social trust metrics"""
        cursor = self.conn.cursor()
        
        # Signal accuracy
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won
            FROM signals
            WHERE agent_id = ? AND status IN ('won', 'lost')
        """, (agent_id,))
        signals = cursor.fetchone()
        signal_accuracy = (signals['won'] / signals['total'] * 100) if signals['total'] > 0 else 50
        
        # Response rate (from agent_messages if exists)
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN responded = 1 THEN 1 ELSE 0 END) as responded
                FROM agent_messages
                WHERE recipient_id = ?
            """, (agent_id,))
            msgs = cursor.fetchone()
            response_rate = (msgs['responded'] / msgs['total'] * 100) if msgs['total'] > 0 else 50
        except:
            response_rate = 50  # Default if table doesn't exist
        
        # Alliance score (placeholder - will implement with alliance system)
        alliance_score = 50
        
        return {
            'signal_accuracy': signal_accuracy,
            'response_rate': response_rate,
            'alliance_score': alliance_score,
        }
    
    def _calculate_history_metrics(self, agent_id: str, agent: Any) -> Dict[str, Any]:
        """Calculate history-based metrics"""
        created_at = datetime.fromisoformat(agent['created_at'].replace('Z', '+00:00')) if isinstance(agent['created_at'], str) else agent['created_at']
        age_days = (datetime.now() - created_at).days if created_at else 0
        
        return {
            'age_days': age_days,
            'total_trades': agent['total_trades'] or 0,
            'total_volume': agent['total_volume'] or 0,
        }
    
    def _trading_composite(self, metrics: Dict[str, float]) -> float:
        """Calculate composite trading score (0-100)"""
        # Win rate: 50% baseline, 70%+ is good
        win_score = min((metrics['win_rate'] - 30) / 0.4, 100) if metrics['win_rate'] > 30 else 0
        
        # Profit factor: 1.0 baseline, 2.0+ is good
        pf_score = min((metrics['profit_factor'] - 0.5) * 40, 100) if metrics['profit_factor'] > 0.5 else 0
        
        # Sharpe ratio: 0 baseline, 1.5+ is good
        sharpe_score = min((metrics['sharpe_ratio'] + 1) * 33, 100) if metrics['sharpe_ratio'] > -1 else 0
        
        # Max drawdown penalty: 0% is perfect, 50%+ is bad
        dd_penalty = min(metrics['max_drawdown'] / 0.5, 50)
        
        # Weighted combination
        score = (win_score * 0.3 + pf_score * 0.3 + sharpe_score * 0.3) - dd_penalty * 0.1
        return max(0, min(100, score))
    
    def _social_composite(self, metrics: Dict[str, float]) -> float:
        """Calculate composite social score (0-100)"""
        return (
            metrics['signal_accuracy'] * 0.5 +
            metrics['response_rate'] * 0.25 +
            metrics['alliance_score'] * 0.25
        )
    
    def _history_composite(self, metrics: Dict[str, Any]) -> float:
        """Calculate composite history score (0-100)"""
        # Age: 0 days = 0, 30+ days = 50, 180+ days = 100
        age_score = min(metrics['age_days'] / 1.8, 100)
        
        # Trades: 0 = 0, 50 = 50, 200+ = 100
        trade_score = min(metrics['total_trades'] / 2, 100)
        
        # Volume: Logarithmic scale
        volume_score = min(math.log10(metrics['total_volume'] + 1) * 20, 100)
        
        return (age_score * 0.3 + trade_score * 0.4 + volume_score * 0.3)
    
    def _get_tier(self, trust_score: float) -> str:
        """Determine tier based on trust score"""
        for threshold, tier in self.TIERS:
            if trust_score >= threshold:
                return tier
        return "Bronze"
    
    def update_agent_reputation(self, agent_id: str) -> float:
        """Recalculate and save agent's reputation score"""
        rep = self.calculate_reputation(agent_id)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agents
            SET reputation_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ?
        """, (rep.trust_score / 100, agent_id))  # Store as 0-1 in DB
        self.conn.commit()
        
        return rep.trust_score
    
    def get_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top agents by reputation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT agent_id, display_name, reputation_score, total_trades, pnl
            FROM agents
            WHERE status = 'active'
            ORDER BY reputation_score DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            rep = self.calculate_reputation(row['agent_id'])
            results.append({
                'agent_id': row['agent_id'],
                'display_name': row['display_name'],
                'trust_score': rep.trust_score,
                'tier': rep.tier,
                'win_rate': rep.win_rate,
                'total_trades': rep.total_trades,
                'pnl': row['pnl'],
            })
        
        return results


# Singleton instance
_reputation_service = None

def get_reputation_service() -> ReputationService:
    global _reputation_service
    if _reputation_service is None:
        _reputation_service = ReputationService()
    return _reputation_service
