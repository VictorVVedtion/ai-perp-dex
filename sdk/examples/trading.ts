/**
 * AI Perp DEX SDK - Trading Example
 * 
 * This example demonstrates trading operations:
 * 1. Register agent
 * 2. Deposit collateral
 * 3. Open a long position
 * 4. Close the position
 * 5. Withdraw profits
 */

import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import { AiPerpDexClient, MarketIndex, Side } from "../src";
import * as fs from "fs";

const RPC_URL = "https://api.devnet.solana.com";
const KEYPAIR_PATH = process.env.KEYPAIR_PATH || "~/.config/solana/id.json";

async function main() {
  console.log("🤖 AI Perp DEX Trading Example\n");

  // Setup
  const connection = new Connection(RPC_URL, "confirmed");
  const keypairPath = KEYPAIR_PATH.replace("~", process.env.HOME || "");
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf-8"));
  const keypair = Keypair.fromSecretKey(Uint8Array.from(keypairData));
  
  const client = AiPerpDexClient.fromKeypair(connection, keypair);
  const wallet = keypair.publicKey;
  
  console.log(`Wallet: ${wallet.toBase58()}\n`);

  // Check if registered
  let agent = await client.getAgentInfo(wallet);
  
  if (!agent) {
    console.log("📝 Registering agent...");
    try {
      const tx = await client.registerAgent("AI-Trader-001");
      console.log(`   TX: ${tx}\n`);
    } catch (e: any) {
      console.log(`   Error: ${e.message}\n`);
    }
  } else {
    console.log(`✅ Agent registered: ${agent.name}`);
    console.log(`   Collateral: $${agent.collateral.toFixed(2)}\n`);
  }

  // Example: Open a BTC long position
  console.log("📊 Example trade parameters:");
  console.log("   Market: BTC-PERP");
  console.log("   Side: Long");
  console.log("   Size: 0.01 BTC");
  console.log("   Entry Price: $95,000");
  console.log("   Leverage: 5x");
  console.log("   Required Margin: $190\n");

  // To actually execute trades, uncomment below:
  /*
  // Step 1: Deposit collateral (need to have USDC)
  console.log("💰 Depositing $500 USDC...");
  const depositTx = await client.deposit(500);
  console.log(`   TX: ${depositTx}\n`);

  // Step 2: Open position
  console.log("📈 Opening BTC long position...");
  const openTx = await client.openPosition(
    MarketIndex.BTC,
    0.01,    // size: 0.01 BTC
    95000,   // entry price: $95,000
  );
  console.log(`   TX: ${openTx}\n`);

  // Wait for confirmation
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Check position
  const position = await client.getPositionInfo(wallet, MarketIndex.BTC);
  if (position) {
    console.log("📊 Position opened:");
    console.log(`   Size: ${position.size} BTC`);
    console.log(`   Entry: $${position.entryPrice}`);
    console.log(`   Liquidation: $${position.liquidationPrice}\n`);
  }

  // Step 3: Close position at profit
  console.log("💹 Closing position at $96,000...");
  const closeTx = await client.closePosition(
    MarketIndex.BTC,
    96000,   // exit price: $96,000
  );
  console.log(`   TX: ${closeTx}\n`);

  // Step 4: Withdraw profits
  console.log("💸 Withdrawing $100...");
  const withdrawTx = await client.withdraw(100);
  console.log(`   TX: ${withdrawTx}\n`);
  */

  console.log("💡 To execute trades:");
  console.log("   1. Ensure exchange is initialized");
  console.log("   2. Have USDC in your wallet");
  console.log("   3. Uncomment the trading code above");
  console.log("\n✅ Example complete!");
}

main().catch(console.error);
