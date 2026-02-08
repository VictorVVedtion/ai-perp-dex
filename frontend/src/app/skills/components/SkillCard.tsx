import { Skill } from '@/lib/api';
import { formatUsd } from '@/lib/utils';
import { motion } from 'framer-motion';
import { Zap, Check } from 'lucide-react';

interface SkillCardProps {
  skill: Skill;
  isOwned: boolean;
  onPurchase: (skill: Skill) => void;
  onClick: (skill: Skill) => void;
  processing: boolean;
}

export default function SkillCard({ skill, isOwned, onPurchase, onClick, processing }: SkillCardProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-layer-1/50 border border-layer-3 hover:border-rb-cyan/40 hover:bg-layer-2/60 transition-all rounded-xl p-6 flex flex-col h-full group cursor-pointer relative overflow-hidden"
      onClick={() => onClick(skill)}
    >
      <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-10 transition-opacity">
        <Zap className="w-16 h-16 text-rb-cyan" />
      </div>

      <div className="mb-4 relative z-10">
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="font-bold text-lg text-rb-text-main group-hover:text-rb-cyan transition-colors">{skill.name}</h3>
            <p className="text-xs text-rb-text-secondary">by {skill.creatorName}</p>
          </div>
          <div className="bg-rb-cyan/10 text-rb-cyan text-xs font-bold px-2 py-1 rounded border border-rb-cyan/20">
            {skill.category}
          </div>
        </div>
        
        <p className="text-rb-text-secondary text-sm line-clamp-2 h-10 mb-4">{skill.description}</p>
        
        <div className="grid grid-cols-3 gap-2 py-3 border-y border-layer-3/60 mb-4">
          <div className="text-center">
            <div className="text-xs text-rb-text-secondary">Win Rate</div>
            <div className="font-mono font-bold text-rb-cyan">{skill.stats.winRate.toFixed(1)}%</div>
          </div>
          <div className="text-center border-l border-layer-3/60">
            <div className="text-xs text-rb-text-secondary">Return</div>
            <div className={`font-mono font-bold ${skill.stats.totalReturn >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
              {skill.stats.totalReturn > 0 ? '+' : ''}{skill.stats.totalReturn.toFixed(0)}%
            </div>
          </div>
          <div className="text-center border-l border-layer-3/60">
            <div className="text-xs text-rb-text-secondary">Users</div>
            <div className="font-mono font-bold text-rb-text-main">{skill.subscribers}</div>
          </div>
        </div>
      </div>
      
      <div className="mt-auto flex items-center justify-between relative z-10">
        <div className="font-mono font-bold text-rb-text-main text-lg">
          {formatUsd(skill.price)}
        </div>
        
        {isOwned ? (
          <span className="text-rb-text-secondary text-sm font-bold flex items-center gap-1 bg-layer-2/80 px-3 py-1.5 rounded-lg border border-layer-3">
            <Check className="w-4 h-4" /> Owned
          </span>
        ) : (
          <button 
            onClick={(e) => {
              e.stopPropagation();
              onPurchase(skill);
            }}
            disabled={processing}
            className="btn-primary btn-md shadow-[0_0_10px_rgba(14,236,188,0.2)] hover:shadow-[0_0_15px_rgba(14,236,188,0.35)]"
          >
            {processing ? '...' : 'Subscribe'}
          </button>
        )}
      </div>
    </motion.div>
  );
}
