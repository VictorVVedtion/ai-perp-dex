use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

pub mod state;
pub mod errors;

use state::*;
use errors::*;

#[program]
pub mod escrow {
    use super::*;

    /// 初始化协议配置
    pub fn initialize(
        ctx: Context<Initialize>,
        fee_bps: u16,           // 开仓费率 (basis points, 50 = 0.5%)
        liquidation_reward_bps: u16,  // 清算奖励 (500 = 5%)
    ) -> Result<()> {
        let config = &mut ctx.accounts.config;
        config.authority = ctx.accounts.authority.key();
        config.fee_bps = fee_bps;
        config.liquidation_reward_bps = liquidation_reward_bps;
        config.treasury = ctx.accounts.treasury.key();
        config.total_positions = 0;
        config.total_volume = 0;
        config.bump = ctx.bumps.config;
        
        msg!("Protocol initialized with fee: {}bps", fee_bps);
        Ok(())
    }

    /// 锁定仓位 - 双方保证金
    pub fn lock_position(
        ctx: Context<LockPosition>,
        position_id: [u8; 32],   // 链下生成的唯一 ID
        market: u8,              // 0=BTC, 1=ETH, 2=SOL
        side: u8,                // 0=Long, 1=Short (trader's side)
        size: u64,               // 仓位大小 (USDC, 6 decimals)
        entry_price: u64,        // 入场价格 (8 decimals)
        leverage: u8,            // 杠杆倍数
        funding_rate: i64,       // 资金费率 (signed, 8 decimals)
        trader_collateral: u64,  // 交易方保证金
        mm_collateral: u64,      // 做市商保证金
    ) -> Result<()> {
        require!(leverage >= 1 && leverage <= 100, EscrowError::InvalidLeverage);
        require!(size > 0, EscrowError::InvalidSize);
        
        // 计算开仓费用
        let config = &ctx.accounts.config;
        let fee = size * config.fee_bps as u64 / 10000;
        
        // 转移交易方保证金 + 费用
        let trader_total = trader_collateral.checked_add(fee).ok_or(EscrowError::MathOverflow)?;
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.trader_token.to_account_info(),
                    to: ctx.accounts.escrow_vault.to_account_info(),
                    authority: ctx.accounts.trader.to_account_info(),
                },
            ),
            trader_total,
        )?;
        
        // 转移做市商保证金
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.mm_token.to_account_info(),
                    to: ctx.accounts.escrow_vault.to_account_info(),
                    authority: ctx.accounts.mm.to_account_info(),
                },
            ),
            mm_collateral,
        )?;
        
        // 费用转到国库
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.escrow_vault.to_account_info(),
                    to: ctx.accounts.treasury.to_account_info(),
                    authority: ctx.accounts.escrow_vault.to_account_info(),
                },
                &[&[b"vault", &[ctx.bumps.escrow_vault]]],
            ),
            fee,
        )?;
        
        // 创建仓位记录
        let position = &mut ctx.accounts.position;
        position.id = position_id;
        position.trader = ctx.accounts.trader.key();
        position.mm = ctx.accounts.mm.key();
        position.market = market;
        position.side = side;
        position.size = size;
        position.entry_price = entry_price;
        position.leverage = leverage;
        position.funding_rate = funding_rate;
        position.trader_collateral = trader_collateral;
        position.mm_collateral = mm_collateral;
        position.status = PositionStatus::Active as u8;
        position.opened_at = Clock::get()?.unix_timestamp;
        position.last_funding_at = Clock::get()?.unix_timestamp;
        position.bump = ctx.bumps.position;
        
        // 更新全局统计
        let config = &mut ctx.accounts.config;
        config.total_positions += 1;
        config.total_volume = config.total_volume.saturating_add(size);
        
        msg!("Position locked: market={}, size={}, leverage={}x", market, size, leverage);
        Ok(())
    }

    /// 结算资金费率 (每 8 小时调用一次)
    pub fn settle_funding(ctx: Context<SettleFunding>) -> Result<()> {
        let position = &mut ctx.accounts.position;
        require!(position.status == PositionStatus::Active as u8, EscrowError::PositionNotActive);
        
        let now = Clock::get()?.unix_timestamp;
        let hours_elapsed = (now - position.last_funding_at) / 3600;
        
        require!(hours_elapsed >= 8, EscrowError::TooEarlyForFunding);
        
        // 计算资金费用 (简化: funding_rate * size * periods)
        let periods = hours_elapsed / 8;
        let funding_amount = (position.funding_rate.abs() as u64)
            .saturating_mul(position.size)
            .saturating_mul(periods as u64) / 100_000_000; // 8 decimals
        
        // 多头付给空头 (funding_rate > 0) 或反过来
        if position.funding_rate > 0 {
            // Long pays Short
            if position.side == 0 {
                // Trader is long, pays MM
                position.trader_collateral = position.trader_collateral.saturating_sub(funding_amount);
                position.mm_collateral = position.mm_collateral.saturating_add(funding_amount);
            } else {
                // Trader is short, receives from MM
                position.mm_collateral = position.mm_collateral.saturating_sub(funding_amount);
                position.trader_collateral = position.trader_collateral.saturating_add(funding_amount);
            }
        } else {
            // Short pays Long
            if position.side == 1 {
                // Trader is short, pays MM
                position.trader_collateral = position.trader_collateral.saturating_sub(funding_amount);
                position.mm_collateral = position.mm_collateral.saturating_add(funding_amount);
            } else {
                // Trader is long, receives from MM
                position.mm_collateral = position.mm_collateral.saturating_sub(funding_amount);
                position.trader_collateral = position.trader_collateral.saturating_add(funding_amount);
            }
        }
        
        position.last_funding_at = now;
        
        msg!("Funding settled: amount={}, periods={}", funding_amount, periods);
        Ok(())
    }

    /// 平仓
    pub fn close_position(
        ctx: Context<ClosePosition>,
        exit_price: u64,  // 平仓价格 (8 decimals)
    ) -> Result<()> {
        let position = &mut ctx.accounts.position;
        require!(position.status == PositionStatus::Active as u8, EscrowError::PositionNotActive);
        
        // 计算 PnL
        let (trader_pnl, mm_pnl) = calculate_pnl(
            position.entry_price,
            exit_price,
            position.size,
            position.leverage,
            position.side,
        );
        
        // 计算最终余额
        let trader_final = if trader_pnl >= 0 {
            position.trader_collateral.saturating_add(trader_pnl as u64)
        } else {
            position.trader_collateral.saturating_sub((-trader_pnl) as u64)
        };
        
        let mm_final = if mm_pnl >= 0 {
            position.mm_collateral.saturating_add(mm_pnl as u64)
        } else {
            position.mm_collateral.saturating_sub((-mm_pnl) as u64)
        };
        
        // 确保不会超过总锁定金额
        let total_locked = position.trader_collateral + position.mm_collateral;
        let trader_payout = trader_final.min(total_locked);
        let mm_payout = total_locked.saturating_sub(trader_payout);
        
        // 转账给交易方
        if trader_payout > 0 {
            token::transfer(
                CpiContext::new_with_signer(
                    ctx.accounts.token_program.to_account_info(),
                    Transfer {
                        from: ctx.accounts.escrow_vault.to_account_info(),
                        to: ctx.accounts.trader_token.to_account_info(),
                        authority: ctx.accounts.escrow_vault.to_account_info(),
                    },
                    &[&[b"vault", &[ctx.bumps.escrow_vault]]],
                ),
                trader_payout,
            )?;
        }
        
        // 转账给做市商
        if mm_payout > 0 {
            token::transfer(
                CpiContext::new_with_signer(
                    ctx.accounts.token_program.to_account_info(),
                    Transfer {
                        from: ctx.accounts.escrow_vault.to_account_info(),
                        to: ctx.accounts.mm_token.to_account_info(),
                        authority: ctx.accounts.escrow_vault.to_account_info(),
                    },
                    &[&[b"vault".as_ref(), &[ctx.bumps.escrow_vault]]],
                ),
                mm_payout,
            )?;
        }
        
        // 更新状态
        position.status = PositionStatus::Closed as u8;
        position.closed_at = Some(Clock::get()?.unix_timestamp);
        
        msg!("Position closed: trader_payout={}, mm_payout={}", trader_payout, mm_payout);
        Ok(())
    }

    /// 清算 - 当保证金率低于阈值时
    pub fn liquidate(
        ctx: Context<Liquidate>,
        current_price: u64,  // 当前价格
    ) -> Result<()> {
        let position = &mut ctx.accounts.position;
        let config = &ctx.accounts.config;
        require!(position.status == PositionStatus::Active as u8, EscrowError::PositionNotActive);
        
        // 计算 PnL
        let (trader_pnl, _) = calculate_pnl(
            position.entry_price,
            current_price,
            position.size,
            position.leverage,
            position.side,
        );
        
        // 计算保证金率
        let remaining_collateral = if trader_pnl >= 0 {
            position.trader_collateral.saturating_add(trader_pnl as u64)
        } else {
            position.trader_collateral.saturating_sub((-trader_pnl) as u64)
        };
        
        // 维持保证金 = 初始保证金的 50%
        let maintenance_margin = position.trader_collateral / 2;
        
        require!(remaining_collateral < maintenance_margin, EscrowError::PositionHealthy);
        
        // 清算: 对手方获得全部保证金，清算者获得奖励
        let total_locked = position.trader_collateral + position.mm_collateral;
        let liquidation_reward = total_locked * config.liquidation_reward_bps as u64 / 10000;
        let mm_payout = total_locked.saturating_sub(liquidation_reward);
        
        // 清算奖励给清算者
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.escrow_vault.to_account_info(),
                    to: ctx.accounts.liquidator_token.to_account_info(),
                    authority: ctx.accounts.escrow_vault.to_account_info(),
                },
                &[&[b"vault", &[ctx.bumps.escrow_vault]]],
            ),
            liquidation_reward,
        )?;
        
        // 剩余给做市商
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.escrow_vault.to_account_info(),
                    to: ctx.accounts.mm_token.to_account_info(),
                    authority: ctx.accounts.escrow_vault.to_account_info(),
                },
                &[&[b"vault", &[ctx.bumps.escrow_vault]]],
            ),
            mm_payout,
        )?;
        
        position.status = PositionStatus::Liquidated as u8;
        position.closed_at = Some(Clock::get()?.unix_timestamp);
        
        msg!("Position liquidated: reward={}, mm_payout={}", liquidation_reward, mm_payout);
        Ok(())
    }
}

