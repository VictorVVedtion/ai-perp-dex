"use client";

import { useConnection, useWallet } from '@solana/wallet-adapter-react';
import { PublicKey, SystemProgram } from '@solana/web3.js';
import { useMemo, useState, useCallback } from 'react';

// Program ID - Devnet deployment
export const PROGRAM_ID = new PublicKey('CWQ6LrVY3E6tHfyMzEqZjGsgpdfoJYU1S5A3qmG7LuL6');

// PDA derivation helpers
export function getExchangePDA(): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from('exchange')],
    PROGRAM_ID
  );
}

export function getAgentPDA(owner: PublicKey): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from('agent'), owner.toBuffer()],
    PROGRAM_ID
  );
}

export function getPositionPDA(agent: PublicKey, marketIndex: number): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from('position'), agent.toBuffer(), Buffer.from([marketIndex])],
    PROGRAM_ID
  );
}

export function getMarketPDA(marketIndex: number): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from('market'), Buffer.from([marketIndex])],
    PROGRAM_ID
  );
}

// Agent account structure (for decoding)
interface AgentAccount {
  owner: PublicKey;
  name: number[];
  collateral: bigint;
  unrealizedPnl: bigint;
  realizedPnl: bigint;
  totalTrades: bigint;
  winCount: bigint;
  registeredAt: bigint;
  isActive: boolean;
  bump: number;
}

// Position account structure
interface PositionAccount {
  agent: PublicKey;
  marketIndex: number;
  size: bigint;
  entryPrice: bigint;
  liquidationPrice: bigint;
  margin: bigint;
  unrealizedPnl: bigint;
  openedAt: bigint;
  updatedAt: bigint;
  bump: number;
}

// Main hook
export function useAiPerpDex() {
  const { connection } = useConnection();
  const wallet = useWallet();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get agent account (simplified - would need proper deserialization)
  const getAgent = useCallback(async (): Promise<AgentAccount | null> => {
    if (!wallet.publicKey) return null;
    
    try {
      const [agentPDA] = getAgentPDA(wallet.publicKey);
      const accountInfo = await connection.getAccountInfo(agentPDA);
      
      if (!accountInfo) return null;
      
      // Return mock data structure for now
      // In production, properly deserialize the account data
      return {
        owner: wallet.publicKey,
        name: [],
        collateral: BigInt(1000000000), // 1000 USDC mock
        unrealizedPnl: BigInt(0),
        realizedPnl: BigInt(0),
        totalTrades: BigInt(0),
        winCount: BigInt(0),
        registeredAt: BigInt(Date.now()),
        isActive: true,
        bump: 0,
      };
    } catch {
      return null;
    }
  }, [connection, wallet.publicKey]);

  // Get positions (simplified)
  const getPositions = useCallback(async (): Promise<PositionAccount[]> => {
    if (!wallet.publicKey) return [];
    
    const positions: PositionAccount[] = [];
    const [agentPDA] = getAgentPDA(wallet.publicKey);
    
    // Check positions for markets 0-2 (BTC, ETH, SOL)
    for (let i = 0; i < 3; i++) {
      try {
        const [positionPDA] = getPositionPDA(agentPDA, i);
        const accountInfo = await connection.getAccountInfo(positionPDA);
        
        if (accountInfo) {
          // Mock position data - in production, deserialize properly
          positions.push({
            agent: agentPDA,
            marketIndex: i,
            size: BigInt(0),
            entryPrice: BigInt(0),
            liquidationPrice: BigInt(0),
            margin: BigInt(0),
            unrealizedPnl: BigInt(0),
            openedAt: BigInt(0),
            updatedAt: BigInt(0),
            bump: 0,
          });
        }
      } catch {
        // Position doesn't exist
      }
    }
    
    return positions;
  }, [connection, wallet.publicKey]);

  // Register agent (would need proper transaction building)
  const registerAgent = useCallback(async (name: string) => {
    if (!wallet.publicKey || !wallet.signTransaction) {
      throw new Error('Wallet not connected');
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // In production, build and send the actual transaction
      // For now, just simulate success
      console.log('Registering agent:', name);
      await new Promise(resolve => setTimeout(resolve, 1000));
      return 'mock-tx-signature';
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [wallet.publicKey, wallet.signTransaction]);

  return {
    connected: !!wallet.publicKey,
    publicKey: wallet.publicKey,
    loading,
    error,
    registerAgent,
    getAgent,
    getPositions,
  };
}

// Market data hook
export function useMarketData() {
  const [markets] = useState([
    {
      symbol: 'BTC-PERP',
      index: 0,
      price: 97500.00,
      change24h: 2.45,
      high24h: 98100.00,
      low24h: 95800.00,
      volume24h: '2.4B',
      fundingRate: 0.0100,
    },
    {
      symbol: 'ETH-PERP',
      index: 1,
      price: 2750.00,
      change24h: -1.23,
      high24h: 2820.00,
      low24h: 2710.00,
      volume24h: '890M',
      fundingRate: 0.0085,
    },
    {
      symbol: 'SOL-PERP',
      index: 2,
      price: 195.50,
      change24h: 5.67,
      high24h: 198.00,
      low24h: 185.00,
      volume24h: '450M',
      fundingRate: 0.0120,
    },
  ]);

  return { markets };
}
