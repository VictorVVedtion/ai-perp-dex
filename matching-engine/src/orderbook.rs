//! Orderbook implementation with price-time priority matching

use crate::order::{Order, Side, TimeInForce};
use crate::types::{Market, OrderId, Price, PriceLevel, Quantity, OrderBookSnapshot, Timestamp, Trade, TradeId};
use indexmap::IndexMap;
use std::collections::{BTreeMap, HashMap};
use std::sync::atomic::{AtomicU64, Ordering};

/// A single price level in the orderbook
#[derive(Debug, Default)]
struct Level {
    /// Orders at this price level, ordered by time (FIFO)
    orders: IndexMap<OrderId, Order>,
    /// Total quantity at this level
    total_quantity: Quantity,
}

impl Level {
    fn new() -> Self {
        Self {
            orders: IndexMap::new(),
            total_quantity: Quantity::new(rust_decimal::Decimal::ZERO),
        }
    }
    
    fn add_order(&mut self, order: Order) {
        let qty = order.remaining_quantity;
        self.orders.insert(order.id, order);
        self.total_quantity = Quantity::new(self.total_quantity.as_decimal() + qty.as_decimal());
    }
    
    fn remove_order(&mut self, order_id: &OrderId) -> Option<Order> {
        if let Some(order) = self.orders.shift_remove(order_id) {
            self.total_quantity = Quantity::new(
                self.total_quantity.as_decimal() - order.remaining_quantity.as_decimal()
            );
            Some(order)
        } else {
            None
        }
    }
    
    fn is_empty(&self) -> bool {
        self.orders.is_empty()
    }
    
    fn order_count(&self) -> u32 {
        self.orders.len() as u32
    }
}

/// The orderbook for a single market
pub struct OrderBook {
    /// Market identifier
    market: Market,
    /// Bid levels (sorted descending by price - highest first)
    bids: BTreeMap<Price, Level>,
    /// Ask levels (sorted ascending by price - lowest first)
    asks: BTreeMap<Price, Level>,
    /// Order lookup by ID
    orders: HashMap<OrderId, (Price, Side)>,
    /// Sequence number for updates
    sequence: AtomicU64,
    /// Trade ID counter
    trade_counter: AtomicU64,
    /// Best bid price
    best_bid: Option<Price>,
    /// Best ask price
    best_ask: Option<Price>,
}

impl OrderBook {
    /// Create a new orderbook for a market
    pub fn new(market: Market) -> Self {
        Self {
            market,
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
            orders: HashMap::new(),
            sequence: AtomicU64::new(0),
            trade_counter: AtomicU64::new(0),
            best_bid: None,
            best_ask: None,
        }
    }
    
    /// Get the market
    pub fn market(&self) -> &Market {
        &self.market
    }
    
    /// Get best bid price
    pub fn best_bid(&self) -> Option<Price> {
        self.best_bid
    }
    
    /// Get best ask price
    pub fn best_ask(&self) -> Option<Price> {
        self.best_ask
    }
    
    /// Get the spread
    pub fn spread(&self) -> Option<rust_decimal::Decimal> {
        match (self.best_ask, self.best_bid) {
            (Some(ask), Some(bid)) => Some(ask.as_decimal() - bid.as_decimal()),
            _ => None,
        }
    }
    
    /// Get mid price
    pub fn mid_price(&self) -> Option<Price> {
        match (self.best_ask, self.best_bid) {
            (Some(ask), Some(bid)) => {
                let mid = (ask.as_decimal() + bid.as_decimal()) / rust_decimal::Decimal::TWO;
                Some(Price::new(mid))
            }
            _ => None,
        }
    }
    
    /// Place an order and return any resulting trades
    pub fn place_order(&mut self, mut order: Order) -> Vec<Trade> {
        let mut trades = Vec::new();
        
        // Try to match the order
        trades = self.match_order(&mut order);
        
        // If order is still active and not IOC/FOK, add to book
        if order.is_active() && !order.remaining_quantity.is_zero() {
            match order.time_in_force {
                TimeInForce::IOC => {
                    order.cancel();
                }
                TimeInForce::FOK => {
                    // FOK should have been fully filled or rejected
                    order.cancel();
                }
                TimeInForce::PostOnly => {
                    // PostOnly orders that would have matched are rejected
                    if !trades.is_empty() {
                        trades.clear();
                        order.cancel();
                    } else {
                        self.add_order_to_book(order);
                    }
                }
                TimeInForce::GTC => {
                    self.add_order_to_book(order);
                }
            }
        }
        
        self.update_best_prices();
        self.sequence.fetch_add(1, Ordering::SeqCst);
        
        trades
    }
    
