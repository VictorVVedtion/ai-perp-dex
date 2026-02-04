import {
  Connection,
  PublicKey,
  TransactionInstruction,
  Transaction,
  Keypair,
  ConfirmOptions,
  sendAndConfirmTransaction,
} from "@solana/web3.js";
import {
  TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress,
} from "@solana/spl-token";
import { Program, AnchorProvider, BN, Wallet } from "@coral-xyz/anchor";

import {
  Agent,
  AgentInfo,
  Exchange,
  ExchangeInfo,
  Market,
  MarketIndex,
  MarketInfo,
  Position,
  PositionInfo,
  Side,
  TxOptions,
} from "./types";
import {
  PROGRAM_ID,
  getExchangePDA,
  getVaultPDA,
  getAgentPDA,
  getPositionPDA,
  getMarketPDA,
} from "./pdas";

// Import IDL
import idl from "../../solana-program/target/idl/ai_perp_dex.json";

const USDC_DECIMALS = 6;
const PRICE_DECIMALS = 6;

/**
 * Market symbols mapping
 */
const MARKET_SYMBOLS: Record<MarketIndex, string> = {
  [MarketIndex.BTC]: "BTC-PERP",
  [MarketIndex.ETH]: "ETH-PERP",
  [MarketIndex.SOL]: "SOL-PERP",
};

/**
 * AI Perp DEX Client
 * 
 * Main interface for interacting with the AI Perp DEX protocol.
 */
export class AiPerpDexClient {
  public readonly connection: Connection;
  public readonly program: Program;
  public readonly programId: PublicKey;
  private wallet: Wallet | null = null;

  constructor(
    connection: Connection,
    wallet?: Wallet,
    programId: PublicKey = PROGRAM_ID
  ) {
    this.connection = connection;
    this.programId = programId;
    
    if (wallet) {
      this.wallet = wallet;
      const provider = new AnchorProvider(connection, wallet, {
        commitment: "confirmed",
      });
      this.program = new Program(idl as any, provider);
    } else {
      // Read-only mode
      const dummyWallet = {
        publicKey: PublicKey.default,
        signTransaction: async (tx: Transaction) => tx,
        signAllTransactions: async (txs: Transaction[]) => txs,
      };
      const provider = new AnchorProvider(connection, dummyWallet as any, {
        commitment: "confirmed",
      });
      this.program = new Program(idl as any, provider);
    }
  }

  // ============================================================================
  // Static Factory Methods
  // ============================================================================

  /**
   * Create a client from a keypair
   */
  static fromKeypair(
    connection: Connection,
    keypair: Keypair,
    programId?: PublicKey
  ): AiPerpDexClient {
    const wallet = new Wallet(keypair);
    return new AiPerpDexClient(connection, wallet, programId);
  }

  /**
   * Create a read-only client
   */
  static readOnly(connection: Connection, programId?: PublicKey): AiPerpDexClient {
    return new AiPerpDexClient(connection, undefined, programId);
  }

  // ============================================================================
  // Admin Instructions
  // ============================================================================

  /**
   * Initialize the exchange
   */
  async initialize(
    collateralMint: PublicKey,
    feeRateBps: number,
    options?: TxOptions
  ): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [vault] = getVaultPDA(this.programId);

    const tx = await this.program.methods
      .initialize(feeRateBps)
      .accounts({
        authority: this.wallet.publicKey,
        exchange,
        collateralMint,
        vault,
      })
      .rpc(options);

