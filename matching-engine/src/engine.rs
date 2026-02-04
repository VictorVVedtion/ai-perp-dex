//! Matching Engine - orchestrates multiple orderbooks

use crate::agent::{AgentId, AgentRegistry};
use crate::order::{Order, PlaceOrderRequest, CancelOrderRequest, Side, OrderType, TimeInForce};
use crate::orderbook::OrderBook;
use crate::types::{Market, OrderId, Price, Quantity, Trade};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::RwLock;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("Market not found: {0}")]
    MarketNotFound(String),
    #[error("Agent not found: {0}")]
    AgentNotFound(String),
    #[error("Order not found: {0}")]
    OrderNotFound(u64),
    #[error("Invalid order: {0}")]
    InvalidOrder(String),
    #[error("Risk limit exceeded: {0}")]
    RiskLimitExceeded(String),
    #[error("Internal error: {0}")]
    InternalError(String),
}

/// The main matching engine
pub struct MatchingEngine {
    /// Orderbooks by market
    orderbooks: RwLock<HashMap<Market, OrderBook>>,
    /// Agent registry
    agents: RwLock<AgentRegistry>,
    /// Order ID counter
    order_counter: AtomicU64,
    /// Supported markets
    markets: Vec<Market>,
}

impl MatchingEngine {
    /// Create a new matching engine
    pub fn new() -> Self {
        let markets = vec![
            Market::btc_perp(),
            Market::eth_perp(),
            Market::sol_perp(),
        ];
        
        let mut orderbooks = HashMap::new();
        for market in &markets {
            orderbooks.insert(market.clone(), OrderBook::new(market.clone()));
        }
        
        Self {
            orderbooks: RwLock::new(orderbooks),
            agents: RwLock::new(AgentRegistry::new()),
            order_counter: AtomicU64::new(1),
            markets,
        }
    }
    
    /// Get supported markets
    pub fn markets(&self) -> &[Market] {
        &self.markets
    }
    
    /// Generate a new order ID
    fn next_order_id(&self) -> OrderId {
        OrderId(self.order_counter.fetch_add(1, Ordering::SeqCst))
    }
    
    /// Place a new order
    pub fn place_order(&self, request: PlaceOrderRequest) -> Result<(Order, Vec<Trade>), EngineError> {
        let market = Market::new(&request.market);
        
        // Validate market
        if !self.markets.contains(&market) {
            return Err(EngineError::MarketNotFound(request.market));
        }
        
        // Create order
        let order_id = self.next_order_id();
        let order = match request.order_type {
            OrderType::Limit => {
                let price = request.price
                    .ok_or_else(|| EngineError::InvalidOrder("Limit order requires price".to_string()))?;
                Order::new_limit(
                    order_id,
                    request.agent_id,
                    market.clone(),
                    request.side,
                    Price::from_f64(price),
                    Quantity::from_f64(request.quantity),
                    request.time_in_force.unwrap_or(TimeInForce::GTC),
                )
            }
            OrderType::Market => {
                Order::new_market(
                    order_id,
                    request.agent_id,
                    market.clone(),
                    request.side,
                    Quantity::from_f64(request.quantity),
                )
            }
            _ => return Err(EngineError::InvalidOrder("Unsupported order type".to_string())),
        };
        
        // Place order in book
        let mut orderbooks = self.orderbooks.write()
            .map_err(|_| EngineError::InternalError("Lock error".to_string()))?;
        
        let book = orderbooks.get_mut(&market)
            .ok_or_else(|| EngineError::MarketNotFound(market.0.clone()))?;
        
        let trades = book.place_order(order.clone());
        
        Ok((order, trades))
    }
    
    /// Cancel an order
    pub fn cancel_order(&self, request: CancelOrderRequest) -> Result<Order, EngineError> {
        let order_id = OrderId(request.order_id);
        
        let mut orderbooks = self.orderbooks.write()
            .map_err(|_| EngineError::InternalError("Lock error".to_string()))?;
        
        // Search all orderbooks for the order
        for book in orderbooks.values_mut() {
            if let Some(order) = book.cancel_order(&order_id) {
                // Verify ownership
                if order.agent_id != request.agent_id {
                    return Err(EngineError::InvalidOrder("Not order owner".to_string()));
                }
                return Ok(order);
            }
        }
        
        Err(EngineError::OrderNotFound(request.order_id))
    }
    
    /// Get orderbook snapshot
    pub fn get_orderbook(&self, market: &str, depth: usize) -> Result<crate::types::OrderBookSnapshot, EngineError> {
        let market = Market::new(market);
        
        let orderbooks = self.orderbooks.read()
            .map_err(|_| EngineError::InternalError("Lock error".to_string()))?;
        
        let book = orderbooks.get(&market)
            .ok_or_else(|| EngineError::MarketNotFound(market.0.clone()))?;
        
        Ok(book.snapshot(depth))
    }
    
    /// Get best bid/ask for a market
    pub fn get_bbo(&self, market: &str) -> Result<(Option<Price>, Option<Price>), EngineError> {
        let market = Market::new(market);
        
        let orderbooks = self.orderbooks.read()
            .map_err(|_| EngineError::InternalError("Lock error".to_string()))?;
        
        let book = orderbooks.get(&market)
            .ok_or_else(|| EngineError::MarketNotFound(market.0.clone()))?;
        
        Ok((book.best_bid(), book.best_ask()))
    }
}

impl Default for MatchingEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_engine_creation() {
        let engine = MatchingEngine::new();
        assert_eq!(engine.markets().len(), 3);
    }
    
    #[test]
    fn test_place_limit_order() {
        let engine = MatchingEngine::new();
        
        let request = PlaceOrderRequest {
            agent_id: "test-agent".to_string(),
            market: "BTC-PERP".to_string(),
            side: Side::Buy,
            order_type: OrderType::Limit,
            price: Some(50000.0),
            quantity: 1.0,
            time_in_force: Some(TimeInForce::GTC),
            stop_price: None,
            reduce_only: None,
            client_order_id: None,
        };
        
        let result = engine.place_order(request);
        assert!(result.is_ok());
        
        let (order, trades) = result.unwrap();
        assert!(trades.is_empty()); // No matching orders
        assert_eq!(order.market.0, "BTC-PERP");
    }
    
    #[test]
    fn test_order_matching() {
        let engine = MatchingEngine::new();
        
        // Place sell order
        let sell_request = PlaceOrderRequest {
            agent_id: "seller".to_string(),
            market: "BTC-PERP".to_string(),
            side: Side::Sell,
            order_type: OrderType::Limit,
            price: Some(50000.0),
            quantity: 1.0,
            time_in_force: Some(TimeInForce::GTC),
            stop_price: None,
            reduce_only: None,
            client_order_id: None,
        };
        engine.place_order(sell_request).unwrap();
        
        // Place matching buy order
        let buy_request = PlaceOrderRequest {
            agent_id: "buyer".to_string(),
            market: "BTC-PERP".to_string(),
            side: Side::Buy,
            order_type: OrderType::Limit,
            price: Some(50000.0),
            quantity: 0.5,
            time_in_force: Some(TimeInForce::GTC),
            stop_price: None,
            reduce_only: None,
            client_order_id: None,
        };
        
        let (_, trades) = engine.place_order(buy_request).unwrap();
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].maker_agent_id, "seller");
        assert_eq!(trades[0].taker_agent_id, "buyer");
    }
}
