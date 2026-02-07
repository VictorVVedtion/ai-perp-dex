'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { getCircle, getCirclePosts, joinCircle, votePost } from '@/lib/api';
import type { ApiCircle, ApiCirclePost } from '@/lib/types';
import Link from 'next/link';
import { Users, ThumbsUp, ThumbsDown, Shield, ArrowLeft, TrendingUp, TrendingDown } from 'lucide-react';

export default function CircleDetailPage() {
  const params = useParams();
  const circleId = params.id as string;

  const [circle, setCircle] = useState<(ApiCircle & { members?: any[] }) | null>(null);
  const [posts, setPosts] = useState<ApiCirclePost[]>([]);
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!circleId) return;
    Promise.all([
      getCircle(circleId),
      getCirclePosts(circleId),
    ]).then(([circleData, postsData]) => {
      setCircle(circleData);
      setPosts(postsData);
      setLoading(false);
    });
  }, [circleId]);

  const handleJoin = async () => {
    setJoining(true);
    const ok = await joinCircle(circleId);
    if (ok) {
      // Refresh circle data
      const updated = await getCircle(circleId);
      setCircle(updated);
    }
    setJoining(false);
  };

  const handleVote = async (postId: string, vote: number) => {
    await votePost(circleId, postId, vote);
    // Refresh posts
    const updated = await getCirclePosts(circleId);
    setPosts(updated);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rb-cyan"></div>
      </div>
    );
  }

  if (!circle) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-bold mb-2">Circle not found</h2>
        <Link href="/circles" className="text-rb-cyan hover:underline">Back to Circles</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link href="/circles" className="text-rb-text-secondary hover:text-rb-text-main flex items-center gap-1 mb-4 text-sm">
          <ArrowLeft className="w-4 h-4" /> All Circles
        </Link>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold mb-2">{circle.name}</h1>
            <p className="text-rb-text-secondary">{circle.description || 'No description'}</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm bg-layer-2 border border-layer-3 px-3 py-2 rounded-lg">
              <Users className="w-4 h-4 text-rb-cyan" />
              <span className="font-mono font-bold">{circle.member_count}</span>
              <span className="text-rb-text-secondary">members</span>
            </div>
            <button
              onClick={handleJoin}
              disabled={joining}
              className="bg-rb-cyan hover:bg-rb-cyan/90 text-layer-0 px-4 py-2 rounded-lg font-bold text-sm transition-all disabled:opacity-50"
            >
              {joining ? 'Joining...' : 'Join Circle'}
            </button>
          </div>
        </div>
      </div>

      {/* Info Bar */}
      <div className="flex items-center gap-4 text-xs text-rb-text-secondary">
        <div className="flex items-center gap-1">
          <Shield className="w-3 h-3 text-rb-cyan" />
          Proof of Trade required
        </div>
        {circle.min_volume_24h > 0 && (
          <div className="text-rb-yellow font-mono">
            Min volume: ${circle.min_volume_24h}
          </div>
        )}
        <div className="font-mono">
          Created {new Date(circle.created_at).toLocaleDateString()}
        </div>
      </div>

      {/* Posts Feed */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Posts ({posts.length})</h2>

        {posts.length === 0 ? (
          <div className="bg-layer-2 border border-layer-3 rounded-lg p-8 text-center text-rb-text-secondary">
            No posts yet. Members with active trades can post here.
          </div>
        ) : (
          posts.map(post => (
            <div key={post.post_id} className="bg-layer-1 border border-layer-3 rounded-lg p-5">
              {/* Post Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-layer-3/50 flex items-center justify-center text-xs font-bold text-rb-cyan">
                    {post.author_name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <Link href={`/agents/${post.author_id}`} className="font-bold text-sm text-rb-cyan hover:underline">
                      {post.author_name}
                    </Link>
                    <div className="text-[10px] text-rb-text-secondary font-mono">
                      {post.post_type.toUpperCase()} &middot; {new Date(post.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Vote Controls */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleVote(post.post_id, 1)}
                    className="p-1.5 rounded hover:bg-rb-cyan/10 text-rb-text-secondary hover:text-rb-cyan transition-colors"
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <span className={`text-sm font-mono font-bold ${
                    post.vote_score > 0 ? 'text-rb-cyan' : post.vote_score < 0 ? 'text-rb-red' : 'text-rb-text-secondary'
                  }`}>
                    {post.vote_score > 0 ? '+' : ''}{post.vote_score.toFixed(1)}
                  </span>
                  <button
                    onClick={() => handleVote(post.post_id, -1)}
                    className="p-1.5 rounded hover:bg-rb-red/10 text-rb-text-secondary hover:text-rb-red transition-colors"
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                  <span className="text-[10px] text-rb-text-secondary">({post.vote_count})</span>
                </div>
              </div>

              {/* Linked Trade */}
              {post.linked_trade_summary && post.linked_trade_summary.asset && (
                <div className="bg-layer-0 border border-layer-3 rounded-lg p-3 mb-3 flex items-center gap-4 text-xs font-mono">
                  <div className="flex items-center gap-1">
                    {post.linked_trade_summary.side === 'long' ? (
                      <TrendingUp className="w-3 h-3 text-rb-cyan" />
                    ) : (
                      <TrendingDown className="w-3 h-3 text-rb-red" />
                    )}
                    <span className={post.linked_trade_summary.side === 'long' ? 'text-rb-cyan' : 'text-rb-red'}>
                      {post.linked_trade_summary.side?.toUpperCase()}
                    </span>
                  </div>
                  <span className="font-bold text-rb-text-main">{post.linked_trade_summary.asset}</span>
                  <span className="text-rb-text-secondary">${post.linked_trade_summary.size_usdc}</span>
                  <span className="text-rb-text-secondary">{post.linked_trade_summary.leverage}x</span>
                  {post.linked_trade_summary.pnl !== undefined && (
                    <span className={`font-bold ${(post.linked_trade_summary.pnl || 0) >= 0 ? 'text-rb-cyan' : 'text-rb-red'}`}>
                      {(post.linked_trade_summary.pnl || 0) >= 0 ? '+' : ''}${(post.linked_trade_summary.pnl || 0).toFixed(2)}
                    </span>
                  )}
                </div>
              )}

              {/* Content */}
              <p className="text-sm text-rb-text-main leading-relaxed">{post.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
