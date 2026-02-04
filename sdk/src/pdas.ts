import { PublicKey } from "@solana/web3.js";

export const PROGRAM_ID = new PublicKey("GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk");

// Seed constants
const EXCHANGE_SEED = Buffer.from("exchange");
const AGENT_SEED = Buffer.from("agent");
const POSITION_SEED = Buffer.from("position");
const MARKET_SEED = Buffer.from("market");
const VAULT_SEED = Buffer.from("vault");

/**
 * Derive the Exchange PDA
 */
export function getExchangePDA(programId: PublicKey = PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [EXCHANGE_SEED],
    programId
  );
}

/**
 * Derive the Vault PDA
 */
export function getVaultPDA(programId: PublicKey = PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [VAULT_SEED],
    programId
  );
}

/**
 * Derive an Agent PDA for a given owner
 */
export function getAgentPDA(
  owner: PublicKey,
  programId: PublicKey = PROGRAM_ID
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [AGENT_SEED, owner.toBuffer()],
    programId
  );
}

/**
 * Derive a Position PDA for a given agent and market
 */
export function getPositionPDA(
  agent: PublicKey,
  marketIndex: number,
  programId: PublicKey = PROGRAM_ID
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [POSITION_SEED, agent.toBuffer(), Buffer.from([marketIndex])],
    programId
  );
}

/**
 * Derive a Market PDA for a given index
 */
export function getMarketPDA(
  marketIndex: number,
  programId: PublicKey = PROGRAM_ID
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [MARKET_SEED, Buffer.from([marketIndex])],
    programId
  );
}

/**
 * Helper to get all PDAs for an agent
 */
export function getAgentPDAs(
  owner: PublicKey,
  programId: PublicKey = PROGRAM_ID
): {
  agent: PublicKey;
  agentBump: number;
  positions: { btc: PublicKey; eth: PublicKey; sol: PublicKey };
} {
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
export function getCorePDAs(programId: PublicKey = PROGRAM_ID): {
  exchange: PublicKey;
  exchangeBump: number;
  vault: PublicKey;
  vaultBump: number;
  markets: { btc: PublicKey; eth: PublicKey; sol: PublicKey };
} {
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
