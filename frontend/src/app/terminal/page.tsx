'use client';

import IntentTerminal from '@/app/components/IntentTerminal';
import { MessageSquare, Zap, Shield } from 'lucide-react';
import Image from 'next/image';

export default function TerminalPage() {
  const features = [
    { icon: MessageSquare, title: 'Natural Language', desc: 'Describe your trade in plain English or Chinese. "Long BTC 10x with $1000".' },
    { icon: Zap, title: 'Instant Execution', desc: 'Proprietary intent-matching engine executes your order across multiple liquidity sources.' },
    { icon: Shield, title: 'Risk Guard', desc: 'AI automatically calculates liquidation points and suggests optimal leverage based on volatility.' },
  ];

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="flex flex-col items-center text-center space-y-4">
        <div className="w-20 h-20 rounded-lg bg-rb-cyan/10 border border-rb-cyan/20 flex items-center justify-center">
          <Image src="/logo-icon.svg" alt="Riverbit" width={40} height={40} />
        </div>
        <div>
          <h1 className="text-4xl font-bold tracking-tight">
            Intent <span className="text-rb-cyan">Terminal</span>
          </h1>
          <p className="text-rb-text-secondary mt-2 max-w-md mx-auto">
            Execute complex perpetual trades using natural language. The bridge between human intent and autonomous execution.
          </p>
        </div>
      </div>

      {/* Terminal Container */}
      <div className="max-w-4xl mx-auto">
        <div className="bg-layer-2 rounded-lg border border-layer-3 overflow-hidden shadow-2xl">
          <div className="bg-layer-3/30 px-4 py-2 border-b border-layer-3 flex items-center justify-between">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-rb-red/50"></div>
              <div className="w-3 h-3 rounded-full bg-rb-yellow/50"></div>
              <div className="w-3 h-3 rounded-full bg-rb-green/50"></div>
            </div>
            <div className="text-[10px] font-mono text-rb-text-secondary tracking-widest uppercase">
              Agent-Terminal-Session-v1.0.42
            </div>
            <div className="w-12"></div>
          </div>
          <div className="p-2">
            <IntentTerminal />
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
        {features.map((f) => (
          <div key={f.title} className="glass-card p-6 border-b-2 border-b-transparent hover:border-b-rb-cyan transition-all">
            <f.icon className="w-8 h-8 text-rb-cyan mb-4" />
            <h3 className="font-bold mb-2">{f.title}</h3>
            <p className="text-sm text-rb-text-secondary leading-relaxed">
              {f.desc}
            </p>
          </div>
        ))}
      </div>

      <div className="max-w-2xl mx-auto p-8 rounded-lg bg-rb-cyan/5 border border-rb-cyan/10 text-center">
        <h3 className="text-rb-cyan font-bold mb-2">Pro Tip</h3>
        <p className="text-sm text-rb-text-secondary italic">
          "Try saying: 'Show me my current PnL and close all positions if BTC drops below 82k' to set up autonomous safeguards."
        </p>
      </div>
    </div>
  );
}
