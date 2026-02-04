//! Order types and structures

use crate::types::{Market, OrderId, Price, Quantity, Timestamp};
use serde::{Deserialize, Serialize};

/// Order side (buy or sell)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Side {
    Buy,
    Sell,
}

impl Side {
    pub fn opposite(&self) -> Self {
        match self {
            Side::Buy => Side::Sell,
            Side::Sell => Side::Buy,
        }
    }
}

/// Order type
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderType {
    /// Limit order - execute at specified price or better
    Limit,
    /// Market order - execute immediately at best available price
    Market,
    /// Stop limit - becomes limit order when stop price is reached
    StopLimit,
    /// Stop market - becomes market order when stop price is reached
    StopMarket,
}

/// Time in force
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TimeInForce {
    /// Good Till Cancelled - remains active until filled or cancelled
    GTC,
    /// Immediate Or Cancel - fill immediately, cancel unfilled portion
    IOC,
    /// Fill Or Kill - fill entirely or cancel entirely
    FOK,
    /// Post Only - only add liquidity, cancel if would take
    PostOnly,
}

/// Order status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderStatus {
    /// Order is active in the book
    Open,
    /// Order is partially filled
    PartiallyFilled,
    /// Order is completely filled
    Filled,
    /// Order was cancelled
    Cancelled,
    /// Order was rejected
    Rejected,
    /// Order expired
    Expired,
}

/// An order in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    /// Unique order identifier
    pub id: OrderId,
    /// Agent who placed the order
    pub agent_id: String,
    /// Market (e.g., BTC-PERP)
    pub market: Market,
    /// Buy or Sell
    pub side: Side,
    /// Order type
    pub order_type: OrderType,
    /// Limit price (None for market orders)
    pub price: Option<Price>,
    /// Order quantity
    pub quantity: Quantity,
    /// Remaining unfilled quantity
    pub remaining_quantity: Quantity,
    /// Time in force
    pub time_in_force: TimeInForce,
    /// Current status
    pub status: OrderStatus,
    /// Order creation timestamp
    pub created_at: Timestamp,
    /// Last update timestamp
    pub updated_at: Timestamp,
    /// Stop price for stop orders
    pub stop_price: Option<Price>,
    /// Reduce only flag
    pub reduce_only: bool,
    /// Client order ID (optional, for agent tracking)
    pub client_order_id: Option<String>,
}

impl Order {
    /// Create a new limit order
    pub fn new_limit(
        id: OrderId,
        agent_id: String,
        market: Market,
        side: Side,
        price: Price,
        quantity: Quantity,
        time_in_force: TimeInForce,
    ) -> Self {
        let now = Timestamp::now();
        Self {
            id,
            agent_id,
            market,
            side,
            order_type: OrderType::Limit,
            price: Some(price),
            quantity,
            remaining_quantity: quantity,
            time_in_force,
            status: OrderStatus::Open,
            created_at: now,
            updated_at: now,
            stop_price: None,
            reduce_only: false,
            client_order_id: None,
        }
    }
    
    /// Create a new market order
    pub fn new_market(
        id: OrderId,
        agent_id: String,
        market: Market,
        side: Side,
        quantity: Quantity,
    ) -> Self {
        let now = Timestamp::now();
        Self {
            id,
            agent_id,
            market,
            side,
            order_type: OrderType::Market,
            price: None,
            quantity,
            remaining_quantity: quantity,
            time_in_force: TimeInForce::IOC,
            status: OrderStatus::Open,
            created_at: now,
            updated_at: now,
            stop_price: None,
            reduce_only: false,
            client_order_id: None,
        }
    }
    
    /// Check if order is fully filled
    pub fn is_filled(&self) -> bool {
        self.remaining_quantity.is_zero()
    }
    
    /// Check if order can be matched (not cancelled, not filled)
    pub fn is_active(&self) -> bool {
        matches!(self.status, OrderStatus::Open | OrderStatus::PartiallyFilled)
    }
    
    /// Fill some quantity
    pub fn fill(&mut self, qty: Quantity) {
        self.remaining_quantity -= qty;
        self.updated_at = Timestamp::now();
        
        if self.remaining_quantity.is_zero() {
            self.status = OrderStatus::Filled;
        } else {
            self.status = OrderStatus::PartiallyFilled;
        }
    }
    
    /// Cancel the order
    pub fn cancel(&mut self) {
        self.status = OrderStatus::Cancelled;
        self.updated_at = Timestamp::now();
    }
}

/// Request to place a new order
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlaceOrderRequest {
    pub agent_id: String,
    pub market: String,
    pub side: Side,
    pub order_type: OrderType,
    pub price: Option<f64>,
    pub quantity: f64,
    pub time_in_force: Option<TimeInForce>,
    pub stop_price: Option<f64>,
    pub reduce_only: Option<bool>,
    pub client_order_id: Option<String>,
}

/// Request to cancel an order
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CancelOrderRequest {
    pub agent_id: String,
    pub order_id: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;
    
    #[test]
    fn test_limit_order_creation() {
        let order = Order::new_limit(
            OrderId(1),
            "agent-1".to_string(),
            Market::btc_perp(),
            Side::Buy,
            Price::new(dec!(50000)),
            Quantity::new(dec!(0.1)),
            TimeInForce::GTC,
        );
        
        assert_eq!(order.side, Side::Buy);
        assert_eq!(order.status, OrderStatus::Open);
        assert!(order.is_active());
    }
    
    #[test]
    fn test_order_fill() {
        let mut order = Order::new_limit(
            OrderId(1),
            "agent-1".to_string(),
            Market::btc_perp(),
            Side::Buy,
            Price::new(dec!(50000)),
            Quantity::new(dec!(1.0)),
            TimeInForce::GTC,
        );
        
        order.fill(Quantity::new(dec!(0.5)));
        assert_eq!(order.status, OrderStatus::PartiallyFilled);
        assert_eq!(order.remaining_quantity.as_decimal(), dec!(0.5));
        
        order.fill(Quantity::new(dec!(0.5)));
        assert_eq!(order.status, OrderStatus::Filled);
        assert!(order.is_filled());
    }
}
