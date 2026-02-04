"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROGRAM_ID = void 0;
exports.getExchangePDA = getExchangePDA;
exports.getVaultPDA = getVaultPDA;
exports.getAgentPDA = getAgentPDA;
exports.getPositionPDA = getPositionPDA;
exports.getMarketPDA = getMarketPDA;
exports.getAgentPDAs = getAgentPDAs;
exports.getCorePDAs = getCorePDAs;
const web3_js_1 = require("@solana/web3.js");
exports.PROGRAM_ID = new web3_js_1.PublicKey("GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk");
// Seed constants
const EXCHANGE_SEED = Buffer.from("exchange");
const AGENT_SEED = Buffer.from("agent");
const POSITION_SEED = Buffer.from("position");
const MARKET_SEED = Buffer.from("market");
const VAULT_SEED = Buffer.from("vault");
/**
 * Derive the Exchange PDA
 */
function getExchangePDA(programId = exports.PROGRAM_ID) {
    return web3_js_1.PublicKey.findProgramAddressSync([EXCHANGE_SEED], programId);
}
/**
 * Derive the Vault PDA
 */
function getVaultPDA(programId = exports.PROGRAM_ID) {
    return web3_js_1.PublicKey.findProgramAddressSync([VAULT_SEED], programId);
}
/**
 * Derive an Agent PDA for a given owner
 */
function getAgentPDA(owner, programId = exports.PROGRAM_ID) {
    return web3_js_1.PublicKey.findProgramAddressSync([AGENT_SEED, owner.toBuffer()], programId);
}
/**
 * Derive a Position PDA for a given agent and market
 */
function getPositionPDA(agent, marketIndex, programId = exports.PROGRAM_ID) {
    return web3_js_1.PublicKey.findProgramAddressSync([POSITION_SEED, agent.toBuffer(), Buffer.from([marketIndex])], programId);
}
/**
 * Derive a Market PDA for a given index
 */
function getMarketPDA(marketIndex, programId = exports.PROGRAM_ID) {
    return web3_js_1.PublicKey.findProgramAddressSync([MARKET_SEED, Buffer.from([marketIndex])], programId);
}
/**
 * Helper to get all PDAs for an agent
 */
function getAgentPDAs(owner, programId = exports.PROGRAM_ID) {
    const [agent, agentBump] = getAgentPDA(owner, programId);
    const [btcPosition] = getPositionPDA(agent, 0, programId);
    const [ethPosition] = getPositionPDA(agent, 1, programId);
    const [solPosition] = getPositionPDA(agent, 2, programId);
    return {
        agent,
        agentBump,
        positions: {
            btc: btcPosition,
            eth: ethPosition,
            sol: solPosition,
        },
    };
}
/**
 * Helper to get all core PDAs
 */
function getCorePDAs(programId = exports.PROGRAM_ID) {
    const [exchange, exchangeBump] = getExchangePDA(programId);
    const [vault, vaultBump] = getVaultPDA(programId);
    const [btcMarket] = getMarketPDA(0, programId);
    const [ethMarket] = getMarketPDA(1, programId);
    const [solMarket] = getMarketPDA(2, programId);
    return {
        exchange,
        exchangeBump,
        vault,
        vaultBump,
        markets: {
            btc: btcMarket,
            eth: ethMarket,
            sol: solMarket,
        },
    };
}
//# sourceMappingURL=pdas.js.map