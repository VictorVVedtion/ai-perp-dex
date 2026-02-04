/**
 * AI Perp DEX SDK - Basic Usage Example
 * 
 * This example demonstrates how to:
 * 1. Connect to the DEX
 * 2. Register as an agent
 * 3. Deposit collateral
 * 4. Open and close positions
 */

import { Connection, Keypair } from "@solana/web3.js";
import { AiPerpDexClient, MarketIndex, Side } from "../src";
import * as fs from "fs";

// Configuration
const RPC_URL = "https://api.devnet.solana.com";
const KEYPAIR_PATH = process.env.KEYPAIR_PATH || "~/.config/solana/id.json";

async function main() {
  console.log("🚀 AI Perp DEX SDK Example\n");

  // 1. Setup connection
  const connection = new Connection(RPC_URL, "confirmed");
  console.log(`Connected to: ${RPC_URL}`);

  // 2. Load keypair
  const keypairPath = KEYPAIR_PATH.replace("~", process.env.HOME || "");
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf-8"));
  const keypair = Keypair.fromSecretKey(Uint8Array.from(keypairData));
  console.log(`Wallet: ${keypair.publicKey.toBase58()}\n`);

  // 3. Create client
  const client = AiPerpDexClient.fromKeypair(connection, keypair);

  // 4. Try to get exchange info (read-only operation)
  try {
    const exchangeInfo = await client.getExchangeInfo();
    console.log("📊 Exchange Info:");
    console.log(`   Authority: ${exchangeInfo.authority.toBase58()}`);
    console.log(`   Fee Rate: ${exchangeInfo.feeRatePercent}%`);
    console.log(`   Total Agents: ${exchangeInfo.totalAgents}`);
    console.log(`   Total Deposits: $${exchangeInfo.totalDeposits.toLocaleString()}`);
    console.log(`   Total Open Interest: $${exchangeInfo.totalOpenInterest.toLocaleString()}\n`);
  } catch (e) {
    console.log("⚠️  Exchange not initialized yet\n");
  }

  // 5. Check if agent exists
  const agentInfo = await client.getAgentInfo(keypair.publicKey);
  
  if (agentInfo) {
    console.log("👤 Agent Info:");
    console.log(`   Name: ${agentInfo.name}`);
    console.log(`   Collateral: $${agentInfo.collateral.toLocaleString()}`);
    console.log(`   Realized PnL: $${agentInfo.realizedPnl.toLocaleString()}`);
    console.log(`   Unrealized PnL: $${agentInfo.unrealizedPnl.toLocaleString()}`);
    console.log(`   Total Trades: ${agentInfo.totalTrades}`);
    console.log(`   Win Rate: ${agentInfo.winRate.toFixed(1)}%`);
    console.log(`   Registered: ${agentInfo.registeredAt.toISOString()}\n`);

    // 6. Check positions
    const positions = await client.getAllPositions(keypair.publicKey);
    
    if (positions.length > 0) {
      console.log("📈 Open Positions:");
      for (const pos of positions) {
        console.log(`   ${pos.marketSymbol}:`);
        console.log(`      Side: ${pos.side}`);
        console.log(`      Size: ${pos.size}`);
        console.log(`      Entry: $${pos.entryPrice.toLocaleString()}`);
        console.log(`      Liq Price: $${pos.liquidationPrice.toLocaleString()}`);
        console.log(`      PnL: $${pos.unrealizedPnl.toFixed(2)} (${pos.pnlPercent.toFixed(1)}%)`);
      }
    } else {
      console.log("📈 No open positions\n");
    }
  } else {
    console.log("👤 Agent not registered yet");
    console.log("   Call client.registerAgent('YourName') to register\n");
  }

  // 7. Get markets
  const markets = await client.getAllMarkets();
  
  if (markets.length > 0) {
    console.log("🏛️  Markets:");
    for (const market of markets) {
      console.log(`   ${market.symbol}:`);
      console.log(`      Max Leverage: ${market.maxLeverage}x`);
      console.log(`      Initial Margin: ${market.initialMarginRate}%`);
      console.log(`      Long OI: $${market.longOpenInterest.toLocaleString()}`);
      console.log(`      Short OI: $${market.shortOpenInterest.toLocaleString()}`);
      console.log(`      Active: ${market.isActive}`);
    }
  } else {
    console.log("🏛️  No markets configured yet\n");
  }

  console.log("\n✅ Example complete!");
}

main().catch(console.error);
