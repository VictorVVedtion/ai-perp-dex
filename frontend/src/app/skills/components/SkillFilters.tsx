import { Search } from 'lucide-react';

interface SkillFiltersProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
}

// Aligned with backend categories: strategy, signal, indicator
const CATEGORIES = [
  { value: '', label: 'All' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'signal', label: 'Signal' },
  { value: 'indicator', label: 'Indicator' },
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
          className="w-full input-base input-md pl-10"
        />
      </div>

      {/* Categories */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map(({ value, label }) => (
          <button
            key={label}
            onClick={() => setSelectedCategory(value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              selectedCategory === value
                ? 'bg-rb-cyan text-layer-0 shadow-[0_0_10px_rgba(14,236,188,0.3)]'
                : 'bg-layer-1 border border-layer-3 text-rb-text-secondary hover:text-rb-text-main hover:border-layer-4'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
