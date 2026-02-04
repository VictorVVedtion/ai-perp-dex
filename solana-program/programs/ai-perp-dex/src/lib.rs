use anchor_lang::prelude::*;

declare_id!("GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk");

pub mod state;
pub mod instructions;
pub mod errors;

use instructions::*;

#[program]
pub mod ai_perp_dex {
    use super::*;

    /// Initialize the exchange
    pub fn initialize(ctx: Context<Initialize>, fee_rate_bps: u16) -> Result<()> {
        instructions::initialize::handler(ctx, fee_rate_bps)
    }

    /// Register a new agent
    pub fn register_agent(ctx: Context<RegisterAgent>, name: String) -> Result<()> {
        instructions::register_agent::handler(ctx, name)
    }

    /// Deposit collateral
    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        instructions::deposit::handler(ctx, amount)
    }

    /// Withdraw collateral
    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        instructions::withdraw::handler(ctx, amount)
    }

    /// Open a position (called by matching engine)
    pub fn open_position(
        ctx: Context<OpenPosition>,
        market_index: u8,
        size: i64,
        entry_price: u64,
    ) -> Result<()> {
        instructions::open_position::handler(ctx, market_index, size, entry_price)
    }

    /// Close a position
    pub fn close_position(
        ctx: Context<ClosePosition>,
        market_index: u8,
        exit_price: u64,
    ) -> Result<()> {
        instructions::close_position::handler(ctx, market_index, exit_price)
    }

    /// Liquidate an underwater position
    pub fn liquidate(ctx: Context<Liquidate>, market_index: u8) -> Result<()> {
        instructions::liquidate::handler(ctx, market_index)
    }

    /// Settle PnL for a position
    pub fn settle_pnl(ctx: Context<SettlePnl>, market_index: u8) -> Result<()> {
        instructions::settle_pnl::handler(ctx, market_index)
    }
}
