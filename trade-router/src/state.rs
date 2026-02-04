use crate::types::*;
use dashmap::DashMap;
use std::sync::Arc;
use tokio::sync::broadcast;
use uuid::Uuid;

/// 应用状态 - 线程安全
#[derive(Clone)]
pub struct AppState {
    /// 活跃的交易请求
    pub requests: Arc<DashMap<Uuid, TradeRequest>>,
    /// 活跃的报价 (request_id -> Vec<Quote>)
    pub quotes: Arc<DashMap<Uuid, Vec<Quote>>>,
    /// 仓位
    pub positions: Arc<DashMap<Uuid, Position>>,
    /// Agent 的仓位索引 (agent_id -> Vec<position_id>)
    pub agent_positions: Arc<DashMap<String, Vec<Uuid>>>,
    /// WebSocket 广播频道
    pub broadcast_tx: broadcast::Sender<WsMessage>,
    /// 模拟价格 (实际应从 Oracle 获取)
    pub prices: Arc<DashMap<Market, f64>>,
}

impl AppState {
    pub fn new() -> Self {
        let (broadcast_tx, _) = broadcast::channel(1000);
        
        let state = Self {
            requests: Arc::new(DashMap::new()),
            quotes: Arc::new(DashMap::new()),
            positions: Arc::new(DashMap::new()),
            agent_positions: Arc::new(DashMap::new()),
            broadcast_tx,
            prices: Arc::new(DashMap::new()),
        };
        
        // 初始化模拟价格
        state.prices.insert(Market::BtcPerp, 84000.0);
        state.prices.insert(Market::EthPerp, 2200.0);
        state.prices.insert(Market::SolPerp, 130.0);
        
        state
    }
    
    /// 添加交易请求
    pub fn add_request(&self, req: TradeRequest) {
        let id = req.id;
        self.requests.insert(id, req.clone());
        self.quotes.insert(id, Vec::new());
        
        // 广播给所有 MM
        let _ = self.broadcast_tx.send(WsMessage::TradeRequest(req));
    }
    
    /// 添加报价
    pub fn add_quote(&self, quote: Quote) -> Result<(), String> {
        let request_id = quote.request_id;
        
        // 检查请求是否存在
        if !self.requests.contains_key(&request_id) {
            return Err("Trade request not found".to_string());
        }
        
        // 添加报价
        if let Some(mut quotes) = self.quotes.get_mut(&request_id) {
            quotes.push(quote);
            Ok(())
        } else {
            Err("Quote storage not found".to_string())
        }
    }
    
    /// 接受报价，创建仓位
    pub fn accept_quote(&self, request_id: Uuid, quote_id: Uuid) -> Result<Position, String> {
        // 获取请求
        let request = self.requests.get(&request_id)
            .ok_or("Trade request not found")?
            .clone();
        
        // 获取报价
        let quote = self.quotes.get(&request_id)
            .ok_or("Quotes not found")?
            .iter()
            .find(|q| q.id == quote_id)
            .cloned()
            .ok_or("Quote not found")?;
        
        // 获取当前价格
        let entry_price = self.prices.get(&request.market)
            .map(|p| *p)
            .unwrap_or(0.0);
        
        // 创建仓位
        let position = Position {
            id: Uuid::new_v4(),
            request_id,
            quote_id,
            trader_agent: request.agent_id.clone(),
            mm_agent: quote.agent_id.clone(),
            market: request.market,
            side: request.side,
            size_usdc: request.size_usdc,
            leverage: request.leverage,
            entry_price,
            funding_rate: quote.funding_rate,
            trader_collateral: request.size_usdc / request.leverage as f64,
            mm_collateral: quote.collateral_usdc,
            status: PositionStatus::Active,
            created_at: chrono::Utc::now(),
            closed_at: None,
        };
        
        // 保存仓位
        let pos_id = position.id;
        self.positions.insert(pos_id, position.clone());
        
        // 更新 agent 索引
        self.agent_positions.entry(request.agent_id).or_insert(Vec::new()).push(pos_id);
        self.agent_positions.entry(quote.agent_id).or_insert(Vec::new()).push(pos_id);
        
        // 清理请求和报价
        self.requests.remove(&request_id);
        self.quotes.remove(&request_id);
        
        // 广播
        let _ = self.broadcast_tx.send(WsMessage::QuoteAccepted { 
            request_id, 
            quote_id, 
            position_id: pos_id 
        });
        let _ = self.broadcast_tx.send(WsMessage::PositionOpened(position.clone()));
        
        Ok(position)
    }
    
    /// 平仓
    pub fn close_position(&self, position_id: Uuid, _agent_id: &str) -> Result<(f64, f64), String> {
        let mut position = self.positions.get_mut(&position_id)
            .ok_or("Position not found")?;
        
        if position.status != PositionStatus::Active {
            return Err("Position is not active".to_string());
        }
        
        // 获取当前价格
        let current_price = self.prices.get(&position.market)
            .map(|p| *p)
            .unwrap_or(position.entry_price);
        
        // 计算 PnL
        let price_change = (current_price - position.entry_price) / position.entry_price;
        let leveraged_change = price_change * position.leverage as f64;
        
        let (pnl_trader, pnl_mm) = match position.side {
            Side::Long => {
                let trader_pnl = position.size_usdc * leveraged_change;
                (trader_pnl, -trader_pnl)
            }
            Side::Short => {
                let trader_pnl = position.size_usdc * (-leveraged_change);
                (trader_pnl, -trader_pnl)
            }
        };
        
        // 更新状态
        position.status = PositionStatus::Closed;
        position.closed_at = Some(chrono::Utc::now());
        
        // 广播
        let _ = self.broadcast_tx.send(WsMessage::PositionClosed { 
            position_id, 
            pnl_trader, 
            pnl_mm 
        });
        
        Ok((pnl_trader, pnl_mm))
    }
    
    /// 获取 agent 的所有仓位
    pub fn get_agent_positions(&self, agent_id: &str) -> Vec<Position> {
        self.agent_positions.get(agent_id)
            .map(|ids| {
                ids.iter()
                    .filter_map(|id| self.positions.get(id).map(|p| p.clone()))
                    .collect()
            })
            .unwrap_or_default()
    }
    
    /// 获取所有活跃请求
    pub fn get_active_requests(&self) -> Vec<TradeRequest> {
        let now = chrono::Utc::now();
        self.requests.iter()
            .filter(|r| r.expires_at > now)
            .map(|r| r.clone())
            .collect()
    }
    
    /// 获取请求的所有报价
    pub fn get_quotes(&self, request_id: Uuid) -> Vec<Quote> {
        self.quotes.get(&request_id)
            .map(|q| q.clone())
            .unwrap_or_default()
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}
