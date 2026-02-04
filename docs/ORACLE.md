# Oracle Integration

## Overview

AI Perp DEX integrates with Pyth Network for real-time price feeds on Solana.

## Supported Price Feeds (Devnet)

| Market | Symbol | Pyth Price Feed Address |
|--------|--------|------------------------|
| BTC | BTC-PERP | `HovQMDrbAgAYPCmHVSrezcSmkMtXSSUsLDFANExrZh2J` |
| ETH | ETH-PERP | `EdVCmQ9FSPcVe5YySXDPCRmc8aDQLKJ9xvYBMZPie1Vw` |
| SOL | SOL-PERP | `J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix` |

## Implementation Status

### Completed ✅
- Manual Pyth price account parser (`oracle.rs`)
- Price normalization to 6 decimal precision
- Staleness checks (60 second max age)
- Confidence interval validation (max 5%)
- `create_market` instruction with oracle address
- `update_position_pnl` instruction using oracle prices

### Blocked 🚧
Build is currently blocked due to a dependency conflict:
- `constant_time_eq v0.4.2` requires Rust edition 2024
- Solana SBF toolchain (platform-tools v1.51) uses Rust 1.84.1
- Rust 1.84 doesn't support edition 2024

**Fix**: Wait for Solana toolchain update (expected in platform-tools v1.52+)

## Usage

### Create Market with Oracle
```rust
// Create BTC market with Pyth oracle
create_market(
    ctx,
    0,                              // market_index
    [66, 84, 67, 45, 80, 69, 82, 80, 0, 0, 0, 0, 0, 0, 0, 0], // "BTC-PERP"
    1000,                           // 10% initial margin
    500,                            // 5% maintenance margin
    10,                             // 10x max leverage
)
```

### Update Position PnL
```rust
// Fetch latest price from Pyth and update PnL
update_position_pnl(ctx)
```

## Oracle Module (`oracle.rs`)

```rust
// Get price from Pyth account
let price = get_price_from_pyth(&oracle_account, MAX_PRICE_AGE_SECS)?;

// Get full price info
let oracle_price = OraclePrice::from_account(&oracle_account)?;
println!("Price: {}, Confidence: {}", oracle_price.price, oracle_price.confidence);
```

## Price Format

- Prices are normalized to 6 decimal places (USDC precision)
- BTC at $95,000 = `95000000000` (95000 * 10^6)
- ETH at $3,500 = `3500000000` (3500 * 10^6)

## Security Considerations

1. **Staleness**: Prices older than 60 seconds are rejected
2. **Confidence**: Prices with >5% confidence interval are rejected
3. **Negative Prices**: Rejected as invalid
4. **Oracle Validation**: Market's oracle address must match price account

## Mainnet Price Feeds

For mainnet deployment, update the oracle addresses:

| Market | Mainnet Price Feed |
|--------|-------------------|
| BTC/USD | `GVXRSBjFk6e6J3NbVPXohDJetcTjaeeuykUpbQF8UoMU` |
| ETH/USD | `JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB` |
| SOL/USD | `H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG` |

## References

- [Pyth Network Docs](https://docs.pyth.network/price-feeds/solana)
- [Pyth Price Feed IDs](https://pyth.network/developers/price-feed-ids)
