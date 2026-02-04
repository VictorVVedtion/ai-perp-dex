import { Connection, PublicKey, Keypair } from "@solana/web3.js";
import { Program, Wallet } from "@coral-xyz/anchor";
import { Agent, AgentInfo, Exchange, ExchangeInfo, Market, MarketIndex, MarketInfo, Position, PositionInfo, TxOptions } from "./types";
/**
 * AI Perp DEX Client
 *
 * Main interface for interacting with the AI Perp DEX protocol.
 */
export declare class AiPerpDexClient {
    readonly connection: Connection;
    readonly program: Program;
    readonly programId: PublicKey;
    private wallet;
    constructor(connection: Connection, wallet?: Wallet, programId?: PublicKey);
    /**
     * Create a client from a keypair
     */
    static fromKeypair(connection: Connection, keypair: Keypair, programId?: PublicKey): AiPerpDexClient;
    /**
     * Create a read-only client
     */
    static readOnly(connection: Connection, programId?: PublicKey): AiPerpDexClient;
    /**
     * Initialize the exchange
     */
    initialize(collateralMint: PublicKey, feeRateBps: number, options?: TxOptions): Promise<string>;
    /**
     * Register a new agent
     */
    registerAgent(name: string, options?: TxOptions): Promise<string>;
    /**
     * Deposit collateral (USDC)
     */
    deposit(amount: number, options?: TxOptions): Promise<string>;
    /**
     * Withdraw collateral
     */
    withdraw(amount: number, options?: TxOptions): Promise<string>;
    /**
     * Open a position
     */
    openPosition(marketIndex: MarketIndex, size: number, entryPrice: number, payer?: Keypair, options?: TxOptions): Promise<string>;
    /**
     * Close a position
     */
    closePosition(marketIndex: MarketIndex, exitPrice: number, options?: TxOptions): Promise<string>;
    /**
     * Liquidate an underwater position
     */
    liquidate(targetAgent: PublicKey, marketIndex: MarketIndex, options?: TxOptions): Promise<string>;
    /**
     * Settle PnL for a position
     */
    settlePnl(marketIndex: MarketIndex, options?: TxOptions): Promise<string>;
    /**
     * Get exchange state
     */
    getExchange(): Promise<Exchange>;
    /**
     * Get exchange info (parsed)
     */
    getExchangeInfo(): Promise<ExchangeInfo>;
    /**
     * Get agent account
     */
    getAgent(owner: PublicKey): Promise<Agent | null>;
    /**
     * Get agent info (parsed)
     */
    getAgentInfo(owner: PublicKey): Promise<AgentInfo | null>;
    /**
     * Get position account
     */
    getPosition(owner: PublicKey, marketIndex: MarketIndex): Promise<Position | null>;
    /**
     * Get position info (parsed)
     */
    getPositionInfo(owner: PublicKey, marketIndex: MarketIndex): Promise<PositionInfo | null>;
    /**
     * Get all positions for an agent
     */
    getAllPositions(owner: PublicKey): Promise<PositionInfo[]>;
    /**
     * Get market account
     */
    getMarket(marketIndex: MarketIndex): Promise<Market | null>;
    /**
     * Get market info (parsed)
     */
    getMarketInfo(marketIndex: MarketIndex): Promise<MarketInfo | null>;
    /**
     * Get all markets
     */
    getAllMarkets(): Promise<MarketInfo[]>;
    /**
     * Get the wallet's public key
     */
    getWalletPublicKey(): PublicKey | null;
    /**
     * Check if the client has a wallet
     */
    hasWallet(): boolean;
}
//# sourceMappingURL=client.d.ts.map