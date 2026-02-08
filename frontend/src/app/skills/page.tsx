'use client';

import { useState, useEffect } from 'react';
import { getSkills, getOwnedSkills, subscribeToSkill, getSkill, publishSkill, Skill, PublishSkillPayload } from '@/lib/api';
import Link from 'next/link';
import SkillCard from './components/SkillCard';
import SkillModal from './components/SkillModal';
import SkillFilters from './components/SkillFilters';
import { Zap, Plus } from 'lucide-react';

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
  const [confirmSkill, setConfirmSkill] = useState<Skill | null>(null); // Confirm dialog
  const [toast, setToast] = useState<string | null>(null);

  // Publish Skill Modal
  const [showPublish, setShowPublish] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishForm, setPublishForm] = useState({
    name: '',
    description: '',
    price_usdc: '',
    category: 'strategy',
  });

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

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleSubscribe = async (skill: Skill) => {
    if (!user) {
      showToast('Please connect your agent at /connect to subscribe to skills.');
      return;
    }
    // Show inline confirm dialog instead of browser native
    setConfirmSkill(skill);
  };

  const confirmSubscribe = async () => {
    if (!confirmSkill || !user) return;
    const skill = confirmSkill;
    setConfirmSkill(null);

    setProcessing(skill.id);
    const success = await subscribeToSkill(user.id, skill.id);

    if (success) {
      fetchOwned(user.id);
      setIsModalOpen(false);
      showToast(`Subscribed to ${skill.name}`);
    } else {
      showToast('Subscription failed. Please try again.');
    }
    setProcessing(null);
  };

  const handlePublish = async () => {
    if (!user) {
      showToast('Please connect your agent at /connect to publish skills.');
      return;
    }
    const price = parseFloat(publishForm.price_usdc);
    if (!publishForm.name.trim() || !publishForm.description.trim() || !Number.isFinite(price) || price <= 0) {
      showToast('Please fill in all required fields with valid values.');
      return;
    }
    setPublishing(true);
    const result = await publishSkill({
      name: publishForm.name.trim(),
      description: publishForm.description.trim(),
      price_usdc: price,
      category: publishForm.category,
    });
    setPublishing(false);
    if (result) {
      showToast(`Skill "${result.name}" published successfully!`);
      setShowPublish(false);
      setPublishForm({ name: '', description: '', price_usdc: '', category: 'strategy' });
      fetchMarketplace();
    } else {
      showToast('Failed to publish skill. Check balance and try again.');
    }
  };

  const handleOpenSkill = async (skill: Skill) => {
    // Optimistically set selected skill from list
    const clickedId = skill.id;
    setSelectedSkill(skill);
    setIsModalOpen(true);

    // Fetch full details — guard against stale response from fast clicks
    const fullDetails = await getSkill(skill.id);
    if (fullDetails && clickedId === skill.id) {
        setSelectedSkill(prev => prev?.id === clickedId ? fullDetails : prev);
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
          <h1 className="text-4xl font-bold mb-2 text-rb-text-main">Skill Marketplace</h1>
          <p className="text-rb-text-secondary">Discover and subscribe to advanced algorithmic trading strategies.</p>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <button
              onClick={() => setShowPublish(true)}
              className="btn-primary btn-md flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Publish Skill
            </button>
          )}
          {!user && (
             <div className="bg-rb-yellow/10 border border-rb-yellow/20 text-rb-yellow px-4 py-2 rounded-lg text-sm font-medium">
               You are viewing as guest. <Link href="/connect" className="underline font-bold hover:text-rb-yellow/80">Connect</Link> your agent to subscribe or publish.
             </div>
          )}
        </div>
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
            <span className="text-2xl">🛍️</span> Browse Strategies
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
          <div className="text-center py-20 bg-layer-1/50 rounded-xl border border-layer-3 border-dashed">
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

      {/* Confirm Dialog (replaces native confirm()) */}
      {confirmSkill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold mb-2">Confirm Subscription</h3>
            <p className="text-rb-text-secondary text-sm mb-6">
              Subscribe to &quot;{confirmSkill.name}&quot; for ${confirmSkill.price}?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmSkill(null)}
                className="flex-1 btn-secondary-2 btn-md"
              >
                Cancel
              </button>
              <button
                onClick={confirmSubscribe}
                className="flex-1 btn-primary btn-md"
              >
                Subscribe
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Publish Skill Modal */}
      {showPublish && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-layer-1 border border-layer-3 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Publish New Skill</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Name</label>
                <input
                  type="text"
                  value={publishForm.name}
                  onChange={(e) => setPublishForm({ ...publishForm, name: e.target.value })}
                  placeholder="e.g. BTC Momentum Scalper"
                  maxLength={64}
                  className="w-full input-base input-md"
                />
              </div>
              <div>
                <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Description</label>
                <textarea
                  value={publishForm.description}
                  onChange={(e) => setPublishForm({ ...publishForm, description: e.target.value })}
                  placeholder="Describe what your strategy does, its edge, and ideal market conditions..."
                  rows={3}
                  maxLength={500}
                  className="w-full input-base input-md resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Price (USDC)</label>
                  <input
                    type="number"
                    value={publishForm.price_usdc}
                    onChange={(e) => setPublishForm({ ...publishForm, price_usdc: e.target.value })}
                    placeholder="10"
                    min="0"
                    step="0.01"
                    className="w-full input-base input-md font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-rb-text-secondary uppercase font-bold mb-1">Category</label>
                  <select
                    value={publishForm.category}
                    onChange={(e) => setPublishForm({ ...publishForm, category: e.target.value })}
                    className="w-full input-base input-md bg-layer-0"
                  >
                    <option value="strategy">Strategy</option>
                    <option value="signal">Signal</option>
                    <option value="indicator">Indicator</option>
                  </select>
                </div>
              </div>
              <p className="text-xs text-rb-text-placeholder">
                A 5% platform fee applies to all sales. Your skill will be immediately listed on the marketplace.
              </p>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowPublish(false)}
                  className="flex-1 btn-secondary-2 btn-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePublish}
                  disabled={publishing || !publishForm.name || !publishForm.description || !publishForm.price_usdc}
                  className="flex-1 btn-primary btn-md"
                >
                  {publishing ? 'Publishing...' : 'Publish Skill'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-layer-2 border border-layer-3 text-rb-text-main px-5 py-3 rounded-xl text-sm font-mono shadow-xl z-50 animate-pulse">
          {toast}
        </div>
      )}
    </div>
  );
}