    return tx;
  }

  // ============================================================================
  // Agent Instructions
  // ============================================================================

  /**
   * Register a new agent
   */
  async registerAgent(name: string, options?: TxOptions): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);

    const tx = await this.program.methods
      .registerAgent(name)
      .accounts({
        owner: this.wallet.publicKey,
        exchange,
        agent,
      })
      .rpc(options);

    return tx;
  }

  /**
   * Deposit collateral (USDC)
   */
  async deposit(amount: number, options?: TxOptions): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);
    const [vault] = getVaultPDA(this.programId);

    // Get exchange to find collateral mint
    const exchangeAccount = await this.getExchange();
    const ownerTokenAccount = await getAssociatedTokenAddress(
      exchangeAccount.collateralMint,
      this.wallet.publicKey
    );

    const amountBN = new BN(amount * 10 ** USDC_DECIMALS);

    const tx = await this.program.methods
      .deposit(amountBN)
      .accounts({
        owner: this.wallet.publicKey,
        exchange,
        agent,
        ownerTokenAccount,
        vault,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc(options);

    return tx;
  }

  /**
   * Withdraw collateral
   */
  async withdraw(amount: number, options?: TxOptions): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);
    const [vault] = getVaultPDA(this.programId);

    const exchangeAccount = await this.getExchange();
    const ownerTokenAccount = await getAssociatedTokenAddress(
      exchangeAccount.collateralMint,
      this.wallet.publicKey
    );

    const amountBN = new BN(amount * 10 ** USDC_DECIMALS);

    const tx = await this.program.methods
      .withdraw(amountBN)
      .accounts({
        owner: this.wallet.publicKey,
        exchange,
        agent,
        ownerTokenAccount,
        vault,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .rpc(options);

    return tx;
  }

  // ============================================================================
  // Trading Instructions
  // ============================================================================

  /**
   * Open a position
   */
  async openPosition(
    marketIndex: MarketIndex,
    size: number,
    entryPrice: number,
    payer?: Keypair,
    options?: TxOptions
  ): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);
    const [position] = getPositionPDA(agent, marketIndex, this.programId);
    const [market] = getMarketPDA(marketIndex, this.programId);

    // Size: positive for long, negative for short
    const sizeBN = new BN(Math.round(size * 10 ** 8)); // 8 decimals for size
    const priceBN = new BN(Math.round(entryPrice * 10 ** PRICE_DECIMALS));

    const tx = await this.program.methods
      .openPosition(marketIndex, sizeBN, priceBN)
      .accounts({
        authority: this.wallet.publicKey,
        exchange,
        agent,
        position,
        market,
        payer: payer?.publicKey || this.wallet.publicKey,
      })
      .signers(payer ? [payer] : [])
      .rpc(options);

    return tx;
  }

  /**
   * Close a position
   */
  async closePosition(
    marketIndex: MarketIndex,
    exitPrice: number,
    options?: TxOptions
  ): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);
    const [position] = getPositionPDA(agent, marketIndex, this.programId);

    const priceBN = new BN(Math.round(exitPrice * 10 ** PRICE_DECIMALS));

    const tx = await this.program.methods
      .closePosition(marketIndex, priceBN)
      .accounts({
        authority: this.wallet.publicKey,
        exchange,
        agent,
        position,
      })
      .rpc(options);

    return tx;
  }

  /**
   * Liquidate an underwater position
   */
  async liquidate(
    targetAgent: PublicKey,
    marketIndex: MarketIndex,
    options?: TxOptions
  ): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [exchange] = getExchangePDA(this.programId);
    const [agent] = getAgentPDA(targetAgent, this.programId);
    const [position] = getPositionPDA(agent, marketIndex, this.programId);
    const [liquidatorAgent] = getAgentPDA(this.wallet.publicKey, this.programId);

    const tx = await this.program.methods
      .liquidate(marketIndex)
      .accounts({
        liquidator: this.wallet.publicKey,
        exchange,
        agent,
        position,
        liquidatorAgent,
      })
      .rpc(options);

    return tx;
  }

  /**
   * Settle PnL for a position
   */
  async settlePnl(marketIndex: MarketIndex, options?: TxOptions): Promise<string> {
    if (!this.wallet) throw new Error("Wallet required for transactions");

    const [agent] = getAgentPDA(this.wallet.publicKey, this.programId);
    const [position] = getPositionPDA(agent, marketIndex, this.programId);

    const tx = await this.program.methods
      .settlePnl(marketIndex)
      .accounts({
        owner: this.wallet.publicKey,
        agent,
        position,
      })
      .rpc(options);

    return tx;
  }

  // ============================================================================
  // Read Methods
  // ============================================================================

  /**
   * Get exchange state
   */
  async getExchange(): Promise<Exchange> {
    const [exchange] = getExchangePDA(this.programId);
    return await this.program.account.exchange.fetch(exchange) as Exchange;
  }

  /**
   * Get exchange info (parsed)
   */
  async getExchangeInfo(): Promise<ExchangeInfo> {
    const [address] = getExchangePDA(this.programId);
    const exchange = await this.getExchange();

    return {
      address,
      authority: exchange.authority,
      collateralMint: exchange.collateralMint,
      vault: exchange.vault,
      feeRateBps: exchange.feeRateBps,
      feeRatePercent: exchange.feeRateBps / 100,
      totalAgents: exchange.totalAgents.toNumber(),
      totalDeposits: exchange.totalDeposits.toNumber() / 10 ** USDC_DECIMALS,
      totalOpenInterest: exchange.totalOpenInterest.toNumber() / 10 ** USDC_DECIMALS,
    };
  }

  /**
   * Get agent account
   */
  async getAgent(owner: PublicKey): Promise<Agent | null> {
    const [agent] = getAgentPDA(owner, this.programId);
    try {
      return await this.program.account.agent.fetch(agent) as Agent;
    } catch {
      return null;
    }
  }

  /**
   * Get agent info (parsed)
   */
  async getAgentInfo(owner: PublicKey): Promise<AgentInfo | null> {
    const agent = await this.getAgent(owner);
    if (!agent) return null;

    const [address] = getAgentPDA(owner, this.programId);
    const name = Buffer.from(agent.name).toString("utf-8").replace(/\0/g, "");
    const totalTrades = agent.totalTrades.toNumber();
    const winCount = agent.winCount.toNumber();

    return {
      address,
      owner: agent.owner,
      name,
      collateral: agent.collateral.toNumber() / 10 ** USDC_DECIMALS,
      unrealizedPnl: agent.unrealizedPnl.toNumber() / 10 ** USDC_DECIMALS,
      realizedPnl: agent.realizedPnl.toNumber() / 10 ** USDC_DECIMALS,
      totalTrades,
      winCount,
      winRate: totalTrades > 0 ? (winCount / totalTrades) * 100 : 0,
      registeredAt: new Date(agent.registeredAt.toNumber() * 1000),
      isActive: agent.isActive,
    };
  }

  /**
   * Get position account
   */
  async getPosition(owner: PublicKey, marketIndex: MarketIndex): Promise<Position | null> {
    const [agent] = getAgentPDA(owner, this.programId);
    const [position] = getPositionPDA(agent, marketIndex, this.programId);
    try {
      return await this.program.account.position.fetch(position) as Position;
    } catch {
      return null;
    }
  }

  /**
   * Get position info (parsed)
   */
  async getPositionInfo(
    owner: PublicKey,
    marketIndex: MarketIndex
  ): Promise<PositionInfo | null> {
    const position = await this.getPosition(owner, marketIndex);
    if (!position || position.size.isZero()) return null;

    const [agentPda] = getAgentPDA(owner, this.programId);
    const [address] = getPositionPDA(agentPda, marketIndex, this.programId);

    const size = position.size.toNumber() / 10 ** 8;
    const entryPrice = position.entryPrice.toNumber() / 10 ** PRICE_DECIMALS;
    const margin = position.margin.toNumber() / 10 ** USDC_DECIMALS;
    const unrealizedPnl = position.unrealizedPnl.toNumber() / 10 ** USDC_DECIMALS;

    return {
      address,
      agent: position.agent,
      market: marketIndex,
      marketSymbol: MARKET_SYMBOLS[marketIndex],
      side: size > 0 ? Side.Long : Side.Short,
      size: Math.abs(size),
      entryPrice,
      liquidationPrice: position.liquidationPrice.toNumber() / 10 ** PRICE_DECIMALS,
      margin,
      unrealizedPnl,
      pnlPercent: margin > 0 ? (unrealizedPnl / margin) * 100 : 0,
      openedAt: new Date(position.openedAt.toNumber() * 1000),
    };
  }

  /**
   * Get all positions for an agent
   */
  async getAllPositions(owner: PublicKey): Promise<PositionInfo[]> {
    const positions: PositionInfo[] = [];

    for (const marketIndex of [MarketIndex.BTC, MarketIndex.ETH, MarketIndex.SOL]) {
      const position = await this.getPositionInfo(owner, marketIndex);
      if (position) {
        positions.push(position);
      }
    }

    return positions;
  }

  /**
   * Get market account
   */
  async getMarket(marketIndex: MarketIndex): Promise<Market | null> {
    const [market] = getMarketPDA(marketIndex, this.programId);
    try {
      return await this.program.account.market.fetch(market) as Market;
    } catch {
      return null;
    }
  }

  /**
   * Get market info (parsed)
   */
  async getMarketInfo(marketIndex: MarketIndex): Promise<MarketInfo | null> {
    const market = await this.getMarket(marketIndex);
    if (!market) return null;

    const [address] = getMarketPDA(marketIndex, this.programId);
    const longOI = market.longOpenInterest.toNumber() / 10 ** USDC_DECIMALS;
    const shortOI = market.shortOpenInterest.toNumber() / 10 ** USDC_DECIMALS;

    return {
      address,
      index: marketIndex,
      symbol: MARKET_SYMBOLS[marketIndex],
      oracle: market.oracle,
      initialMarginRate: market.initialMarginRate / 100,
      maintenanceMarginRate: market.maintenanceMarginRate / 100,
      maxLeverage: market.maxLeverage,
      longOpenInterest: longOI,
      shortOpenInterest: shortOI,
      totalOpenInterest: longOI + shortOI,
      isActive: market.isActive,
    };
  }

  /**
   * Get all markets
   */
  async getAllMarkets(): Promise<MarketInfo[]> {
    const markets: MarketInfo[] = [];

    for (const marketIndex of [MarketIndex.BTC, MarketIndex.ETH, MarketIndex.SOL]) {
      const market = await this.getMarketInfo(marketIndex);
      if (market) {
        markets.push(market);
      }
    }

    return markets;
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Get the wallet's public key
   */
  getWalletPublicKey(): PublicKey | null {
    return this.wallet?.publicKey || null;
  }

  /**
   * Check if the client has a wallet
   */
  hasWallet(): boolean {
    return this.wallet !== null;
  }
}