    /// Match an incoming order against the book
    fn match_order(&mut self, order: &mut Order) -> Vec<Trade> {
        let mut trades = Vec::new();
        
        let opposite_side = match order.side {
            Side::Buy => &mut self.asks,
            Side::Sell => &mut self.bids,
        };
        
        let prices_to_remove: Vec<Price> = Vec::new();
        
        // Get prices to match against
        let matching_prices: Vec<Price> = match order.side {
            Side::Buy => opposite_side.keys().cloned().collect(),
            Side::Sell => opposite_side.keys().rev().cloned().collect(),
        };
        
        for price in matching_prices {
            if order.remaining_quantity.is_zero() {
                break;
            }
            
            // Check price compatibility
            if let Some(limit_price) = order.price {
                match order.side {
                    Side::Buy if price > limit_price => break,
                    Side::Sell if price < limit_price => break,
                    _ => {}
                }
            }
            
            // Match against orders at this price level
            if let Some(level) = opposite_side.get_mut(&price) {
                let order_ids: Vec<OrderId> = level.orders.keys().cloned().collect();
                
                for maker_order_id in order_ids {
                    if order.remaining_quantity.is_zero() {
                        break;
                    }
                    
                    if let Some(maker_order) = level.orders.get_mut(&maker_order_id) {
                        let fill_qty = std::cmp::min(
                            order.remaining_quantity,
                            maker_order.remaining_quantity,
                        );
                        
                        // Create trade
                        let trade = Trade {
                            id: TradeId(self.trade_counter.fetch_add(1, Ordering::SeqCst)),
                            market: self.market.clone(),
                            price,
                            quantity: fill_qty,
                            maker_order_id,
                            taker_order_id: order.id,
                            maker_agent_id: maker_order.agent_id.clone(),
                            taker_agent_id: order.agent_id.clone(),
                            timestamp: Timestamp::now(),
                        };
                        
                        trades.push(trade);
                        
                        // Update quantities
                        order.fill(fill_qty);
                        maker_order.fill(fill_qty);
                        level.total_quantity = Quantity::new(
                            level.total_quantity.as_decimal() - fill_qty.as_decimal()
                        );
                        
                        // Remove filled maker order
                        if maker_order.is_filled() {
                            self.orders.remove(&maker_order_id);
                        }
                    }
                }
                
                // Remove filled orders from level
                level.orders.retain(|_, o| !o.is_filled());
            }
        }
        
        // Remove empty price levels
        match order.side {
            Side::Buy => self.asks.retain(|_, level| !level.is_empty()),
            Side::Sell => self.bids.retain(|_, level| !level.is_empty()),
        }
        
        trades
    }
    
    /// Add an order to the orderbook
    fn add_order_to_book(&mut self, order: Order) {
        let price = order.price.expect("Limit order must have price");
        let side = order.side;
        let order_id = order.id;
        
        let levels = match side {
            Side::Buy => &mut self.bids,
            Side::Sell => &mut self.asks,
        };
        
        levels
            .entry(price)
            .or_insert_with(Level::new)
            .add_order(order);
        
        self.orders.insert(order_id, (price, side));
    }
    
    /// Cancel an order
    pub fn cancel_order(&mut self, order_id: &OrderId) -> Option<Order> {
        if let Some((price, side)) = self.orders.remove(order_id) {
            let levels = match side {
                Side::Buy => &mut self.bids,
                Side::Sell => &mut self.asks,
            };
            
            if let Some(level) = levels.get_mut(&price) {
                let mut order = level.remove_order(order_id)?;
                order.cancel();
                
                if level.is_empty() {
                    levels.remove(&price);
                }
                
                self.update_best_prices();
                self.sequence.fetch_add(1, Ordering::SeqCst);
                
                return Some(order);
            }
        }
        None
    }
    
