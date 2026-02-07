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
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-rb-text-secondary" size={18} />
        <input 
          type="text" 
          placeholder="Search skills, creators, or strategies..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-layer-1 border border-layer-3 rounded-lg pl-10 pr-4 py-2.5 text-white placeholder:text-rb-text-placeholder focus:outline-none focus:border-rb-cyan focus:ring-1 focus:ring-rb-cyan transition-all"
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
                ? 'bg-rb-cyan text-black shadow-[0_0_10px_rgba(0,212,170,0.3)]'
                : 'bg-layer-1 border border-layer-3 text-rb-text-secondary hover:text-white hover:border-layer-4'
            }`}
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
}
