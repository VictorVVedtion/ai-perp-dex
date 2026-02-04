use anchor_lang::prelude::*;
use pyth_sdk_solana::state::SolanaPriceAccount;

/// Oracle error codes
#[error_code]
pub enum OracleError {
    #[msg("Oracle price is stale")]
    StalePrice,
    #[msg("Oracle price is negative")]
    NegativePrice,
    #[msg("Invalid oracle account")]
    InvalidOracle,
    #[msg("Price confidence interval too wide")]
    PriceUncertain,
}

/// Maximum age for price updates (60 seconds)
pub const MAX_PRICE_AGE_SECS: u64 = 60;

/// Maximum confidence interval ratio (5%)
pub const MAX_CONFIDENCE_RATIO: u64 = 500; // basis points

/// Pyth Price Feed Addresses (Devnet)
pub mod price_feeds {
    use anchor_lang::prelude::*;
    use std::str::FromStr;
    
    /// BTC/USD Price Feed (Pyth Devnet)
    pub fn btc_usd() -> Pubkey {
        Pubkey::from_str("HovQMDrbAgAYPCmHVSrezcSmkMtXSSUsLDFANExrZh2J").unwrap()
    }
    
    /// ETH/USD Price Feed (Pyth Devnet)
    pub fn eth_usd() -> Pubkey {
        Pubkey::from_str("EdVCmQ9FSPcVe5YySXDPCRmc8aDQLKJ9xvYBMZPie1Vw").unwrap()
    }
    
    /// SOL/USD Price Feed (Pyth Devnet)
    pub fn sol_usd() -> Pubkey {
        Pubkey::from_str("J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix").unwrap()
    }
}

/// Get the price from a Pyth price account
/// Returns the price in 6 decimal precision (matching USDC)
pub fn get_price_from_pyth(
    price_account: &AccountInfo,
    max_age: u64,
) -> Result<u64> {
    let clock = Clock::get()?;
    let current_timestamp = clock.unix_timestamp as u64;
    
    // Load the price account
    let price_feed = SolanaPriceAccount::account_info_to_feed(price_account)
        .map_err(|_| OracleError::InvalidOracle)?;
    
    // Get current price
    let price = price_feed
        .get_price_no_older_than(current_timestamp as i64, max_age)
        .ok_or(OracleError::StalePrice)?;
    
    // Check for negative price
    if price.price < 0 {
        return Err(OracleError::NegativePrice.into());
    }
    
    // Check confidence interval
    let price_abs = price.price as u64;
    let conf = price.conf;
    
    // Confidence should be less than MAX_CONFIDENCE_RATIO% of price
    if conf > 0 && price_abs > 0 {
        let conf_ratio = (conf * 10000) / price_abs;
        if conf_ratio > MAX_CONFIDENCE_RATIO {
            return Err(OracleError::PriceUncertain.into());
        }
    }
    
    // Convert to 6 decimal precision
    // Pyth prices have variable exponents, normalize to 6 decimals
    let exponent = price.expo;
    let normalized_price = normalize_price(price_abs, exponent, 6);
    
    Ok(normalized_price)
}

/// Normalize a price from one decimal precision to another
fn normalize_price(price: u64, from_exponent: i32, to_decimals: i32) -> u64 {
    let from_decimals = -from_exponent;
    let adjustment = to_decimals - from_decimals;
    
    if adjustment > 0 {
        // Need to multiply
        price * 10u64.pow(adjustment as u32)
    } else if adjustment < 0 {
        // Need to divide
        price / 10u64.pow((-adjustment) as u32)
    } else {
        price
    }
}

/// Get price for a specific market index
pub fn get_market_price(
    market_index: u8,
    oracle_account: &AccountInfo,
) -> Result<u64> {
    get_price_from_pyth(oracle_account, MAX_PRICE_AGE_SECS)
}

/// Simplified oracle price info
#[derive(Clone, Copy, Debug)]
pub struct OraclePrice {
    pub price: u64,        // Price in 6 decimals (USDC precision)
    pub confidence: u64,   // Confidence interval
    pub timestamp: i64,    // Unix timestamp
}

impl OraclePrice {
    pub fn from_account(price_account: &AccountInfo) -> Result<Self> {
        let clock = Clock::get()?;
        let current_timestamp = clock.unix_timestamp;
        
        let price_feed = SolanaPriceAccount::account_info_to_feed(price_account)
            .map_err(|_| OracleError::InvalidOracle)?;
        
        let price = price_feed
            .get_price_no_older_than(current_timestamp, MAX_PRICE_AGE_SECS)
            .ok_or(OracleError::StalePrice)?;
        
        let normalized_price = normalize_price(
            price.price as u64,
            price.expo,
            6,
        );
        
        let normalized_conf = normalize_price(
            price.conf,
            price.expo,
            6,
        );
        
        Ok(Self {
            price: normalized_price,
            confidence: normalized_conf,
            timestamp: price.publish_time,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_normalize_price() {
        // BTC at $95,000 with -8 exponent
        // 9500000000000 * 10^-8 = $95,000
        let btc_price = 9500000000000u64;
        let normalized = normalize_price(btc_price, -8, 6);
        assert_eq!(normalized, 95000000000); // $95,000 with 6 decimals
        
        // ETH at $3,500 with -8 exponent
        let eth_price = 350000000000u64;
        let normalized = normalize_price(eth_price, -8, 6);
        assert_eq!(normalized, 3500000000); // $3,500 with 6 decimals
    }
}