    /// Update best bid/ask prices
    fn update_best_prices(&mut self) {
        self.best_bid = self.bids.keys().next_back().cloned();
        self.best_ask = self.asks.keys().next().cloned();
    }
    
    /// Get orderbook snapshot
    pub fn snapshot(&self, depth: usize) -> OrderBookSnapshot {
        let bids: Vec<PriceLevel> = self.bids
            .iter()
            .rev()
            .take(depth)
            .map(|(price, level)| PriceLevel {
                price: *price,
                quantity: level.total_quantity,
                order_count: level.order_count(),
            })
            .collect();
        
        let asks: Vec<PriceLevel> = self.asks
            .iter()
            .take(depth)
            .map(|(price, level)| PriceLevel {
                price: *price,
                quantity: level.total_quantity,
                order_count: level.order_count(),
            })
            .collect();
        
        OrderBookSnapshot {
            market: self.market.clone(),
            bids,
            asks,
            timestamp: Timestamp::now(),
            sequence: self.sequence.load(Ordering::SeqCst),
        }
    }
    
    /// Get an order by ID
    pub fn get_order(&self, order_id: &OrderId) -> Option<&Order> {
        if let Some((price, side)) = self.orders.get(order_id) {
            let levels = match side {
                Side::Buy => &self.bids,
                Side::Sell => &self.asks,
            };
            
            levels.get(price)?.orders.get(order_id)
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;
    
    fn create_test_order(id: u64, side: Side, price: f64, qty: f64) -> Order {
        Order::new_limit(
            OrderId(id),
            "test-agent".to_string(),
            Market::btc_perp(),
            side,
            Price::from_f64(price),
            Quantity::from_f64(qty),
            TimeInForce::GTC,
        )
    }
    
    #[test]
    fn test_add_and_cancel_order() {
        let mut book = OrderBook::new(Market::btc_perp());
        
        let order = create_test_order(1, Side::Buy, 50000.0, 1.0);
        let trades = book.place_order(order);
        
        assert!(trades.is_empty());
        assert_eq!(book.best_bid(), Some(Price::from_f64(50000.0)));
        
        let cancelled = book.cancel_order(&OrderId(1));
        assert!(cancelled.is_some());
        assert!(book.best_bid().is_none());
    }
    
    #[test]
    fn test_order_matching() {
        let mut book = OrderBook::new(Market::btc_perp());
        
        // Add a sell order
        let sell_order = create_test_order(1, Side::Sell, 50000.0, 1.0);
        book.place_order(sell_order);
        
        // Add a matching buy order
        let buy_order = create_test_order(2, Side::Buy, 50000.0, 0.5);
        let trades = book.place_order(buy_order);
        
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].quantity.as_decimal(), dec!(0.5));
        assert_eq!(trades[0].price, Price::from_f64(50000.0));
    }
    
    #[test]
    fn test_price_time_priority() {
        let mut book = OrderBook::new(Market::btc_perp());
        
        // Add two sell orders at same price
        let sell1 = create_test_order(1, Side::Sell, 50000.0, 1.0);
        let sell2 = create_test_order(2, Side::Sell, 50000.0, 1.0);
        book.place_order(sell1);
        book.place_order(sell2);
        
        // Buy order should match with first sell order (time priority)
        let buy = create_test_order(3, Side::Buy, 50000.0, 0.5);
        let trades = book.place_order(buy);
        
        assert_eq!(trades.len(), 1);
        assert_eq!(trades[0].maker_order_id, OrderId(1)); // First order matched
    }
    
    #[test]
    fn test_spread_calculation() {
        let mut book = OrderBook::new(Market::btc_perp());
        
        book.place_order(create_test_order(1, Side::Buy, 49900.0, 1.0));
        book.place_order(create_test_order(2, Side::Sell, 50100.0, 1.0));
        
        assert_eq!(book.spread(), Some(dec!(200.0)));
        assert_eq!(book.mid_price().map(|p| p.as_decimal()), Some(dec!(50000.0)));
    }
}
