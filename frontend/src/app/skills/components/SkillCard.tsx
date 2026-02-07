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
      className="bg-zinc-900/30 border border-zinc-800 hover:border-[#00D4AA]/50 hover:bg-zinc-900/50 transition-all rounded-xl p-6 flex flex-col h-full group cursor-pointer relative overflow-hidden"
      onClick={() => onClick(skill)}
    >
      <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-10 transition-opacity">
        <Zap className="w-16 h-16 text-[#00D4AA]" />
      </div>

      <div className="mb-4 relative z-10">
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="font-bold text-lg text-white group-hover:text-[#00D4AA] transition-colors">{skill.name}</h3>
            <p className="text-xs text-zinc-500">by {skill.creatorName}</p>
          </div>
          <div className="bg-[#00D4AA]/10 text-[#00D4AA] text-xs font-bold px-2 py-1 rounded border border-[#00D4AA]/20">
            {skill.category}
          </div>
        </div>
        
        <p className="text-zinc-400 text-sm line-clamp-2 h-10 mb-4">{skill.description}</p>
        
        <div className="grid grid-cols-3 gap-2 py-3 border-y border-zinc-800/50 mb-4">
          <div className="text-center">
            <div className="text-xs text-zinc-500">Win Rate</div>
            <div className="font-mono font-bold text-[#00D4AA]">{skill.stats.winRate.toFixed(1)}%</div>
          </div>
          <div className="text-center border-l border-zinc-800/50">
            <div className="text-xs text-zinc-500">Return</div>
            <div className={`font-mono font-bold ${skill.stats.totalReturn >= 0 ? 'text-[#00D4AA]' : 'text-red-500'}`}>
              {skill.stats.totalReturn > 0 ? '+' : ''}{skill.stats.totalReturn.toFixed(0)}%
            </div>
          </div>
          <div className="text-center border-l border-zinc-800/50">
            <div className="text-xs text-zinc-500">Users</div>
            <div className="font-mono font-bold text-white">{skill.subscribers}</div>
          </div>
        </div>
      </div>
      
      <div className="mt-auto flex items-center justify-between relative z-10">
        <div className="font-mono font-bold text-white text-lg">
          {formatUsd(skill.price)}
        </div>
        
        {isOwned ? (
          <span className="text-zinc-500 text-sm font-bold flex items-center gap-1 bg-zinc-800/50 px-3 py-1.5 rounded-lg">
            <Check className="w-4 h-4" /> Owned
          </span>
        ) : (
          <button 
            onClick={(e) => {
              e.stopPropagation();
              onPurchase(skill);
            }}
            disabled={processing}
            className="bg-[#00D4AA] hover:bg-[#00D4AA]/90 text-black px-4 py-2 rounded-lg font-bold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_10px_rgba(0,212,170,0.2)] hover:shadow-[0_0_15px_rgba(0,212,170,0.4)]"
          >
            {processing ? '...' : 'Subscribe'}
          </button>
        )}
      </div>
    </motion.div>
  );
}
