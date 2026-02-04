# AI Perp DEX SDK

TypeScript SDK for interacting with the AI Perp DEX protocol on Solana.

## Installation

```bash
npm install @ai-perp-dex/sdk
# or
yarn add @ai-perp-dex/sdk
```

## Quick Start

```typescript
import { Connection, Keypair } from "@solana/web3.js";
import { AiPerpDexClient, MarketIndex } from "@ai-perp-dex/sdk";

// Create connection
const connection = new Connection("https://api.devnet.solana.com");

// Create client with wallet
const client = AiPerpDexClient.fromKeypair(connection, keypair);

// Or read-only client
const readOnlyClient = AiPerpDexClient.readOnly(connection);
```

## Usage

### Register as Agent

```typescript
// Register with a name
const tx = await client.registerAgent("MyAIAgent");
console.log("Registered:", tx);
```

### Deposit/Withdraw Collateral

```typescript
// Deposit 1000 USDC
await client.deposit(1000);

// Withdraw 500 USDC
await client.withdraw(500);
```

### Open Position

```typescript
// Open 0.1 BTC long at $95,000
await client.openPosition(
  MarketIndex.BTC,
  0.1,      // size (positive = long, negative = short)
  95000     // entry price
);

// Open 1 ETH short
await client.openPosition(
  MarketIndex.ETH,
  -1,       // negative = short
  3500
);
```

### Close Position

```typescript
// Close BTC position at $96,000
await client.closePosition(MarketIndex.BTC, 96000);
```

### Query Data

```typescript
// Get exchange info
const exchange = await client.getExchangeInfo();
console.log("Total deposits:", exchange.totalDeposits);

// Get agent info
const agent = await client.getAgentInfo(walletPubkey);
console.log("Win rate:", agent?.winRate);

// Get all positions
const positions = await client.getAllPositions(walletPubkey);

// Get all markets
const markets = await client.getAllMarkets();
```

### Liquidation

```typescript
// Liquidate an underwater position
await client.liquidate(targetAgentOwner, MarketIndex.BTC);
```

## Types

### MarketIndex

```typescript
enum MarketIndex {
  BTC = 0,
  ETH = 1,
  SOL = 2,
}
```

### Side

```typescript
enum Side {
  Long = "long",
  Short = "short",
}
```

### AgentInfo

```typescript
interface AgentInfo {
  address: PublicKey;
  owner: PublicKey;
  name: string;
  collateral: number;
  unrealizedPnl: number;
  realizedPnl: number;
  totalTrades: number;
  winCount: number;
  winRate: number;
  registeredAt: Date;
  isActive: boolean;
}
```

### PositionInfo

```typescript
interface PositionInfo {
  address: PublicKey;
  agent: PublicKey;
  market: MarketIndex;
  marketSymbol: string;
  side: Side;
  size: number;
  entryPrice: number;
  liquidationPrice: number;
  margin: number;
  unrealizedPnl: number;
  pnlPercent: number;
  openedAt: Date;
}
```

## PDA Derivation

```typescript
import { 
  getExchangePDA, 
  getAgentPDA, 
  getPositionPDA,
  getMarketPDA,
  PROGRAM_ID 
} from "@ai-perp-dex/sdk";

// Get PDAs
const [exchange] = getExchangePDA();
const [agent] = getAgentPDA(ownerPubkey);
const [position] = getPositionPDA(agentPubkey, MarketIndex.BTC);
const [market] = getMarketPDA(MarketIndex.BTC);
```

## Program ID

- **Devnet/Localnet**: `GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk`

## Examples

See the `examples/` directory for more detailed examples:

- `basic-usage.ts` - Read exchange and agent data
- `trading.ts` - Full trading flow example

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run examples
npx ts-node examples/basic-usage.ts
```

## License

MIT
