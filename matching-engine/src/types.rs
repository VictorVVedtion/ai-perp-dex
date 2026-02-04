//! Core types for AI Perp DEX

use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::fmt;

/// Unique identifier for orders
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct OrderId(pub u64);

impl fmt::Display for OrderId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "ORD-{:016X}", self.0)
    }
}

/// Unique identifier for trades
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TradeId(pub u64);

impl fmt::Display for TradeId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "TRD-{:016X}", self.0)
    }
}

/// Market identifier (e.g., BTC-PERP)
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Market(pub String);

impl Market {
    pub fn new(symbol: &str) -> Self {
        Self(symbol.to_uppercase())
    }
    
    pub fn btc_perp() -> Self {
        Self::new("BTC-PERP")
    }
    
    pub fn eth_perp() -> Self {
        Self::new("ETH-PERP")
    }
    
    pub fn sol_perp() -> Self {
        Self::new("SOL-PERP")
    }
}

/// Price with decimal precision
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Price(pub Decimal);

impl Price {
    pub fn new(value: Decimal) -> Self {
        Self(value)
    }
    
    pub fn from_f64(value: f64) -> Self {
        Self(Decimal::try_from(value).unwrap_or_default())
    }
    
    pub fn as_decimal(&self) -> Decimal {
        self.0
    }
}

/// Quantity/Size
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, Default)]
pub struct Quantity(pub Decimal);

impl Quantity {
    pub fn new(value: Decimal) -> Self {
        Self(value)
    }
    
    pub fn from_f64(value: f64) -> Self {
        Self(Decimal::try_from(value).unwrap_or_default())
    }
    
    pub fn as_decimal(&self) -> Decimal {
        self.0
    }
    
    pub fn is_zero(&self) -> bool {
        self.0.is_zero()
    }
}

impl std::ops::Sub for Quantity {
    type Output = Self;
    
    fn sub(self, rhs: Self) -> Self::Output {
        Self(self.0 - rhs.0)
    }
}

impl std::ops::SubAssign for Quantity {
    fn sub_assign(&mut self, rhs: Self) {
        self.0 -= rhs.0;
    }
}

/// Timestamp in nanoseconds
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Timestamp(pub u64);

impl Timestamp {
    pub fn now() -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64;
        Self(nanos)
    }
    
    pub fn as_nanos(&self) -> u64 {
        self.0
    }
}

/// Trade execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub id: TradeId,
    pub market: Market,
    pub price: Price,
    pub quantity: Quantity,
    pub maker_order_id: OrderId,
    pub taker_order_id: OrderId,
    pub maker_agent_id: String,
    pub taker_agent_id: String,
    pub timestamp: Timestamp,
}

/// Orderbook snapshot at a price level
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriceLevel {
    pub price: Price,
    pub quantity: Quantity,
    pub order_count: u32,
}

/// Full orderbook snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderBookSnapshot {
    pub market: Market,
    pub bids: Vec<PriceLevel>,
    pub asks: Vec<PriceLevel>,
    pub timestamp: Timestamp,
    pub sequence: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_order_id_display() {
        let id = OrderId(12345);
        assert_eq!(format!("{}", id), "ORD-0000000000003039");
    }
    
    #[test]
    fn test_market_creation() {
        let market = Market::new("btc-perp");
        assert_eq!(market.0, "BTC-PERP");
    }
    
    #[test]
    fn test_timestamp_ordering() {
        let t1 = Timestamp::now();
        std::thread::sleep(std::time::Duration::from_millis(1));
        let t2 = Timestamp::now();
        assert!(t2 > t1);
    }
}
