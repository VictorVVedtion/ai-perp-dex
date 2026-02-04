use anchor_lang::prelude::*;

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
    #[msg("Invalid price data")]
    InvalidPriceData,
}

/// Maximum age for price updates (60 seconds)
pub const MAX_PRICE_AGE_SECS: i64 = 60;

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

/// Pyth price account magic number
const PYTH_MAGIC: u32 = 0xa1b2c3d4;

/// Pyth price account version
const PYTH_VERSION: u32 = 2;

/// Pyth Price structure (simplified)
/// Layout based on Pyth price account format
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct PythPrice {
    pub price: i64,
    pub conf: u64,
    pub expo: i32,
    pub publish_time: i64,
}

impl Default for PythPrice {
    fn default() -> Self {
        Self {
            price: 0,
            conf: 0,
            expo: 0,
            publish_time: 0,
        }
    }
}

/// Parse a Pyth price account
/// 
/// Pyth price account layout (V2):
/// - magic: u32 (0xa1b2c3d4)
/// - version: u32 (2)
/// - type: u32 (3 = price)
/// - size: u32
/// - price_type: u32
/// - expo: i32
/// - num_component_prices: u32
/// - num_quoters: u32
/// - last_slot: u64
/// - valid_slot: u64
/// - twap_component: i64
/// - twac_component: u64  
/// - drv1_component: i64
/// - drv2_component: i64
/// - product: Pubkey (32 bytes)
/// - next: Pubkey (32 bytes)
/// - previous_slot: u64
/// - previous_price: i64
/// - previous_conf: u64
/// - previous_publish_time: i64
/// - agg_price: i64 (offset ~208)
/// - agg_conf: u64
/// - agg_status: u32
/// - agg_corp_act_status: u32
/// - agg_publish_slot: u64
/// - agg_publish_time: i64 (offset ~248)
pub fn parse_pyth_price(data: &[u8]) -> Result<PythPrice> {
    if data.len() < 256 {
        return Err(OracleError::InvalidPriceData.into());
    }
    
    // Check magic number
    let magic = u32::from_le_bytes(data[0..4].try_into().unwrap());
    if magic != PYTH_MAGIC {
        return Err(OracleError::InvalidOracle.into());
    }
    
    // Check version
    let version = u32::from_le_bytes(data[4..8].try_into().unwrap());
    if version != PYTH_VERSION {
        return Err(OracleError::InvalidOracle.into());
    }
    
    // Get exponent (offset 20)
    let expo = i32::from_le_bytes(data[20..24].try_into().unwrap());
    
    // Get aggregate price (offset 208)
    let price = i64::from_le_bytes(data[208..216].try_into().unwrap());
    
    // Get aggregate confidence (offset 216)
    let conf = u64::from_le_bytes(data[216..224].try_into().unwrap());
    
    // Get publish time (offset 248)
    let publish_time = i64::from_le_bytes(data[248..256].try_into().unwrap());
    
    Ok(PythPrice {
        price,
        conf,
        expo,
        publish_time,
    })
}

/// Get the price from a Pyth price account
/// Returns the price in 6 decimal precision (matching USDC)
pub fn get_price_from_pyth(
    price_account: &AccountInfo,
    max_age: i64,
) -> Result<u64> {
    let clock = Clock::get()?;
    let current_timestamp = clock.unix_timestamp;
    
    // Parse price account
    let data = price_account.try_borrow_data()?;
    let price_data = parse_pyth_price(&data)?;
    
    // Check if price is fresh enough
    if current_timestamp - price_data.publish_time > max_age {
        return Err(OracleError::StalePrice.into());
    }
    
    // Check for negative price
    if price_data.price < 0 {
        return Err(OracleError::NegativePrice.into());
    }
    
    let price_abs = price_data.price as u64;
    let conf = price_data.conf;
    
    // Check confidence interval
    if conf > 0 && price_abs > 0 {
        let conf_ratio = (conf * 10000) / price_abs;
        if conf_ratio > MAX_CONFIDENCE_RATIO {
            return Err(OracleError::PriceUncertain.into());
        }
    }
    
    // Convert to 6 decimal precision
    let normalized_price = normalize_price(price_abs, price_data.expo, 6);
    
    Ok(normalized_price)
}

/// Normalize a price from one decimal precision to another
fn normalize_price(price: u64, from_exponent: i32, to_decimals: i32) -> u64 {
    let from_decimals = -from_exponent;
    let adjustment = to_decimals - from_decimals;
    
    if adjustment > 0 {
        // Need to multiply
        price.saturating_mul(10u64.pow(adjustment as u32))
    } else if adjustment < 0 {
        // Need to divide
        price / 10u64.pow((-adjustment) as u32)
    } else {
        price
    }
}

/// Get price for a specific market index
pub fn get_market_price(
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
        let data = price_account.try_borrow_data()?;
        let price_data = parse_pyth_price(&data)?;
        
        let normalized_price = normalize_price(
            price_data.price as u64,
            price_data.expo,
            6,
        );
        
        let normalized_conf = normalize_price(
            price_data.conf,
            price_data.expo,
            6,
        );
        
        Ok(Self {
            price: normalized_price,
            confidence: normalized_conf,
            timestamp: price_data.publish_time,
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
        
        // SOL at $150 with -8 exponent
        let sol_price = 15000000000u64;
        let normalized = normalize_price(sol_price, -8, 6);
        assert_eq!(normalized, 150000000); // $150 with 6 decimals
    }
}
