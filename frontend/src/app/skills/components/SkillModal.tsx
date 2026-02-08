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
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-layer-1 border border-layer-3 w-full max-w-4xl rounded-2xl overflow-hidden shadow-2xl relative"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-start p-6 border-b border-layer-3">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-rb-text-main">{skill.name}</h2>
                <span className="bg-rb-cyan/10 text-rb-cyan text-xs font-bold px-2 py-1 rounded border border-rb-cyan/20">
                  {skill.category}
                </span>
              </div>
              <p className="text-rb-text-secondary">Created by <span className="text-rb-text-main font-medium">{skill.creatorName}</span></p>
            </div>
            <button 
              onClick={onClose}
              className="text-rb-text-secondary hover:text-rb-text-main transition-colors p-2 hover:bg-layer-2 rounded-full"
            >
              <X size={24} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3">
            {/* Main Content */}
            <div className="md:col-span-2 p-6 border-r border-layer-3">
              <div className="h-[300px] mb-6 w-full bg-layer-0/70 rounded-xl border border-layer-3 p-4">
                <h4 className="text-sm font-medium text-rb-text-secondary mb-4">30-Day Performance Backtest</h4>
                <div className="h-[calc(100%-2rem)]">
                  <PerformanceChart skill={skill} />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-bold text-rb-text-main">Strategy Description</h3>
                <p className="text-rb-text-secondary leading-relaxed">
                  {skill.description}
                </p>
              </div>
            </div>

            {/* Sidebar Stats */}
            <div className="p-6 bg-layer-1/50">
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-medium text-rb-text-secondary mb-2">Performance Stats</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-layer-0 p-3 rounded-lg border border-layer-3">
                      <div className="text-xs text-rb-text-secondary">Win Rate</div>
                      <div className="text-xl font-mono font-bold text-rb-cyan">{skill.stats.winRate.toFixed(1)}%</div>
                    </div>
                    <div className="bg-layer-0 p-3 rounded-lg border border-layer-3">
                      <div className="text-xs text-rb-text-secondary">Total Return</div>
                      <div className={`text-xl font-mono font-bold ${skill.stats.totalReturn >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                        {skill.stats.totalReturn > 0 ? '+' : ''}{skill.stats.totalReturn.toFixed(1)}%
                      </div>
                    </div>
                    <div className="bg-layer-0 p-3 rounded-lg border border-layer-3">
                      <div className="text-xs text-rb-text-secondary">Sharpe Ratio</div>
                      <div className="text-xl font-mono font-bold text-rb-text-main">{skill.stats.sharpeRatio.toFixed(2)}</div>
                    </div>
                    <div className="bg-layer-0 p-3 rounded-lg border border-layer-3">
                      <div className="text-xs text-rb-text-secondary">Subscribers</div>
                      <div className="text-xl font-mono font-bold text-rb-text-main">{skill.subscribers}</div>
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-layer-3">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-rb-text-secondary">Price</span>
                    <span className="text-3xl font-bold text-rb-text-main font-mono">{formatUsd(skill.price)}</span>
                  </div>
                  
                  {isOwned ? (
                    <button disabled className="w-full bg-layer-2 text-rb-text-secondary py-3 rounded-xl font-bold cursor-not-allowed border border-layer-3">
                      Subscribed
                    </button>
                  ) : (
                    <button 
                      onClick={() => onPurchase(skill)}
                      disabled={processing}
                      className="w-full btn-primary py-3 rounded-xl text-lg shadow-[0_0_20px_rgba(14,236,188,0.3)] hover:shadow-[0_0_30px_rgba(14,236,188,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {processing ? 'Processing...' : 'Subscribe Now'}
                    </button>
                  )}
                  <p className="text-center text-xs text-rb-text-secondary mt-3">
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