/// 计算 PnL
fn calculate_pnl(
    entry_price: u64,
    exit_price: u64,
    size: u64,
    leverage: u8,
    side: u8,
) -> (i64, i64) {
    // 价格变化比例 (8 decimals)
    let price_change = if exit_price > entry_price {
        ((exit_price - entry_price) as i128 * 100_000_000 / entry_price as i128) as i64
    } else {
        -(((entry_price - exit_price) as i128 * 100_000_000 / entry_price as i128) as i64)
    };
    
    // 杠杆放大
    let leveraged_change = price_change * leverage as i64;
    
    // PnL (USDC, 6 decimals)
    let pnl = size as i128 * leveraged_change as i128 / 100_000_000;
    
    let trader_pnl = if side == 0 {
        // Long: 价格涨赚钱
        pnl as i64
    } else {
        // Short: 价格跌赚钱
        -pnl as i64
    };
    
    (-trader_pnl, trader_pnl)  // (trader_pnl, mm_pnl) 零和博弈
}

// ===== Contexts =====

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
    
    /// CHECK: Treasury token account
    pub treasury: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(position_id: [u8; 32])]
pub struct LockPosition<'info> {
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
    
    #[account(
        mut,
        seeds = [b"vault"],
        bump
    )]
    pub escrow_vault: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub trader: Signer<'info>,
    
    #[account(mut)]
    pub mm: Signer<'info>,
    
    #[account(mut)]
    pub trader_token: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub mm_token: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub treasury: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SettleFunding<'info> {
    #[account(mut)]
    pub position: Account<'info, Position>,
    
    pub caller: Signer<'info>,
}

#[derive(Accounts)]
pub struct ClosePosition<'info> {
    #[account(mut)]
    pub position: Account<'info, Position>,
    
    #[account(
        mut,
        seeds = [b"vault"],
        bump
    )]
    pub escrow_vault: Account<'info, TokenAccount>,
    
    /// 必须是 trader 或 mm
    #[account(
        constraint = closer.key() == position.trader || closer.key() == position.mm
    )]
    pub closer: Signer<'info>,
    
    #[account(
        mut,
        constraint = trader_token.owner == position.trader
    )]
    pub trader_token: Account<'info, TokenAccount>,
    
    #[account(
        mut,
        constraint = mm_token.owner == position.mm
    )]
    pub mm_token: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct Liquidate<'info> {
    pub config: Account<'info, Config>,
    
    #[account(mut)]
    pub position: Account<'info, Position>,
    
    #[account(
        mut,
        seeds = [b"vault"],
        bump
    )]
    pub escrow_vault: Account<'info, TokenAccount>,
    
    pub liquidator: Signer<'info>,
    
    #[account(mut)]
    pub liquidator_token: Account<'info, TokenAccount>,
    
    #[account(
        mut,
        constraint = mm_token.owner == position.mm
    )]
    pub mm_token: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}
