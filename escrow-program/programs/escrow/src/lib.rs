use anchor_lang::prelude::*;

declare_id!("6F37235k7H3JXTPvRv9w1uAAdPKkcD9avVqmzUTxGpRC");

#[program]
pub mod escrow {
    use super::*;

    /// 初始化协议配置
    pub fn initialize(
        ctx: Context<Initialize>,
        fee_bps: u16,
        liquidation_reward_bps: u16,
    ) -> Result<()> {
        let config = &mut ctx.accounts.config;
        config.authority = ctx.accounts.authority.key();
        config.fee_bps = fee_bps;
        config.liquidation_reward_bps = liquidation_reward_bps;
        config.total_positions = 0;
        config.total_volume = 0;
        config.bump = *ctx.bumps.get("config").unwrap();
        
        msg!("Protocol initialized with fee: {}bps", fee_bps);
        Ok(())
    }

    /// 创建仓位 (简化版: 不涉及真实 token 转账，用于 MVP 测试)
    pub fn create_position(
        ctx: Context<CreatePosition>,
        position_id: [u8; 32],
        market: u8,              // 0=BTC, 1=ETH, 2=SOL
        side: u8,                // 0=Long, 1=Short
        size: u64,               // USDC, 6 decimals
        entry_price: u64,        // 8 decimals
        leverage: u8,
        trader_collateral: u64,
        mm_collateral: u64,
    ) -> Result<()> {
        require!(leverage >= 1 && leverage <= 100, EscrowError::InvalidLeverage);
        require!(size > 0, EscrowError::InvalidSize);
        
        let position = &mut ctx.accounts.position;
        position.id = position_id;
        position.trader = ctx.accounts.trader.key();
        position.mm = ctx.accounts.mm.key();
        position.market = market;
        position.side = side;
        position.size = size;
        position.entry_price = entry_price;
        position.leverage = leverage;
        position.trader_collateral = trader_collateral;
        position.mm_collateral = mm_collateral;
        position.status = 0; // Active
        position.opened_at = Clock::get()?.unix_timestamp;
        position.bump = *ctx.bumps.get("position").unwrap();
        
        // 更新统计
        let config = &mut ctx.accounts.config;
        config.total_positions += 1;
        config.total_volume = config.total_volume.saturating_add(size);
        
        msg!("Position created: market={}, size={}, leverage={}x", market, size, leverage);
        Ok(())
    }

    /// 平仓
    pub fn close_position(
        ctx: Context<ClosePosition>,
        exit_price: u64,
    ) -> Result<()> {
        let position = &mut ctx.accounts.position;
        require!(position.status == 0, EscrowError::PositionNotActive);
        
        // 计算 PnL (简化版)
        let (trader_pnl, mm_pnl) = calculate_pnl(
            position.entry_price,
            exit_price,
            position.size,
            position.leverage,
            position.side,
        );
        
        // 记录结算结果 (实际转账在链下完成)
        position.status = 1; // Closed
        position.exit_price = Some(exit_price);
        position.closed_at = Some(Clock::get()?.unix_timestamp);
        position.trader_pnl = trader_pnl;
        position.mm_pnl = mm_pnl;
        
        msg!("Position closed: trader_pnl={}, mm_pnl={}", trader_pnl, mm_pnl);
        Ok(())
    }

    /// 清算
    pub fn liquidate(
        ctx: Context<Liquidate>,
        current_price: u64,
    ) -> Result<()> {
        let position = &mut ctx.accounts.position;
        require!(position.status == 0, EscrowError::PositionNotActive);
        
        // 计算 PnL
        let (trader_pnl, _) = calculate_pnl(
            position.entry_price,
            current_price,
            position.size,
            position.leverage,
            position.side,
        );
        
        // 检查是否可清算 (亏损超过 80% 保证金)
        let loss_threshold = (position.trader_collateral as i64) * 80 / 100;
        require!(trader_pnl < -loss_threshold, EscrowError::PositionHealthy);
        
        position.status = 2; // Liquidated
        position.exit_price = Some(current_price);
        position.closed_at = Some(Clock::get()?.unix_timestamp);
        position.liquidator = Some(ctx.accounts.liquidator.key());
        
        msg!("Position liquidated at price {}", current_price);
        Ok(())
    }
}

fn calculate_pnl(
    entry_price: u64,
    exit_price: u64,
    size: u64,
    leverage: u8,
    side: u8,
) -> (i64, i64) {
    let price_change = if exit_price > entry_price {
        ((exit_price - entry_price) as i128 * 100_000_000 / entry_price as i128) as i64
    } else {
        -(((entry_price - exit_price) as i128 * 100_000_000 / entry_price as i128) as i64)
    };
    
    let leveraged_change = price_change * leverage as i64;
    let pnl = size as i128 * leveraged_change as i128 / 100_000_000;
    
    let trader_pnl = if side == 0 { pnl as i64 } else { -pnl as i64 };
    (-trader_pnl, trader_pnl)
}

// ===== Accounts =====

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Config::INIT_SPACE,
        seeds = [b"config"],
        bump
    )]
    pub config: Account<'info, Config>,
    
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(position_id: [u8; 32])]
pub struct CreatePosition<'info> {
    #[account(
        mut,
        seeds = [b"config"],
        bump = config.bump
    )]
    pub config: Account<'info, Config>,
    
    #[account(
        init,
        payer = trader,
        space = 8 + Position::INIT_SPACE,
        seeds = [b"position", position_id.as_ref()],
        bump
    )]
    pub position: Account<'info, Position>,
    
    #[account(mut)]
    pub trader: Signer<'info>,
    
    /// CHECK: MM just signs, no lamport transfer in MVP
    pub mm: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ClosePosition<'info> {
    #[account(
        mut,
        constraint = closer.key() == position.trader || closer.key() == position.mm
    )]
    pub position: Account<'info, Position>,
    
    pub closer: Signer<'info>,
}

#[derive(Accounts)]
pub struct Liquidate<'info> {
    #[account(mut)]
    pub position: Account<'info, Position>,
    
    pub liquidator: Signer<'info>,
}

// ===== State =====

#[account]
#[derive(InitSpace)]
pub struct Config {
    pub authority: Pubkey,
    pub fee_bps: u16,
    pub liquidation_reward_bps: u16,
    pub total_positions: u64,
    pub total_volume: u64,
    pub bump: u8,
}

#[account]
#[derive(InitSpace)]
pub struct Position {
    pub id: [u8; 32],
    pub trader: Pubkey,
    pub mm: Pubkey,
    pub market: u8,
    pub side: u8,
    pub size: u64,
    pub entry_price: u64,
    pub leverage: u8,
    pub trader_collateral: u64,
    pub mm_collateral: u64,
    pub status: u8,  // 0=Active, 1=Closed, 2=Liquidated
    pub opened_at: i64,
    pub closed_at: Option<i64>,
    pub exit_price: Option<u64>,
    pub trader_pnl: i64,
    pub mm_pnl: i64,
    pub liquidator: Option<Pubkey>,
    pub bump: u8,
}

// ===== Errors =====

#[error_code]
pub enum EscrowError {
    #[msg("Invalid leverage, must be 1-100")]
    InvalidLeverage,
    
    #[msg("Invalid size, must be greater than 0")]
    InvalidSize,
    
    #[msg("Position is not active")]
    PositionNotActive,
    
    #[msg("Position is healthy, cannot liquidate")]
    PositionHealthy,
}
