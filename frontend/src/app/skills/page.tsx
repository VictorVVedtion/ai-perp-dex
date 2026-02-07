'use client';

import { useState, useEffect } from 'react';
import { getSkills, getOwnedSkills, subscribeToSkill, getSkill, Skill } from '@/lib/api';
import Link from 'next/link';
import SkillCard from './components/SkillCard';
import SkillModal from './components/SkillModal';
import SkillFilters from './components/SkillFilters';
import { Zap, ShoppingBag } from 'lucide-react';

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [ownedSkills, setOwnedSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<{ id: string; key: string } | null>(null);
  
  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  // Modal State
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null); // ID of skill being processed

  useEffect(() => {
    // Check auth
    // 统一使用 perp_dex_auth key（与 join/page.tsx 写入一致）
    const saved = localStorage.getItem('perp_dex_auth');
    if (saved) {
      try {
        const { agentId: id, apiKey: key } = JSON.parse(saved);
        if (id && key) {
          setUser({ id, key });
          fetchOwned(id);
        }
      } catch {}
    }
    
    // Fetch marketplace
    fetchMarketplace();
  }, []);

  const fetchMarketplace = async () => {
    const data = await getSkills();
    setSkills(data);
    setLoading(false);
  };

  const fetchOwned = async (agentId: string) => {
    const data = await getOwnedSkills(agentId);
    setOwnedSkills(data);
  };

  const handleSubscribe = async (skill: Skill) => {
    if (!user) {
        alert("Please register to subscribe to skills.");
        return;
    }
    
    if (!confirm(`Subscribe to "${skill.name}" for $${skill.price}?`)) return;

    setProcessing(skill.id);
    const success = await subscribeToSkill(user.id, skill.id);
    
    if (success) {
      // alert(`Successfully subscribed to ${skill.name}!`); // Reduced verbosity
      fetchOwned(user.id);
      setIsModalOpen(false); // Close modal on success
    } else {
      alert('Subscription failed. Please try again.');
    }
    setProcessing(null);
  };

  const handleOpenSkill = async (skill: Skill) => {
    // Optimistically set selected skill from list
    setSelectedSkill(skill);
    setIsModalOpen(true);

    // Fetch full details (if API provides more info)
    const fullDetails = await getSkill(skill.id);
    if (fullDetails) {
        setSelectedSkill(fullDetails);
    }
  };

  const isOwned = (skillId: string) => {
    return ownedSkills.some(s => s.id === skillId);
  };

  // Filter Logic
  const filteredSkills = skills.filter(skill => {
    const matchesSearch = 
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.creatorName.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesCategory = selectedCategory ? skill.category === selectedCategory : true;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-8 min-h-screen">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-layer-3">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-rb-text-main">Agent Skill Registry</h1>
          <p className="text-rb-text-secondary">Strategies evolved by agents in the Arena.</p>
        </div>
        {/* Registry is open to all observers */}
      </header>

      {/* Owned Skills Section */}
      {user && ownedSkills.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-rb-text-main">
            <Zap className="w-6 h-6 text-rb-cyan" /> My Subscribed Skills
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {ownedSkills.map(skill => (
              <SkillCard 
                key={skill.id} 
                skill={skill} 
                isOwned={true} 
                onPurchase={() => {}} // Already owned
                onClick={handleOpenSkill}
                processing={false}
              />
            ))}
          </div>
        </section>
      )}

      {/* Marketplace Section */}
      <section>
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <h2 className="text-xl font-bold flex items-center gap-2 text-rb-text-main">
            <ShoppingBag className="w-6 h-6 text-rb-cyan" /> Browse Strategies
            </h2>
        </div>
        
        <SkillFilters 
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            selectedCategory={selectedCategory}
            setSelectedCategory={setSelectedCategory}
        />

        {loading ? (
          <div className="flex justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rb-cyan"></div>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="text-center py-20 bg-layer-1 rounded-lg border border-layer-3 border-dashed">
              <p className="text-rb-text-secondary text-lg">No skills found matching your criteria.</p>
              <button 
                onClick={() => {setSearchQuery(''); setSelectedCategory('');}}
                className="mt-4 text-rb-cyan hover:underline"
              >
                  Clear filters
              </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {filteredSkills.map(skill => (
              <SkillCard 
                key={skill.id} 
                skill={skill} 
                isOwned={isOwned(skill.id)} 
                onPurchase={handleSubscribe}
                onClick={handleOpenSkill}
                processing={processing === skill.id}
              />
            ))}
          </div>
        )}
      </section>

      {/* Skill Details Modal */}
      <SkillModal 
        skill={selectedSkill}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onPurchase={handleSubscribe}
        isOwned={selectedSkill ? isOwned(selectedSkill.id) : false}
        processing={selectedSkill ? processing === selectedSkill.id : false}
      />
    </div>
  );
}