import { PublicKey } from "@solana/web3.js";
export declare const PROGRAM_ID: PublicKey;
/**
 * Derive the Exchange PDA
 */
export declare function getExchangePDA(programId?: PublicKey): [PublicKey, number];
/**
 * Derive the Vault PDA
 */
export declare function getVaultPDA(programId?: PublicKey): [PublicKey, number];
/**
 * Derive an Agent PDA for a given owner
 */
export declare function getAgentPDA(owner: PublicKey, programId?: PublicKey): [PublicKey, number];
/**
 * Derive a Position PDA for a given agent and market
 */
export declare function getPositionPDA(agent: PublicKey, marketIndex: number, programId?: PublicKey): [PublicKey, number];
/**
 * Derive a Market PDA for a given index
 */
export declare function getMarketPDA(marketIndex: number, programId?: PublicKey): [PublicKey, number];
/**
 * Helper to get all PDAs for an agent
 */
export declare function getAgentPDAs(owner: PublicKey, programId?: PublicKey): {
    agent: PublicKey;
    agentBump: number;
    positions: {
        btc: PublicKey;
        eth: PublicKey;
        sol: PublicKey;
    };
};
/**
 * Helper to get all core PDAs
 */
export declare function getCorePDAs(programId?: PublicKey): {
    exchange: PublicKey;
    exchangeBump: number;
    vault: PublicKey;
    vaultBump: number;
    markets: {
        btc: PublicKey;
        eth: PublicKey;
        sol: PublicKey;
    };
};
//# sourceMappingURL=pdas.d.ts.map