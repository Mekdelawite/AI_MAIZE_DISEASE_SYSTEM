import React, { useCallback, useEffect, useState } from 'react';
import { MessageSquare, Plus, RefreshCw, Search, Send, X } from 'lucide-react';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { discussionService } from '../services/discussionService';
import { DiscussionPost } from '../types/api';
import { formatDateTime } from '../utils/media';

export const DiscussionPage: React.FC = () => {
  const { t, notify } = useApp();
  const { effectiveRole } = useAuth();

  const [posts, setPosts] = useState<DiscussionPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [postTypeFilter, setPostTypeFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Create Post Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState<'question' | 'advisory' | 'announcement' | 'alert'>('question');
  const [newPriority, setNewPriority] = useState<'low' | 'normal' | 'medium' | 'high' | 'urgent'>('normal');
  const [creating, setCreating] = useState(false);

  // Detail & Reply Drawer
  const [selectedPost, setSelectedPost] = useState<DiscussionPost | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [replying, setReplying] = useState(false);

  const canPostAdvisoryTypes = effectiveRole === 'extension_agent' || effectiveRole === 'admin';

  const loadPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await discussionService.getPosts({
        search: search.trim() || undefined,
        post_type: postTypeFilter || undefined,
        priority: priorityFilter || undefined,
        page,
      });
      setPosts(res.posts);
      setTotalPages(Math.max(1, res.pages));
    } catch (err: any) {
      setError(err?.message || 'Unable to load community discussion posts from server.');
    } finally {
      setLoading(false);
    }
  }, [search, postTypeFilter, priorityFilter, page]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const handleOpenPostDetail = async (postId: string | number) => {
    setDetailLoading(true);
    try {
      const detail = await discussionService.getPostDetail(postId);
      setSelectedPost(detail);
    } catch (err: any) {
      notify(err?.message || 'Unable to load post details.', 'error');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreatePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) {
      notify('Title and content are required.', 'warning');
      return;
    }

    setCreating(true);
    try {
      await discussionService.createPost({
        title: newTitle.trim(),
        content: newContent.trim(),
        post_type: canPostAdvisoryTypes ? newType : 'question',
        priority: newPriority,
      });
      notify('Post published to the community board.', 'success');
      setNewTitle('');
      setNewContent('');
      setCreateOpen(false);
      loadPosts();
    } catch (err: any) {
      notify(err?.message || 'Failed to create discussion post.', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPost || !replyContent.trim()) return;
    setReplying(true);
    try {
      await discussionService.createReply(selectedPost.id, replyContent.trim());
      setReplyContent('');
      notify('Reply posted.', 'success');
      const updated = await discussionService.getPostDetail(selectedPost.id);
      setSelectedPost(updated);
      loadPosts();
    } catch (err: any) {
      notify(err?.message || 'Failed to submit reply.', 'error');
    } finally {
      setReplying(false);
    }
  };

  return (
    <AppShell
      title={t('navDiscussion')}
      subtitle="Collaborate with smallholder farmers and woreda extension agents on maize disease symptoms and agronomic practices."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadPosts}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-700 dark:text-stone-200 border border-stone-300 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t('refresh')}</span>
          </button>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg cursor-pointer whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{canPostAdvisoryTypes ? 'New Post / Advisory' : 'Ask a Question'}</span>
          </button>
        </div>
      }
    >
      {/* Search and Filter Bar */}
      <div className="mb-6 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-4 flex flex-wrap items-center justify-between gap-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            loadPosts();
          }}
          className="flex items-center gap-2 flex-1 min-w-[240px]"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search questions, symptoms, or woreda advisories..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-800 rounded-lg cursor-pointer"
          >
            {t('search')}
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={postTypeFilter}
            onChange={(e) => {
              setPostTypeFilter(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by post type"
            className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          >
            <option value="">All Post Types</option>
            <option value="question">Farmer Questions</option>
            <option value="advisory">Extension Advisories</option>
            <option value="announcement">Announcements</option>
            <option value="alert">Outbreak Alerts</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by priority"
            className="px-3 py-1.5 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
          >
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className={selectedPost ? 'lg:col-span-7 space-y-4' : 'lg:col-span-12 space-y-4'}>
          {loading ? (
            <LoadingSkeleton rows={4} />
          ) : error ? (
            <ErrorState title="Could not load discussion feed" message={error} onRetry={loadPosts} />
          ) : posts.length === 0 ? (
            <EmptyState
              title="No community discussion posts found"
              description="Start a new conversation by posting a field question or extension update."
              actionLabel={canPostAdvisoryTypes ? 'Create Post' : 'Ask a Question'}
              onAction={() => setCreateOpen(true)}
            />
          ) : (
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] divide-y divide-stone-200 dark:divide-stone-800">
              {posts.map((post) => (
                <div
                  key={String(post.id)}
                  onClick={() => handleOpenPostDetail(post.id)}
                  className="p-5 hover:bg-stone-50/80 dark:hover:bg-stone-800/40 transition-colors cursor-pointer"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
                    <span className="font-semibold text-emerald-800 dark:text-emerald-400 uppercase tracking-wider">
                      {post.post_type || 'question'}
                    </span>
                    {post.priority && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span>Priority: {post.priority}</span>
                      </>
                    )}
                    <span aria-hidden="true">·</span>
                    <span>{post.author_name || 'Member'}</span>
                    {post.region && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span>
                          {post.region}
                          {post.woreda ? ` / ${post.woreda}` : ''}
                        </span>
                      </>
                    )}
                    <span aria-hidden="true">·</span>
                    <span className="font-mono tabular-nums">{formatDateTime(post.created_at)}</span>
                  </div>

                  <h3 className="mt-1.5 text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                    {post.title}
                  </h3>
                  <p className="mt-1 text-sm text-stone-600 dark:text-stone-400 line-clamp-2 leading-relaxed">
                    {post.content}
                  </p>
                  <div className="mt-3 flex items-center gap-2 text-xs text-stone-500">
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span className="tabular-nums">
                      {post.replies_count ?? post.replies?.length ?? 0} replies
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2 text-xs">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-stone-300 dark:border-stone-700 disabled:opacity-40 cursor-pointer"
              >
                Previous
              </button>
              <span className="font-mono tabular-nums">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-lg border border-stone-300 dark:border-stone-700 disabled:opacity-40 cursor-pointer"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Post Detail & Replies Column */}
        {selectedPost && (
          <div className="lg:col-span-5">
            <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sticky top-20 space-y-5">
              <div className="flex items-start justify-between gap-3 border-b border-stone-200 dark:border-stone-800 pb-4">
                <div>
                  <div className="text-xs text-stone-500">
                    {selectedPost.post_type || 'question'} · {selectedPost.author_name || 'Member'} ·{' '}
                    <span className="font-mono">{formatDateTime(selectedPost.created_at)}</span>
                  </div>
                  <h3 className="mt-1 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                    {selectedPost.title}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedPost(null)}
                  className="text-stone-400 hover:text-stone-700 cursor-pointer"
                  aria-label="Close post details"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {detailLoading ? (
                <LoadingSkeleton rows={2} />
              ) : (
                <>
                  <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-line leading-relaxed">
                    {selectedPost.content}
                  </p>

                  <div className="pt-4 border-t border-stone-200 dark:border-stone-800 space-y-3">
                    <h4 className="text-xs font-semibold text-stone-500">
                      Replies ({selectedPost.replies?.length ?? 0})
                    </h4>

                    {selectedPost.replies && selectedPost.replies.length > 0 ? (
                      <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                        {selectedPost.replies.map((reply) => (
                          <div
                            key={String(reply.id)}
                            className="rounded-lg bg-stone-50 dark:bg-stone-900/60 border border-stone-200/70 dark:border-stone-800 p-3 text-xs"
                          >
                            <div className="flex items-center justify-between text-stone-500 mb-1">
                              <span className="font-semibold text-stone-800 dark:text-stone-200">
                                {reply.author_name || 'Responder'}
                                {reply.author_role ? ` (${reply.author_role})` : ''}
                              </span>
                              <span className="font-mono">{formatDateTime(reply.created_at)}</span>
                            </div>
                            <p className="text-stone-700 dark:text-stone-300 whitespace-pre-line">
                              {reply.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-stone-500">No replies yet. Be the first to respond.</p>
                    )}

                    <form onSubmit={handleSendReply} className="pt-2 flex gap-2">
                      <input
                        type="text"
                        required
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        placeholder="Write a helpful response..."
                        className="flex-1 px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                      />
                      <button
                        type="submit"
                        disabled={replying}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50 cursor-pointer"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Reply</span>
                      </button>
                    </form>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Create Post Modal */}
      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-lg rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                {canPostAdvisoryTypes ? 'Create Community Post or Advisory' : 'Ask a Maize Farming Question'}
              </h3>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="text-stone-400 hover:text-stone-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreatePost} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Describe your question or advisory topic clearly"
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              {canPostAdvisoryTypes && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                      Post Type
                    </label>
                    <select
                      value={newType}
                      onChange={(e) => setNewType(e.target.value as any)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    >
                      <option value="question">Question</option>
                      <option value="advisory">Advisory</option>
                      <option value="announcement">Announcement</option>
                      <option value="alert">Alert</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                      Priority
                    </label>
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value as any)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                    >
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-stone-700 dark:text-stone-300 mb-1">
                  Details *
                </label>
                <textarea
                  rows={4}
                  required
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="Include leaf symptoms, crop stage, woreda conditions, or treatment questions..."
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCreateOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-stone-700 dark:text-stone-300 bg-stone-100 dark:bg-stone-800 rounded-lg cursor-pointer"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 rounded-lg disabled:opacity-50 cursor-pointer"
                >
                  {creating ? 'Publishing...' : 'Publish Post'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
};
