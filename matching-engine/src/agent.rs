//! Agent identity and management

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Unique agent identifier
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AgentId(pub String);

impl AgentId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }
}

impl std::fmt::Display for AgentId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Agent metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMetadata {
    pub name: String,
    pub description: Option<String>,
    pub avatar_url: Option<String>,
    pub website: Option<String>,
}

/// Risk limits for an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRiskLimits {
    /// Maximum position size in USD
    pub max_position_usd: f64,
    /// Maximum leverage
    pub max_leverage: f64,
    /// Daily loss limit in USD
    pub daily_loss_limit_usd: f64,
    /// Maximum number of open orders
    pub max_open_orders: u32,
}

impl Default for AgentRiskLimits {
    fn default() -> Self {
        Self {
            max_position_usd: 100_000.0,
            max_leverage: 10.0,
            daily_loss_limit_usd: 10_000.0,
            max_open_orders: 100,
        }
    }
}

/// Agent reputation/performance metrics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AgentReputation {
    /// Total number of trades
    pub total_trades: u64,
    /// Number of winning trades
    pub winning_trades: u64,
    /// Total PnL in USD
    pub total_pnl_usd: f64,
    /// Maximum drawdown percentage
    pub max_drawdown_pct: f64,
    /// Sharpe ratio (if calculable)
    pub sharpe_ratio: Option<f64>,
    /// Trust score (0-100)
    pub trust_score: u8,
}

impl AgentReputation {
    pub fn win_rate(&self) -> f64 {
        if self.total_trades == 0 {
            0.0
        } else {
            self.winning_trades as f64 / self.total_trades as f64
        }
    }
}

/// An AI agent in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Agent {
    /// Unique identifier
    pub id: AgentId,
    /// Wallet address (Solana pubkey)
    pub wallet: String,
    /// API key hash (for programmatic access)
    pub api_key_hash: Option<String>,
    /// Agent metadata
    pub metadata: AgentMetadata,
    /// Risk limits
    pub risk_limits: AgentRiskLimits,
    /// Reputation metrics
    pub reputation: AgentReputation,
    /// Registration timestamp
    pub registered_at: u64,
    /// Is agent active
    pub is_active: bool,
    /// Is agent verified
    pub is_verified: bool,
}

impl Agent {
    pub fn new(id: AgentId, wallet: String, name: String) -> Self {
        Self {
            id,
            wallet,
            api_key_hash: None,
            metadata: AgentMetadata {
                name,
                description: None,
                avatar_url: None,
                website: None,
            },
            risk_limits: AgentRiskLimits::default(),
            reputation: AgentReputation::default(),
            registered_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            is_active: true,
            is_verified: false,
        }
    }
}

/// Agent registry
pub struct AgentRegistry {
    agents: HashMap<AgentId, Agent>,
    wallet_to_agent: HashMap<String, AgentId>,
}

impl AgentRegistry {
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
            wallet_to_agent: HashMap::new(),
        }
    }
    
    /// Register a new agent
    pub fn register(&mut self, agent: Agent) -> Result<(), String> {
        if self.agents.contains_key(&agent.id) {
            return Err("Agent ID already exists".to_string());
        }
        if self.wallet_to_agent.contains_key(&agent.wallet) {
            return Err("Wallet already registered".to_string());
        }
        
        self.wallet_to_agent.insert(agent.wallet.clone(), agent.id.clone());
        self.agents.insert(agent.id.clone(), agent);
        Ok(())
    }
    
    /// Get agent by ID
    pub fn get(&self, id: &AgentId) -> Option<&Agent> {
        self.agents.get(id)
    }
    
    /// Get agent by wallet
    pub fn get_by_wallet(&self, wallet: &str) -> Option<&Agent> {
        self.wallet_to_agent.get(wallet).and_then(|id| self.agents.get(id))
    }
    
    /// Update agent
    pub fn update(&mut self, agent: Agent) -> Result<(), String> {
        if !self.agents.contains_key(&agent.id) {
            return Err("Agent not found".to_string());
        }
        self.agents.insert(agent.id.clone(), agent);
        Ok(())
    }
    
    /// List all agents
    pub fn list(&self) -> Vec<&Agent> {
        self.agents.values().collect()
    }
    
    /// Get agent count
    pub fn count(&self) -> usize {
        self.agents.len()
    }
}

impl Default for AgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_agent_creation() {
        let agent = Agent::new(
            AgentId::new("aria-001"),
            "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK".to_string(),
            "Aria Trading Bot".to_string(),
        );
        
        assert_eq!(agent.id.0, "aria-001");
        assert!(agent.is_active);
        assert!(!agent.is_verified);
    }
    
    #[test]
    fn test_agent_registry() {
        let mut registry = AgentRegistry::new();
        
        let agent = Agent::new(
            AgentId::new("aria-001"),
            "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK".to_string(),
            "Aria".to_string(),
        );
        
        assert!(registry.register(agent.clone()).is_ok());
        assert!(registry.register(agent).is_err()); // Duplicate
        
        assert_eq!(registry.count(), 1);
        assert!(registry.get(&AgentId::new("aria-001")).is_some());
    }
    
    #[test]
    fn test_win_rate_calculation() {
        let mut rep = AgentReputation::default();
        assert_eq!(rep.win_rate(), 0.0);
        
        rep.total_trades = 100;
        rep.winning_trades = 60;
        assert_eq!(rep.win_rate(), 0.6);
    }
}
