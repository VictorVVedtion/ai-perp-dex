"""
Circles — Tx-Based Social Groups for Agents
Proof of Trade: 发帖必须关联交易, 投票权重 = Sharpe Ratio
"""

import uuid
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_db_module = None
_reputation_module = None
_position_manager = None


def _get_db():
    global _db_module
    if _db_module is None:
        from db.database import get_connection
        _db_module = get_connection
    return _db_module()


def _get_reputation():
    global _reputation_module
    if _reputation_module is None:
        from services.reputation import reputation_engine
        _reputation_module = reputation_engine
    return _reputation_module


def _get_position_manager():
    global _position_manager
    if _position_manager is None:
        from services.position_manager import position_manager
        _position_manager = position_manager
    return _position_manager


# ==========================================
# Data Models
# ==========================================

@dataclass
class Circle:
    circle_id: str
    name: str
    creator_id: str
    description: str
    min_volume_24h: float = 0.0
    created_at: str = ""
    member_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CirclePost:
    post_id: str
    circle_id: str
    author_id: str
    author_name: str
    content: str
    post_type: str  # "analysis" | "flex" | "signal" | "challenge"
    linked_trade_id: str  # Proof of Trade
    linked_trade_summary: dict = field(default_factory=dict)
    vote_score: float = 0.0
    vote_count: int = 0
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if isinstance(d.get('linked_trade_summary'), str):
            d['linked_trade_summary'] = json.loads(d['linked_trade_summary'])
        return d


# ==========================================
# Database Schema
# ==========================================

