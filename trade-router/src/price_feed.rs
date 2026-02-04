//! Background price feed - keeps prices up to date

use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;
use tracing::{info, warn};

use crate::state::AppState;
use crate::types::Market;

const COINGECKO_URL: &str = "https://api.coingecko.com/api/v3/simple/price";

/// Start background price updater
pub async fn start_price_feed(state: Arc<AppState>, interval_secs: u64) {
    info!("📈 Price feed starting (interval: {}s)", interval_secs);
    
    let mut ticker = interval(Duration::from_secs(interval_secs));
    let client = reqwest::Client::new();
    
    loop {
        ticker.tick().await;
        
        match fetch_prices(&client).await {
            Ok(prices) => {
                // Update state
                if let Some(btc) = prices.get("bitcoin") {
                    state.prices.insert(Market::BtcPerp, *btc);
                }
                if let Some(eth) = prices.get("ethereum") {
                    state.prices.insert(Market::EthPerp, *eth);
                }
                if let Some(sol) = prices.get("solana") {
                    state.prices.insert(Market::SolPerp, *sol);
                }
                
                info!("📈 Prices updated: BTC=${:.0}, ETH=${:.0}, SOL=${:.0}",
                      prices.get("bitcoin").unwrap_or(&0.0),
                      prices.get("ethereum").unwrap_or(&0.0),
                      prices.get("solana").unwrap_or(&0.0));
            }
            Err(e) => {
                warn!("Price fetch failed: {}", e);
            }
        }
    }
}

async fn fetch_prices(client: &reqwest::Client) -> Result<std::collections::HashMap<String, f64>, String> {
    let resp = client
        .get(COINGECKO_URL)
        .query(&[("ids", "bitcoin,ethereum,solana"), ("vs_currencies", "usd")])
        .header("User-Agent", "AI-Perp-DEX/1.0")
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let text = resp.text().await.map_err(|e| format!("Read failed: {}", e))?;
    let data: serde_json::Value = serde_json::from_str(&text)
        .map_err(|e| format!("Parse failed: {} - body: {}", e, &text[..100.min(text.len())]))?;
    
    let mut prices = std::collections::HashMap::new();
    
    // Parse with better error handling
    tracing::debug!("API response: {:?}", data);
    
    for (coin, _) in [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL")] {
        if let Some(price) = data.get(coin).and_then(|v| v.get("usd")).and_then(|v| v.as_f64()) {
            prices.insert(coin.to_string(), price);
            tracing::debug!("Parsed {} = ${}", coin, price);
        } else {
            tracing::warn!("Missing price for {} in data: {:?}", coin, data.get(coin));
        }
    }
    
    tracing::info!("Fetched {} prices", prices.len());
    Ok(prices)
}
