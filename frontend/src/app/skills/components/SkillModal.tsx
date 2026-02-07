'use client';

import { Skill } from '@/lib/api';
import { formatUsd } from '@/lib/utils';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PerformanceChart from './PerformanceChart';

interface SkillModalProps {
  skill: Skill | null;
  isOpen: boolean;
  onClose: () => void;
  onPurchase: (skill: Skill) => void;
  isOwned: boolean;
  processing: boolean;
}

export default function SkillModal({ skill, isOpen, onClose, onPurchase, isOwned, processing }: SkillModalProps) {
  if (!isOpen || !skill) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={onClose}>
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-zinc-900 border border-zinc-800 w-full max-w-4xl rounded-2xl overflow-hidden shadow-2xl relative"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-start p-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-white">{skill.name}</h2>
                <span className="bg-[#00D4AA]/10 text-[#00D4AA] text-xs font-bold px-2 py-1 rounded border border-[#00D4AA]/20">
                  {skill.category}
                </span>
              </div>
              <p className="text-zinc-400">Created by <span className="text-zinc-300 font-medium">{skill.creatorName}</span></p>
            </div>
            <button 
              onClick={onClose}
              className="text-zinc-500 hover:text-white transition-colors p-2 hover:bg-zinc-800 rounded-full"
            >
              <X size={24} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3">
            {/* Main Content */}
            <div className="md:col-span-2 p-6 border-r border-zinc-800">
              <div className="h-[300px] mb-6 w-full bg-zinc-950/50 rounded-xl border border-zinc-800 p-4">
                <h4 className="text-sm font-medium text-zinc-500 mb-4">30-Day Performance Backtest</h4>
                <div className="h-[calc(100%-2rem)]">
                  <PerformanceChart skill={skill} />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-bold text-white">Strategy Description</h3>
                <p className="text-zinc-400 leading-relaxed">
                  {skill.description}
                </p>
              </div>
            </div>

            {/* Sidebar Stats */}
            <div className="p-6 bg-zinc-900/50">
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-medium text-zinc-500 mb-2">Performance Stats</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                      <div className="text-xs text-zinc-500">Win Rate</div>
                      <div className="text-xl font-mono font-bold text-[#00D4AA]">{skill.stats.winRate.toFixed(1)}%</div>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                      <div className="text-xs text-zinc-500">Total Return</div>
                      <div className={`text-xl font-mono font-bold ${skill.stats.totalReturn >= 0 ? 'text-[#00D4AA]' : 'text-red-500'}`}>
                        {skill.stats.totalReturn > 0 ? '+' : ''}{skill.stats.totalReturn.toFixed(1)}%
                      </div>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                      <div className="text-xs text-zinc-500">Sharpe Ratio</div>
                      <div className="text-xl font-mono font-bold text-white">{skill.stats.sharpeRatio.toFixed(2)}</div>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                      <div className="text-xs text-zinc-500">Subscribers</div>
                      <div className="text-xl font-mono font-bold text-white">{skill.subscribers}</div>
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-zinc-800">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-zinc-400">Price</span>
                    <span className="text-3xl font-bold text-white font-mono">{formatUsd(skill.price)}</span>
                  </div>
                  
                  {isOwned ? (
                    <button disabled className="w-full bg-zinc-800 text-zinc-400 py-3 rounded-xl font-bold cursor-not-allowed">
                      Subscribed
                    </button>
                  ) : (
                    <button 
                      onClick={() => onPurchase(skill)}
                      disabled={processing}
                      className="w-full bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black py-3 rounded-xl font-bold text-lg shadow-[0_0_20px_rgba(0,212,170,0.3)] hover:shadow-[0_0_30px_rgba(0,212,170,0.5)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {processing ? 'Processing...' : 'Subscribe Now'}
                    </button>
                  )}
                  <p className="text-center text-xs text-zinc-500 mt-3">
                    Includes lifetime updates and support.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
