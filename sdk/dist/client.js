"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AiPerpDexClient = void 0;
const web3_js_1 = require("@solana/web3.js");
const spl_token_1 = require("@solana/spl-token");
const anchor_1 = require("@coral-xyz/anchor");
const types_1 = require("./types");
const pdas_1 = require("./pdas");
// Import IDL
const idl_json_1 = __importDefault(require("./idl.json"));
const USDC_DECIMALS = 6;
const PRICE_DECIMALS = 6;
/**
 * Market symbols mapping
 */
const MARKET_SYMBOLS = {
    [types_1.MarketIndex.BTC]: "BTC-PERP",
    [types_1.MarketIndex.ETH]: "ETH-PERP",
    [types_1.MarketIndex.SOL]: "SOL-PERP",
};
/**
 * AI Perp DEX Client
 *
 * Main interface for interacting with the AI Perp DEX protocol.
 */
class AiPerpDexClient {
    constructor(connection, wallet, programId = pdas_1.PROGRAM_ID) {
        this.wallet = null;
        this.connection = connection;
        this.programId = programId;
        if (wallet) {
            this.wallet = wallet;
            const provider = new anchor_1.AnchorProvider(connection, wallet, {
                commitment: "confirmed",
            });
            this.program = new anchor_1.Program(idl_json_1.default, provider);
        }
        else {
            // Read-only mode
            const dummyWallet = {
                publicKey: web3_js_1.PublicKey.default,
                signTransaction: async (tx) => tx,
                signAllTransactions: async (txs) => txs,
            };
            const provider = new anchor_1.AnchorProvider(connection, dummyWallet, {
                commitment: "confirmed",
            });
            this.program = new anchor_1.Program(idl_json_1.default, provider);
        }
    }
    // ============================================================================
    // Static Factory Methods
    // ============================================================================
    /**
     * Create a client from a keypair
     */
    static fromKeypair(connection, keypair, programId) {
        const wallet = new anchor_1.Wallet(keypair);
        return new AiPerpDexClient(connection, wallet, programId);
    }
    /**
     * Create a read-only client
     */
    static readOnly(connection, programId) {
        return new AiPerpDexClient(connection, undefined, programId);
    }
    // ============================================================================
    // Admin Instructions
    // ============================================================================
    /**
     * Initialize the exchange
     */
    async initialize(collateralMint, feeRateBps, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [vault] = (0, pdas_1.getVaultPDA)(this.programId);
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
    async registerAgent(name, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
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
    async deposit(amount, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
        const [vault] = (0, pdas_1.getVaultPDA)(this.programId);
        // Get exchange to find collateral mint
        const exchangeAccount = await this.getExchange();
        const ownerTokenAccount = await (0, spl_token_1.getAssociatedTokenAddress)(exchangeAccount.collateralMint, this.wallet.publicKey);
        const amountBN = new anchor_1.BN(amount * 10 ** USDC_DECIMALS);
        const tx = await this.program.methods
            .deposit(amountBN)
            .accounts({
            owner: this.wallet.publicKey,
            exchange,
            agent,
            ownerTokenAccount,
            vault,
            tokenProgram: spl_token_1.TOKEN_PROGRAM_ID,
        })
            .rpc(options);
        return tx;
    }
    /**
     * Withdraw collateral
     */
    async withdraw(amount, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
        const [vault] = (0, pdas_1.getVaultPDA)(this.programId);
        const exchangeAccount = await this.getExchange();
        const ownerTokenAccount = await (0, spl_token_1.getAssociatedTokenAddress)(exchangeAccount.collateralMint, this.wallet.publicKey);
        const amountBN = new anchor_1.BN(amount * 10 ** USDC_DECIMALS);
        const tx = await this.program.methods
            .withdraw(amountBN)
            .accounts({
            owner: this.wallet.publicKey,
            exchange,
            agent,
            ownerTokenAccount,
            vault,
            tokenProgram: spl_token_1.TOKEN_PROGRAM_ID,
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
    async openPosition(marketIndex, size, entryPrice, payer, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
        const [position] = (0, pdas_1.getPositionPDA)(agent, marketIndex, this.programId);
        const [market] = (0, pdas_1.getMarketPDA)(marketIndex, this.programId);
        // Size: positive for long, negative for short
        const sizeBN = new anchor_1.BN(Math.round(size * 10 ** 8)); // 8 decimals for size
        const priceBN = new anchor_1.BN(Math.round(entryPrice * 10 ** PRICE_DECIMALS));
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
    async closePosition(marketIndex, exitPrice, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
        const [position] = (0, pdas_1.getPositionPDA)(agent, marketIndex, this.programId);
        const priceBN = new anchor_1.BN(Math.round(exitPrice * 10 ** PRICE_DECIMALS));
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
    async liquidate(targetAgent, marketIndex, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        const [agent] = (0, pdas_1.getAgentPDA)(targetAgent, this.programId);
        const [position] = (0, pdas_1.getPositionPDA)(agent, marketIndex, this.programId);
        const [liquidatorAgent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
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
    async settlePnl(marketIndex, options) {
        if (!this.wallet)
            throw new Error("Wallet required for transactions");
        const [agent] = (0, pdas_1.getAgentPDA)(this.wallet.publicKey, this.programId);
        const [position] = (0, pdas_1.getPositionPDA)(agent, marketIndex, this.programId);
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
    async getExchange() {
        const [exchange] = (0, pdas_1.getExchangePDA)(this.programId);
        return await this.program.account.exchange.fetch(exchange);
    }
    /**
     * Get exchange info (parsed)
     */
    async getExchangeInfo() {
        const [address] = (0, pdas_1.getExchangePDA)(this.programId);
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
    async getAgent(owner) {
        const [agent] = (0, pdas_1.getAgentPDA)(owner, this.programId);
        try {
            return await this.program.account.agent.fetch(agent);
        }
        catch {
            return null;
        }
    }
    /**
     * Get agent info (parsed)
     */
    async getAgentInfo(owner) {
        const agent = await this.getAgent(owner);
        if (!agent)
            return null;
        const [address] = (0, pdas_1.getAgentPDA)(owner, this.programId);
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
    async getPosition(owner, marketIndex) {
        const [agent] = (0, pdas_1.getAgentPDA)(owner, this.programId);
        const [position] = (0, pdas_1.getPositionPDA)(agent, marketIndex, this.programId);
        try {
            return await this.program.account.position.fetch(position);
        }
        catch {
            return null;
        }
    }
    /**
     * Get position info (parsed)
     */
    async getPositionInfo(owner, marketIndex) {
        const position = await this.getPosition(owner, marketIndex);
        if (!position || position.size.isZero())
            return null;
        const [agentPda] = (0, pdas_1.getAgentPDA)(owner, this.programId);
        const [address] = (0, pdas_1.getPositionPDA)(agentPda, marketIndex, this.programId);
        const size = position.size.toNumber() / 10 ** 8;
        const entryPrice = position.entryPrice.toNumber() / 10 ** PRICE_DECIMALS;
        const margin = position.margin.toNumber() / 10 ** USDC_DECIMALS;
        const unrealizedPnl = position.unrealizedPnl.toNumber() / 10 ** USDC_DECIMALS;
        return {
            address,
            agent: position.agent,
            market: marketIndex,
            marketSymbol: MARKET_SYMBOLS[marketIndex],
            side: size > 0 ? types_1.Side.Long : types_1.Side.Short,
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
    async getAllPositions(owner) {
        const positions = [];
        for (const marketIndex of [types_1.MarketIndex.BTC, types_1.MarketIndex.ETH, types_1.MarketIndex.SOL]) {
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
    async getMarket(marketIndex) {
        const [market] = (0, pdas_1.getMarketPDA)(marketIndex, this.programId);
        try {
            return await this.program.account.market.fetch(market);
        }
        catch {
            return null;
        }
    }
    /**
     * Get market info (parsed)
     */
    async getMarketInfo(marketIndex) {
        const market = await this.getMarket(marketIndex);
        if (!market)
            return null;
        const [address] = (0, pdas_1.getMarketPDA)(marketIndex, this.programId);
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
    async getAllMarkets() {
        const markets = [];
        for (const marketIndex of [types_1.MarketIndex.BTC, types_1.MarketIndex.ETH, types_1.MarketIndex.SOL]) {
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
    getWalletPublicKey() {
        return this.wallet?.publicKey || null;
    }
    /**
     * Check if the client has a wallet
     */
    hasWallet() {
        return this.wallet !== null;
    }
}
exports.AiPerpDexClient = AiPerpDexClient;
//# sourceMappingURL=client.js.map