use anchor_lang::prelude::*;

/// Exchange global state
#[account]
#[derive(Default)]
pub struct Exchange {
    /// Authority (admin)
    pub authority: Pubkey,
    /// USDC mint
    pub collateral_mint: Pubkey,
    /// Exchange vault
    pub vault: Pubkey,
    /// Fee rate in basis points (e.g., 10 = 0.1%)
    pub fee_rate_bps: u16,
    /// Total registered agents
    pub total_agents: u64,
    /// Total deposited collateral
    pub total_deposits: u64,
    /// Total open interest
    pub total_open_interest: u64,
    /// Bump seed
    pub bump: u8,
}

impl Exchange {
    pub const SIZE: usize = 8 + // discriminator
        32 + // authority
        32 + // collateral_mint
        32 + // vault
        2 +  // fee_rate_bps
        8 +  // total_agents
        8 +  // total_deposits
        8 +  // total_open_interest
        1;   // bump
}

/// Agent account (PDA per wallet)
#[account]
#[derive(Default)]
pub struct Agent {
    /// Owner wallet
    pub owner: Pubkey,
    /// Agent name
    pub name: [u8; 32],
    /// Collateral balance (USDC, 6 decimals)
    pub collateral: u64,
    /// Unrealized PnL
    pub unrealized_pnl: i64,
    /// Realized PnL
    pub realized_pnl: i64,
    /// Total trades
    pub total_trades: u64,
    /// Win count
    pub win_count: u64,
    /// Registration timestamp
    pub registered_at: i64,
    /// Is active
    pub is_active: bool,
    /// Bump seed
    pub bump: u8,
}

impl Agent {
    pub const SIZE: usize = 8 + // discriminator
        32 + // owner
        32 + // name
        8 +  // collateral
        8 +  // unrealized_pnl
        8 +  // realized_pnl
        8 +  // total_trades
        8 +  // win_count
        8 +  // registered_at
        1 +  // is_active
        1;   // bump
}

/// Position for an agent in a market
#[account]
#[derive(Default)]
pub struct Position {
    /// Agent pubkey
    pub agent: Pubkey,
    /// Market index (0=BTC, 1=ETH, 2=SOL)
    pub market_index: u8,
    /// Size (positive=long, negative=short)
    pub size: i64,
    /// Entry price (6 decimals)
    pub entry_price: u64,
    /// Liquidation price
    pub liquidation_price: u64,
    /// Margin used
    pub margin: u64,
    /// Unrealized PnL
    pub unrealized_pnl: i64,
    /// Open timestamp
    pub opened_at: i64,
    /// Last update timestamp
    pub updated_at: i64,
    /// Bump seed
    pub bump: u8,
}

impl Position {
    pub const SIZE: usize = 8 + // discriminator
        32 + // agent
        1 +  // market_index
        8 +  // size
        8 +  // entry_price
        8 +  // liquidation_price
        8 +  // margin
        8 +  // unrealized_pnl
        8 +  // opened_at
        8 +  // updated_at
        1;   // bump
}

/// Market configuration
#[account]
#[derive(Default)]
pub struct Market {
    /// Market index
    pub index: u8,
    /// Symbol (e.g., "BTC-PERP")
    pub symbol: [u8; 16],
    /// Oracle price feed
    pub oracle: Pubkey,
    /// Initial margin rate (e.g., 1000 = 10%)
    pub initial_margin_rate: u16,
    /// Maintenance margin rate (e.g., 500 = 5%)
    pub maintenance_margin_rate: u16,
    /// Max leverage (e.g., 10)
    pub max_leverage: u8,
    /// Total long open interest
    pub long_open_interest: u64,
    /// Total short open interest
    pub short_open_interest: u64,
    /// Is active
    pub is_active: bool,
    /// Bump seed
    pub bump: u8,
}

impl Market {
    pub const SIZE: usize = 8 + // discriminator
        1 +  // index
        16 + // symbol
        32 + // oracle
        2 +  // initial_margin_rate
        2 +  // maintenance_margin_rate
        1 +  // max_leverage
        8 +  // long_open_interest
        8 +  // short_open_interest
        1 +  // is_active
        1;   // bump
}

/// Trade history record
#[account]
pub struct TradeRecord {
    /// Trade ID
    pub trade_id: u64,
    /// Market index
    pub market_index: u8,
    /// Maker agent
    pub maker: Pubkey,
    /// Taker agent
    pub taker: Pubkey,
    /// Price
    pub price: u64,
    /// Size
    pub size: u64,
    /// Maker fee
    pub maker_fee: u64,
    /// Taker fee
    pub taker_fee: u64,
    /// Timestamp
    pub timestamp: i64,
    /// Bump seed
    pub bump: u8,
}

impl TradeRecord {
    pub const SIZE: usize = 8 + // discriminator
        8 +  // trade_id
        1 +  // market_index
        32 + // maker
        32 + // taker
        8 +  // price
        8 +  // size
        8 +  // maker_fee
        8 +  // taker_fee
        8 +  // timestamp
        1;   // bump
}