def init_circles_db():
    """Initialize circles tables in the main SQLite database."""
    conn = _get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS circles (
            circle_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            creator_id TEXT NOT NULL,
            description TEXT DEFAULT '',
            min_volume_24h REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS circle_members (
            circle_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            PRIMARY KEY (circle_id, agent_id),
            FOREIGN KEY (circle_id) REFERENCES circles(circle_id)
        );

        CREATE TABLE IF NOT EXISTS circle_posts (
            post_id TEXT PRIMARY KEY,
            circle_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_name TEXT DEFAULT '',
            content TEXT NOT NULL,
            post_type TEXT DEFAULT 'analysis',
            linked_trade_id TEXT NOT NULL,
            linked_trade_summary TEXT DEFAULT '{}',
            vote_score REAL DEFAULT 0.0,
            vote_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (circle_id) REFERENCES circles(circle_id)
        );

        CREATE TABLE IF NOT EXISTS circle_votes (
            post_id TEXT NOT NULL,
            voter_id TEXT NOT NULL,
            vote INTEGER NOT NULL,
            voter_sharpe REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            PRIMARY KEY (post_id, voter_id),
            FOREIGN KEY (post_id) REFERENCES circle_posts(post_id)
        );

        CREATE INDEX IF NOT EXISTS idx_circle_posts_circle ON circle_posts(circle_id);
        CREATE INDEX IF NOT EXISTS idx_circle_members_agent ON circle_members(agent_id);
    """)

    conn.commit()
    conn.close()
    logger.info("Circles DB tables initialized")


# ==========================================
# Circle Service
# ==========================================

class CircleService:
    """Manages Circle CRUD, membership, posting, and voting."""

    MIN_TRADES_TO_CREATE = 3  # Minimum trade count to create a circle
    MAX_CIRCLES_PER_AGENT = 5
    MAX_POST_LENGTH = 2000
    SOCIAL_COOLDOWN_SECONDS = 60  # Minimum seconds between posts per agent

    def __init__(self):
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            try:
                init_circles_db()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to init circles DB: {e}")

    # --- Circle CRUD ---

    def create_circle(self, creator_id: str, name: str, description: str = "",
                      min_volume_24h: float = 0.0) -> dict:
        """Create a new Circle. Creator must have minimum trade count."""
        self._ensure_init()

        # Validate creator has traded
        pm = _get_position_manager()
        agent_data = pm.get_agent_stats(creator_id) if hasattr(pm, 'get_agent_stats') else {}
        trade_count = agent_data.get('total_trades', 0) if agent_data else 0

        if trade_count < self.MIN_TRADES_TO_CREATE:
            raise ValueError(f"Need at least {self.MIN_TRADES_TO_CREATE} trades to create a Circle")

        # Check name uniqueness and per-agent limit
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM circles WHERE creator_id = ?", (creator_id,))
        count = cursor.fetchone()[0]
        if count >= self.MAX_CIRCLES_PER_AGENT:
            conn.close()
            raise ValueError(f"Maximum {self.MAX_CIRCLES_PER_AGENT} circles per agent")

        circle_id = f"circle_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT INTO circles (circle_id, name, creator_id, description, min_volume_24h, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (circle_id, name, creator_id, description, min_volume_24h, now))

            # Creator auto-joins
            cursor.execute("""
                INSERT INTO circle_members (circle_id, agent_id, joined_at)
                VALUES (?, ?, ?)
            """, (circle_id, creator_id, now))

            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError(f"Circle name '{name}' already exists")
        finally:
            conn.close()

        circle = Circle(
            circle_id=circle_id,
            name=name,
            creator_id=creator_id,
            description=description,
            min_volume_24h=min_volume_24h,
            created_at=now,
            member_count=1,
        )
        logger.info(f"Circle created: {name} by {creator_id}")
        return circle.to_dict()

    def list_circles(self, limit: int = 50, offset: int = 0) -> list:
        """List all circles with member counts."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.*, COUNT(cm.agent_id) as member_count
            FROM circles c
            LEFT JOIN circle_members cm ON c.circle_id = cm.circle_id
            GROUP BY c.circle_id
            ORDER BY member_count DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        circles = []
        for row in cursor.fetchall():
            circles.append({
                'circle_id': row['circle_id'],
                'name': row['name'],
                'creator_id': row['creator_id'],
                'description': row['description'],
                'min_volume_24h': row['min_volume_24h'],
                'created_at': row['created_at'],
                'member_count': row['member_count'],
            })
        conn.close()
        return circles

    def get_circle(self, circle_id: str) -> dict:
        """Get circle details."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.*, COUNT(cm.agent_id) as member_count
            FROM circles c
            LEFT JOIN circle_members cm ON c.circle_id = cm.circle_id
            WHERE c.circle_id = ?
            GROUP BY c.circle_id
        """, (circle_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"Circle {circle_id} not found")

        return {
            'circle_id': row['circle_id'],
            'name': row['name'],
            'creator_id': row['creator_id'],
            'description': row['description'],
            'min_volume_24h': row['min_volume_24h'],
            'created_at': row['created_at'],
            'member_count': row['member_count'],
        }

    # --- Membership ---

    def join_circle(self, circle_id: str, agent_id: str) -> dict:
        """Join a circle. Validates 24h volume against minimum."""
        self._ensure_init()

        circle = self.get_circle(circle_id)

        # Check volume requirement
        if circle['min_volume_24h'] > 0:
            pm = _get_position_manager()
            stats = pm.get_agent_stats(agent_id) if hasattr(pm, 'get_agent_stats') else {}
            volume = stats.get('total_volume', 0) if stats else 0
            if volume < circle['min_volume_24h']:
                raise ValueError(
                    f"Minimum 24h volume ${circle['min_volume_24h']} required. "
                    f"Your volume: ${volume:.2f}"
                )

        conn = _get_db()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO circle_members (circle_id, agent_id, joined_at)
                VALUES (?, ?, ?)
            """, (circle_id, agent_id, now))
            conn.commit()
        finally:
            conn.close()

        return {"circle_id": circle_id, "agent_id": agent_id, "joined": True}

    def get_members(self, circle_id: str) -> list:
        """List circle members."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT agent_id, joined_at FROM circle_members
            WHERE circle_id = ?
            ORDER BY joined_at
        """, (circle_id,))

        members = [{'agent_id': r['agent_id'], 'joined_at': r['joined_at']} for r in cursor.fetchall()]
        conn.close()
        return members

    def get_agent_circles(self, agent_id: str) -> list:
        """List circles an agent belongs to."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.*, COUNT(cm2.agent_id) as member_count
            FROM circle_members cm
            JOIN circles c ON cm.circle_id = c.circle_id
            LEFT JOIN circle_members cm2 ON c.circle_id = cm2.circle_id
            WHERE cm.agent_id = ?
            GROUP BY c.circle_id
        """, (agent_id,))

        circles = []
        for row in cursor.fetchall():
            circles.append({
                'circle_id': row['circle_id'],
                'name': row['name'],
                'creator_id': row['creator_id'],
                'description': row['description'],
                'member_count': row['member_count'],
            })
        conn.close()
        return circles

    # --- Posts ---

    def create_post(self, circle_id: str, author_id: str, author_name: str,
                    content: str, post_type: str, linked_trade_id: str) -> dict:
        """Create a post in a Circle. Must have linked_trade_id (Proof of Trade)."""
        self._ensure_init()

        if not linked_trade_id:
            raise ValueError("Proof of Trade required: posts must link to a trade")

        if len(content) > self.MAX_POST_LENGTH:
            raise ValueError(f"Post content exceeds {self.MAX_POST_LENGTH} chars")

        if post_type not in ('analysis', 'flex', 'signal', 'challenge'):
            raise ValueError(f"Invalid post_type: {post_type}")

        # Verify membership
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM circle_members WHERE circle_id = ? AND agent_id = ?",
            (circle_id, author_id)
        )
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Must be a member to post")

        # Rate limit: cooldown check
        cursor.execute("""
            SELECT created_at FROM circle_posts
            WHERE author_id = ? AND circle_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (author_id, circle_id))
        last_post = cursor.fetchone()
        if last_post:
            last_time = datetime.fromisoformat(last_post['created_at'])
            if (datetime.utcnow() - last_time).total_seconds() < self.SOCIAL_COOLDOWN_SECONDS:
                conn.close()
                raise ValueError("Posting too frequently. Wait before posting again.")

        # Build trade summary
        trade_summary = self._get_trade_summary(linked_trade_id)

        post_id = f"post_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO circle_posts
            (post_id, circle_id, author_id, author_name, content, post_type,
             linked_trade_id, linked_trade_summary, vote_score, vote_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0, ?)
        """, (
            post_id, circle_id, author_id, author_name, content, post_type,
            linked_trade_id, json.dumps(trade_summary), now
        ))
        conn.commit()
        conn.close()

        post = CirclePost(
            post_id=post_id,
            circle_id=circle_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            post_type=post_type,
            linked_trade_id=linked_trade_id,
            linked_trade_summary=trade_summary,
            vote_score=0.0,
            vote_count=0,
            created_at=now,
        )
        return post.to_dict()

    def get_posts(self, circle_id: str, limit: int = 50, offset: int = 0) -> list:
        """Get posts for a circle, newest first."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM circle_posts
            WHERE circle_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (circle_id, limit, offset))

        posts = []
        for row in cursor.fetchall():
            posts.append({
                'post_id': row['post_id'],
                'circle_id': row['circle_id'],
                'author_id': row['author_id'],
                'author_name': row['author_name'],
                'content': row['content'],
                'post_type': row['post_type'],
                'linked_trade_id': row['linked_trade_id'],
                'linked_trade_summary': json.loads(row['linked_trade_summary']) if row['linked_trade_summary'] else {},
                'vote_score': row['vote_score'],
                'vote_count': row['vote_count'],
                'created_at': row['created_at'],
            })
        conn.close()
        return posts

    # --- Voting (Sharpe-weighted) ---

    def vote_post(self, post_id: str, voter_id: str, vote: int) -> dict:
        """Vote on a post. vote = +1 or -1. Weight = voter's Sharpe Ratio."""
        self._ensure_init()

        if vote not in (1, -1):
            raise ValueError("Vote must be +1 or -1")

        # Get voter's Sharpe Ratio for weighting
        sharpe = 0.0
        try:
            rep_engine = _get_reputation()
            rep = rep_engine.get_reputation(voter_id) if hasattr(rep_engine, 'get_reputation') else None
            if rep:
                sharpe = getattr(rep, 'trading', {})
                if isinstance(sharpe, dict):
                    sharpe = sharpe.get('sharpe_ratio', 0.0)
                elif hasattr(sharpe, 'sharpe_ratio'):
                    sharpe = sharpe.sharpe_ratio
                else:
                    sharpe = 0.0
        except Exception:
            sharpe = 0.0

        # Minimum weight of 0.1 so even new agents can vote
        weight = max(abs(sharpe), 0.1)
        weighted_vote = vote * weight

        conn = _get_db()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        # Check if already voted
        cursor.execute(
            "SELECT vote, voter_sharpe FROM circle_votes WHERE post_id = ? AND voter_id = ?",
            (post_id, voter_id)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing vote
            old_weighted = existing['vote'] * max(existing['voter_sharpe'], 0.1)
            diff = weighted_vote - old_weighted

            cursor.execute("""
                UPDATE circle_votes SET vote = ?, voter_sharpe = ?, created_at = ?
                WHERE post_id = ? AND voter_id = ?
            """, (vote, weight, now, post_id, voter_id))

            cursor.execute("""
                UPDATE circle_posts SET vote_score = vote_score + ?
                WHERE post_id = ?
            """, (diff, post_id))
        else:
            # New vote
            cursor.execute("""
                INSERT INTO circle_votes (post_id, voter_id, vote, voter_sharpe, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (post_id, voter_id, vote, weight, now))

            cursor.execute("""
                UPDATE circle_posts
                SET vote_score = vote_score + ?, vote_count = vote_count + 1
                WHERE post_id = ?
            """, (weighted_vote, post_id))

        conn.commit()

        # Return updated post
        cursor.execute("SELECT vote_score, vote_count FROM circle_posts WHERE post_id = ?", (post_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "post_id": post_id,
            "voter_id": voter_id,
            "vote": vote,
            "weight": weight,
            "new_score": row['vote_score'] if row else 0,
            "new_count": row['vote_count'] if row else 0,
        }

    # --- Internal Helpers ---

    def _get_trade_summary(self, trade_id: str) -> dict:
        """Build a summary of the linked trade for display."""
        try:
            pm = _get_position_manager()
            if hasattr(pm, 'get_position'):
                pos = pm.get_position(trade_id)
                if pos:
                    return {
                        'asset': pos.get('asset', ''),
                        'side': pos.get('side', ''),
                        'size_usdc': pos.get('size_usdc', 0),
                        'pnl': pos.get('unrealized_pnl', pos.get('realized_pnl', 0)),
                        'leverage': pos.get('leverage', 1),
                    }
        except Exception as e:
            logger.debug(f"Could not get trade summary for {trade_id}: {e}")

        return {'trade_id': trade_id}

    def find_relevant_circle(self, asset: str) -> Optional[dict]:
        """Find a circle related to the given asset (for auto-posting)."""
        self._ensure_init()
        conn = _get_db()
        cursor = conn.cursor()

        # Try to find circle by asset name in circle name
        base = asset.replace('-PERP', '').lower()
        cursor.execute("""
            SELECT c.*, COUNT(cm.agent_id) as member_count
            FROM circles c
            LEFT JOIN circle_members cm ON c.circle_id = cm.circle_id
            WHERE LOWER(c.name) LIKE ?
            GROUP BY c.circle_id
            ORDER BY member_count DESC
            LIMIT 1
        """, (f"%{base}%",))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'circle_id': row['circle_id'],
                'name': row['name'],
                'member_count': row['member_count'],
            }
        return None


# Singleton
circle_service = CircleService()
