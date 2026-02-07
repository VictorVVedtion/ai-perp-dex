import { Search } from 'lucide-react';

interface SkillFiltersProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
}

const CATEGORIES = [
  'All',
  'Trend-Following',
  'Mean-Reversion',
  'Momentum',
  'Arbitrage'
];

export default function SkillFilters({ searchQuery, setSearchQuery, selectedCategory, setSelectedCategory }: SkillFiltersProps) {
  return (
    <div className="flex flex-col md:flex-row gap-4 mb-8">
      {/* Search */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
        <input 
          type="text" 
          placeholder="Search skills, creators, or strategies..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-[#00D4AA] focus:ring-1 focus:ring-[#00D4AA] transition-all"
        />
      </div>

      {/* Categories */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map(category => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category === 'All' ? '' : category)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              (category === 'All' && selectedCategory === '') || category === selectedCategory
                ? 'bg-[#00D4AA] text-black shadow-[0_0_10px_rgba(0,212,170,0.3)]'
                : 'bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700'
            }`}
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
}
