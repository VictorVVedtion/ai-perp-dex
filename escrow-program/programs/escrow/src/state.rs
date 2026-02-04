use anchor_lang::prelude::*;
use crate::ID;

/// 协议配置
#[account]
#[derive(InitSpace)]
pub struct Config {
    /// 管理员
    pub authority: Pubkey,
    /// 开仓费率 (basis points)
    pub fee_bps: u16,
    /// 清算奖励 (basis points)
    pub liquidation_reward_bps: u16,
    /// 国库地址
    pub treasury: Pubkey,
    /// 总仓位数
    pub total_positions: u64,
    /// 总交易量
    pub total_volume: u64,
    /// PDA bump
    pub bump: u8,
}

/// 仓位状态
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum PositionStatus {
    Active = 0,
    Closed = 1,
    Liquidated = 2,
}

/// 仓位
#[account]
#[derive(InitSpace)]
pub struct Position {
    /// 链下生成的唯一 ID
    pub id: [u8; 32],
    /// 交易方
    pub trader: Pubkey,
    /// 做市商
    pub mm: Pubkey,
    /// 市场 (0=BTC, 1=ETH, 2=SOL)
    pub market: u8,
    /// 方向 (0=Long, 1=Short) - trader's side
    pub side: u8,
    /// 仓位大小 (USDC, 6 decimals)
    pub size: u64,
    /// 入场价格 (8 decimals)
    pub entry_price: u64,
    /// 杠杆倍数
    pub leverage: u8,
    /// 资金费率 (signed, 8 decimals)
    pub funding_rate: i64,
    /// 交易方保证金
    pub trader_collateral: u64,
    /// 做市商保证金
    pub mm_collateral: u64,
    /// 状态
    pub status: u8,
    /// 开仓时间
    pub opened_at: i64,
    /// 上次资金费结算时间
    pub last_funding_at: i64,
    /// 平仓时间
    pub closed_at: Option<i64>,
    /// PDA bump
    pub bump: u8,
}
