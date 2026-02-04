# AI Perp DEX - Devnet Deployment Guide

## Prerequisites

1. **Solana CLI** installed (`~/.local/share/solana/install/active_release/bin/solana`)
2. **Anchor CLI** installed (`~/.cargo/bin/anchor`)
3. Wallet with SOL for deployment (~3 SOL)

## Configuration

### 1. Set Solana CLI to Devnet
```bash
export PATH="$HOME/.local/share/solana/install/active_release/bin:$HOME/.cargo/bin:$PATH"
solana config set --url devnet
```

### 2. Create/Check Wallet
```bash
# Create new wallet if needed
solana-keygen new -o ~/.config/solana/id.json

# Check address
solana address
```

### 3. Fund Wallet
```bash
# Request airdrop (may be rate limited)
solana airdrop 2 --url devnet

# Alternative: Use web faucets
# - https://faucet.solana.com/
# - https://solfaucet.com/
```

## Deployment

### Build Program
```bash
cd solana-program
anchor build
```

### Deploy to Devnet
```bash
anchor deploy --provider.cluster devnet
```

### Verify Deployment
```bash
solana program show GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk --url devnet
```

## Program Information

- **Program ID**: `GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk`
- **Upgrade Authority**: Deployer wallet
- **Binary Size**: ~364 KB

## IDL Location

After deployment, the IDL is available at:
- Local: `target/idl/ai_perp_dex.json`
- On-chain: Automatically uploaded with `anchor deploy`

## Testnet vs Devnet

| Network | RPC URL | Use Case |
|---------|---------|----------|
| Devnet | `https://api.devnet.solana.com` | Development & Testing |
| Testnet | `https://api.testnet.solana.com` | Stress Testing |
| Mainnet | `https://api.mainnet-beta.solana.com` | Production |

## Troubleshooting

### Rate Limited Airdrop
Wait 24 hours or use a web faucet:
- https://faucet.solana.com/
- https://solfaucet.com/

### Insufficient Funds
Program deployment requires ~2.6 SOL for rent-exempt account.

### Build Errors
```bash
# Clean build
anchor clean
anchor build
```
