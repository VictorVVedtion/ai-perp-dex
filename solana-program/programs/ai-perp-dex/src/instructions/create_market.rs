use anchor_lang::prelude::*;
use crate::state::{Exchange, Market};
use crate::errors::PerpError;

#[derive(Accounts)]
#[instruction(market_index: u8)]
pub struct CreateMarket<'info> {
    /// Admin authority
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        seeds = [b"exchange"],
        bump = exchange.bump,
        has_one = authority,
    )]
    pub exchange: Account<'info, Exchange>,
    
    #[account(
        init,
        payer = authority,
        space = Market::SIZE,
        seeds = [b"market", market_index.to_le_bytes().as_ref()],
        bump
    )]
    pub market: Account<'info, Market>,
    
    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<CreateMarket>,
    market_index: u8,
    symbol: [u8; 16],
    initial_margin_rate: u16,
    maintenance_margin_rate: u16,
    max_leverage: u8,
) -> Result<()> {
    require!(initial_margin_rate > 0, PerpError::InvalidParameter);
    require!(maintenance_margin_rate > 0, PerpError::InvalidParameter);
    require!(maintenance_margin_rate < initial_margin_rate, PerpError::InvalidParameter);
    require!(max_leverage > 0 && max_leverage <= 100, PerpError::InvalidParameter);
    
    let market = &mut ctx.accounts.market;
    
    market.index = market_index;
    market.symbol = symbol;
    market.oracle = Pubkey::default(); // To be set via update_market
    market.initial_margin_rate = initial_margin_rate;
    market.maintenance_margin_rate = maintenance_margin_rate;
    market.max_leverage = max_leverage;
    market.long_open_interest = 0;
    market.short_open_interest = 0;
    market.is_active = true;
    market.bump = ctx.bumps.market;
    
    msg!(
        "Market created: index={}, symbol={}, max_leverage={}x",
        market_index,
        String::from_utf8_lossy(&symbol),
        max_leverage
    );
    
    Ok(())
}
