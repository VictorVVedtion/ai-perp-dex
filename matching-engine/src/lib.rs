//! AI Perp DEX - High Performance Matching Engine
//! 
//! A price-time priority orderbook designed for AI agent trading.

pub mod orderbook;
pub mod order;
pub mod engine;
pub mod types;
pub mod agent;
pub mod api;
pub mod risk;

pub use orderbook::OrderBook;
pub use order::{Order, OrderType, Side, TimeInForce};
pub use engine::MatchingEngine;
pub use types::*;
pub use agent::{Agent, AgentId};
