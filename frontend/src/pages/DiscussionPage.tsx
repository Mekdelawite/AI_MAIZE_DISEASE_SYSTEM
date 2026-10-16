import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  BadgeCheck,
  Camera,
  ChevronLeft,
  ChevronRight,
  Heart,
  Image as ImageIcon,
  MessageCircle,
  MoreHorizontal,
  Pencil,
  Search,
  Send,
  Share2,
  Sprout,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from '../components/common/FeedbackStates';
import { AppShell } from '../components/layout/AppShell';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { discussionService } from '../services/discussionService';
import { DiscussionPost } from '../types/api';
import { formatDateTime } from '../utils/media';

const POST_TYPES = ['question', 'advisory', 'announcement', 'alert'] as const;
const POST_TYPE_LABELS: Record<(typeof POST_TYPES)[number], string> = {
  question: 'communityQuestions',
  advisory: 'communityAdvisories',
  announcement: 'communityAnnouncements',
  alert: 'communityAlerts',
};

function relativeTime(value?: string): string {
  if (!value) return '';
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return formatDateTime(value);
  const seconds = Math.round((timestamp - Date.now()) / 1000);
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 31536000], ['month', 2592000], ['week', 604800],
    ['day', 86400], ['hour', 3600], ['minute', 60], ['second', 1],
  ];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size || unit === 'second') {
      return formatter.format(Math.round(seconds / size), unit);
    }
  }
  return formatDateTime(value);
}

function initials(name?: string): string {
  return (name || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

export const DiscussionPage: React.FC = () => {
  const { t, notify } = useApp();
  const { user, effectiveRole } = useAuth();
  const imageInputRef = useRef<HTMLInputElement>(null);

  const [posts, setPosts] = useState<DiscussionPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [postType, setPostType] = useState('');
  const [priority, setPriority] = useState('');
  const [myPosts, setMyPosts] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [composerOpen, setComposerOpen] = useState(false);
  const [editingPost, setEditingPost] = useState<DiscussionPost | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [newType, setNewType] = useState<'question' | 'advisory' | 'announcement' | 'alert'>('question');
  const [newPriority, setNewPriority] = useState<'normal' | 'important' | 'urgent'>('normal');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [removeCurrentImage, setRemoveCurrentImage] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const [selectedPost, setSelectedPost] = useState<DiscussionPost | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [comment, setComment] = useState('');
  const [sendingComment, setSendingComment] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DiscussionPost | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [likePending, setLikePending] = useState<Set<string>>(new Set());
  const sharedPostOpened = useRef(false);

  const canCreatePostTypes = effectiveRole === 'extension_agent' || effectiveRole === 'admin';

  const loadPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await discussionService.getPosts({
        search: search || undefined,
        post_type: postType || undefined,
        priority: priority || undefined,
        page,
        per_page: 10,
        mine: myPosts || undefined,
      });
      setPosts(result.posts);
      setTotalPages(Math.max(1, result.pages));
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load community posts.');
    } finally {
      setLoading(false);
    }
  }, [search, postType, priority, page, myPosts]);

  useEffect(() => { void loadPosts(); }, [loadPosts]);
  useEffect(() => () => {
    if (imagePreview?.startsWith('blob:')) URL.revokeObjectURL(imagePreview);
  }, [imagePreview]);

  const activeAgents = useMemo(() => {
    const seen = new Set<string>();
    return posts.filter((post) => {
      const key = String(post.author_id ?? post.author_name ?? post.id);
      if (!post.author_verified || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [posts]);

  const activeDiscussions = useMemo(
    () => [...posts].sort((a, b) =>
      (b.likes_count ?? 0) + (b.replies_count ?? 0) - (a.likes_count ?? 0) - (a.replies_count ?? 0)
    ).slice(0, 4),
    [posts],
  );

  const clearComposer = () => {
    setTitle('');
    setContent('');
    setImageFile(null);
    setImagePreview(null);
    setRemoveCurrentImage(false);
    setEditingPost(null);
    setComposerOpen(false);
  };

  const openCreateComposer = () => {
    clearComposer();
    setNewType(effectiveRole === 'farmer' ? 'question' : 'advisory');
    setComposerOpen(true);
  };

  const openEditComposer = (post: DiscussionPost) => {
    setEditingPost(post);
    setTitle(post.title);
    setContent(post.content);
    setNewType((POST_TYPES.includes(post.post_type as typeof POST_TYPES[number]) ? post.post_type : 'question') as typeof newType);
    setNewPriority(post.priority === 'urgent' || post.priority === 'important' ? post.priority : 'normal');
    setImageFile(null);
    setImagePreview(post.image_url || null);
    setRemoveCurrentImage(false);
    setComposerOpen(true);
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      notify(t('communityChooseImage'), 'warning');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      notify(t('communityImageSize'), 'warning');
      return;
    }
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setRemoveCurrentImage(false);
  };

  const handlePublish = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanContent = content.trim();
    const cleanTitle = title.trim() || cleanContent.slice(0, 100);
    if (!cleanContent || !cleanTitle) return;

    setPublishing(true);
    try {
      let imagePath = editingPost?.image_path || undefined;
      if (removeCurrentImage) imagePath = undefined;
      if (imageFile) {
        const uploaded = await discussionService.uploadImage(imageFile);
        imagePath = uploaded.image_path;
      }

      if (editingPost) {
        await discussionService.updatePost(editingPost.id, {
          title: cleanTitle,
          content: cleanContent,
          image_path: removeCurrentImage ? null : imagePath,
        });
        notify(t('communityPostUpdated'), 'success');
      } else {
        await discussionService.createPost({
          title: cleanTitle,
          content: cleanContent,
          post_type: canCreatePostTypes ? newType : 'question',
          priority: newPriority,
          image_path: imagePath,
        });
        notify(t('communityPostCreated'), 'success');
      }

      clearComposer();
      setPage(1);
      if (editingPost) {
        await loadPosts();
      } else {
        setMyPosts(false);
      }
    } catch (requestError: unknown) {
      notify(requestError instanceof Error ? requestError.message : 'Unable to publish this post.', 'error');
    } finally {
      setPublishing(false);
    }
  };

  const openPost = async (post: DiscussionPost) => {
    setSelectedPost(post);
    setDetailLoading(true);
    try {
      setSelectedPost(await discussionService.getPostDetail(post.id));
    } catch (requestError: unknown) {
      notify(requestError instanceof Error ? requestError.message : 'Unable to load comments.', 'error');
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    if (sharedPostOpened.current || loading || posts.length === 0) return;
    const postId = new URLSearchParams(window.location.search).get('post');
    if (!postId) return;
    const post = posts.find((item) => String(item.id) === postId);
    if (post) {
      sharedPostOpened.current = true;
      void openPost(post);
    }
  }, [loading, posts]);

  const handleLike = async (post: DiscussionPost) => {
    const key = String(post.id);
    if (likePending.has(key)) return;
    const wasLiked = Boolean(post.liked_by_current_user);
    setLikePending((previous) => new Set(previous).add(key));
    setPosts((previous) => previous.map((item) => item.id === post.id
      ? { ...item, liked_by_current_user: !wasLiked, likes_count: Math.max(0, (item.likes_count ?? 0) + (wasLiked ? -1 : 1)) }
      : item));
    if (selectedPost?.id === post.id) {
      setSelectedPost((previous) => previous ? {
        ...previous,
        liked_by_current_user: !wasLiked,
        likes_count: Math.max(0, (previous.likes_count ?? 0) + (wasLiked ? -1 : 1)),
      } : previous);
    }
    try {
      const result = await discussionService.setLike(post.id, !wasLiked);
      setPosts((previous) => previous.map((item) => item.id === post.id
        ? { ...item, liked_by_current_user: result.liked, likes_count: result.likes_count }
        : item));
      setSelectedPost((previous) => previous?.id === post.id
        ? { ...previous, liked_by_current_user: result.liked, likes_count: result.likes_count }
        : previous);
    } catch (requestError: unknown) {
      setPosts((previous) => previous.map((item) => item.id === post.id
        ? { ...item, liked_by_current_user: wasLiked, likes_count: Math.max(0, (item.likes_count ?? 0) + (wasLiked ? 1 : -1)) }
        : item));
      setSelectedPost((previous) => previous?.id === post.id
        ? { ...previous, liked_by_current_user: wasLiked, likes_count: Math.max(0, (previous.likes_count ?? 0) + (wasLiked ? 1 : -1)) }
        : previous);
      notify(requestError instanceof Error ? requestError.message : 'Unable to update your like.', 'error');
    } finally {
      setLikePending((previous) => {
        const next = new Set(previous);
        next.delete(key);
        return next;
      });
    }
  };

  const handleSendComment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedPost || !comment.trim()) return;
    setSendingComment(true);
    try {
      await discussionService.createReply(selectedPost.id, comment.trim());
      setComment('');
      notify(t('communityCommentCreated'), 'success');
      try {
        const detail = await discussionService.getPostDetail(selectedPost.id);
        setSelectedPost(detail);
      } catch (refreshError: unknown) {
        notify(refreshError instanceof Error ? refreshError.message : 'Unable to refresh comments.', 'error');
      }
      await loadPosts();
    } catch (requestError: unknown) {
      notify(requestError instanceof Error ? requestError.message : 'Unable to add your comment.', 'error');
    } finally {
      setSendingComment(false);
    }
  };

  const handleDeletePost = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await discussionService.deletePost(deleteTarget.id);
      setPosts((previous) => previous.filter((post) => post.id !== deleteTarget.id));
      if (selectedPost?.id === deleteTarget.id) setSelectedPost(null);
      setDeleteTarget(null);
      await loadPosts();
      notify(t('communityPostDeleted'), 'success');
    } catch (requestError: unknown) {
      notify(requestError instanceof Error ? requestError.message : 'Unable to delete this post.', 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleShare = async (post: DiscussionPost) => {
    const url = `${window.location.origin}/farmer/discussion?post=${encodeURIComponent(String(post.id))}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: post.title, text: post.content, url });
      } else {
        await navigator.clipboard.writeText(url);
        notify(t('communityCopyLink'), 'success');
      }
    } catch (shareError: any) {
      if (shareError?.name !== 'AbortError') notify('Unable to share this post.', 'error');
    }
  };

  const beginSearch = (event: React.FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const isOwner = (post: DiscussionPost) => String(post.author_id) === String(user?.id);

  return (
    <AppShell title={t('navDiscussion')} subtitle={t('communityComposerHint')}>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <aside className="hidden xl:col-span-3 xl:block">
          <div className="sticky top-20 space-y-3">
            <div className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-[#121A16]">
              <button type="button" onClick={() => { setMyPosts(false); setPage(1); }} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold ${!myPosts ? 'bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200' : 'text-stone-700 hover:bg-stone-50 dark:text-stone-300 dark:hover:bg-stone-800'}`}>
                <Users className="h-4 w-4" />{t('communityHome')}
              </button>
              <button type="button" onClick={() => { setMyPosts(true); setPage(1); }} className={`mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold ${myPosts ? 'bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200' : 'text-stone-700 hover:bg-stone-50 dark:text-stone-300 dark:hover:bg-stone-800'}`}>
                <Sprout className="h-4 w-4" />{t('communityMyPosts')}
              </button>
              <div className="mt-3 border-t border-stone-200 pt-3 dark:border-stone-800">
                <p className="px-3 text-xs font-semibold uppercase tracking-wide text-stone-400">MaizeCare</p>
                <p className="px-3 pt-2 text-xs leading-relaxed text-stone-500 dark:text-stone-400">Farmer questions and extension guidance, shared with your community.</p>
              </div>
            </div>
          </div>
        </aside>

        <main className="space-y-4 xl:col-span-6">
          <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm dark:border-stone-800 dark:bg-[#121A16] sm:p-5">
            <button type="button" onClick={openCreateComposer} className="flex w-full items-center gap-3 rounded-xl bg-stone-50 px-4 py-3 text-left text-sm text-stone-500 hover:bg-stone-100 dark:bg-stone-900 dark:text-stone-400 dark:hover:bg-stone-800">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-800 font-bold text-white">{initials(user?.full_name || user?.name)}</span>
              <span className="flex-1">{t('communityPostPlaceholder')}</span>
              <Camera className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
            </button>
            <p className="px-2 pt-3 text-xs text-stone-500 dark:text-stone-400">{t('communityComposerHint')}</p>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-[#121A16]">
            <form onSubmit={beginSearch} className="flex flex-wrap gap-2">
              <div className="relative min-w-[200px] flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={t('communitySearchPlaceholder')} className="w-full rounded-xl border border-stone-200 bg-stone-50 py-2.5 pl-9 pr-3 text-sm dark:border-stone-700 dark:bg-stone-900" />
              </div>
              <button type="submit" className="rounded-xl bg-emerald-900 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800">{t('search')}</button>
              <select aria-label={t('communityAllTypes')} value={postType} onChange={(event) => { setPostType(event.target.value); setPage(1); }} className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900">
                <option value="">{t('communityAllTypes')}</option>
                {POST_TYPES.map((type) => <option key={type} value={type}>{t(POST_TYPE_LABELS[type])}</option>)}
              </select>
              <select aria-label={t('communityAllPriorities')} value={priority} onChange={(event) => { setPriority(event.target.value); setPage(1); }} className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900">
              <option value="">{t('communityAllPriorities')}</option>
                <option value="normal">{t('communityNormal')}</option><option value="important">{t('communityImportant')}</option><option value="urgent">{t('communityUrgent')}</option>
              </select>
            </form>
          </div>

          {loading ? <LoadingSkeleton rows={4} /> : error ? <ErrorState title={t('communityLoadError')} message={error} onRetry={loadPosts} /> : posts.length === 0 ? (
            <EmptyState title={myPosts ? t('communityMyPosts') : t('communityNoPosts')} description={t('communityNoPosts')} actionLabel={t('communityCreatePost')} onAction={openCreateComposer} />
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <article key={String(post.id)} className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-[#121A16]">
                  <div className="flex items-start gap-3 p-4 sm:p-5">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">{initials(post.author_name)}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5 text-sm font-semibold text-stone-900 dark:text-stone-100">
                        <span>{post.author_name || t('communityMember')}</span>
                        {post.author_verified && <span title={t('communityVerifiedAgent')} className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 dark:text-emerald-300"><BadgeCheck className="h-4 w-4" /><span className="hidden sm:inline">{t('communityVerifiedAgent')}</span></span>}
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-stone-500 dark:text-stone-400">
                        <span>{relativeTime(post.created_at)}</span><span aria-hidden="true">·</span><span className="capitalize">{POST_TYPES.includes(post.post_type as typeof POST_TYPES[number]) ? t(POST_TYPE_LABELS[post.post_type as typeof POST_TYPES[number]]) : post.post_type}</span>
                        {post.region && <><span aria-hidden="true">·</span><span>{post.region}{post.woreda ? `, ${post.woreda}` : ''}</span></>}
                        {post.priority && post.priority !== 'normal' && <span className="rounded-full bg-amber-50 px-2 py-0.5 capitalize text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">{post.priority}</span>}
                      </div>
                    </div>
                    {isOwner(post) && <div className="group relative">
                      <button type="button" aria-label={t('communityPostOptions')} className="rounded-full p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><MoreHorizontal className="h-5 w-5" /></button>
                      <div className="invisible absolute right-0 top-9 z-10 w-36 rounded-xl border border-stone-200 bg-white p-1 opacity-0 shadow-lg group-focus-within:visible group-hover:visible group-focus-within:opacity-100 group-hover:opacity-100 dark:border-stone-700 dark:bg-stone-900">
                        <button type="button" onClick={() => openEditComposer(post)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs hover:bg-stone-100 dark:hover:bg-stone-800"><Pencil className="h-3.5 w-3.5" />{t('communityEdit')}</button>
                        <button type="button" onClick={() => setDeleteTarget(post)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/30"><Trash2 className="h-3.5 w-3.5" />{t('communityDelete')}</button>
                      </div>
                    </div>}
                  </div>
                  <button type="button" onClick={() => void openPost(post)} className="block w-full px-4 pb-3 text-left sm:px-5">
                    <h2 className="text-base font-bold text-stone-900 dark:text-stone-100">{post.title}</h2>
                    <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-stone-700 dark:text-stone-300">{post.content}</p>
                  </button>
                  {post.image_url && <button type="button" onClick={() => void openPost(post)} className="block max-h-[480px] w-full overflow-hidden bg-stone-100 dark:bg-stone-900"><img src={post.image_url} alt={t('communityImageAlt')} loading="lazy" className="mx-auto max-h-[480px] w-full object-contain" /></button>}
                  <div className="flex items-center justify-between px-4 py-2 text-xs text-stone-500 dark:text-stone-400 sm:px-5">
                    <span>{post.likes_count ?? 0} {t('communityLike').toLowerCase()}{(post.likes_count ?? 0) === 1 ? '' : 's'}</span>
                    <button type="button" onClick={() => void openPost(post)} className="hover:underline">{post.replies_count ?? 0} {t('communityComment').toLowerCase()}{(post.replies_count ?? 0) === 1 ? '' : 's'}</button>
                  </div>
                  <div className="mx-4 border-t border-stone-200 dark:border-stone-800 sm:mx-5" />
                  <div className="grid grid-cols-3 px-2 py-1.5 sm:px-3">
                    <button type="button" disabled={likePending.has(String(post.id))} onClick={() => void handleLike(post)} className={`flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold hover:bg-stone-100 disabled:opacity-60 dark:hover:bg-stone-800 ${post.liked_by_current_user ? 'text-rose-600 dark:text-rose-400' : 'text-stone-600 dark:text-stone-300'}`}><Heart className={`h-4 w-4 ${post.liked_by_current_user ? 'fill-current' : ''}`} />{post.liked_by_current_user ? t('communityUnlike') : t('communityLike')}</button>
                    <button type="button" onClick={() => void openPost(post)} className="flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800"><MessageCircle className="h-4 w-4" />{t('communityComment')}</button>
                    <button type="button" onClick={() => void handleShare(post)} className="flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800"><Share2 className="h-4 w-4" />{t('communityShare')}</button>
                  </div>
                </article>
              ))}
            </div>
          )}

          {!loading && !error && totalPages > 1 && <div className="flex items-center justify-between rounded-2xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-[#121A16]">
            <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm disabled:opacity-40"><ChevronLeft className="h-4 w-4" />{t('back')}</button>
            <span className="text-xs text-stone-500">{t('communityPage')} {page} {t('communityOf')} {totalPages}</span>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm disabled:opacity-40">{t('communityNext')}<ChevronRight className="h-4 w-4" /></button>
          </div>}
        </main>

        <aside className="space-y-4 xl:col-span-3">
          <section className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-[#121A16]">
            <h2 className="flex items-center gap-2 text-sm font-bold text-stone-900 dark:text-stone-100"><Sprout className="h-4 w-4 text-emerald-700" />{t('communityActiveDiscussions')}</h2>
            {activeDiscussions.length ? <ul className="mt-3 space-y-1">{activeDiscussions.map((post) => <li key={String(post.id)}><button type="button" onClick={() => void openPost(post)} className="w-full rounded-lg p-2 text-left hover:bg-stone-50 dark:hover:bg-stone-800"><span className="line-clamp-2 text-xs font-semibold text-stone-800 dark:text-stone-200">{post.title}</span><span className="mt-1 block text-[11px] text-stone-500">{post.likes_count ?? 0} likes · {post.replies_count ?? 0} comments</span></button></li>)}</ul> : <p className="mt-3 text-xs text-stone-500">{t('communityNoPosts')}</p>}
          </section>
          {activeAgents.length > 0 && <section className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-[#121A16]">
            <h2 className="text-sm font-bold text-stone-900 dark:text-stone-100">{t('communityVerifiedAgents')}</h2>
            <ul className="mt-3 space-y-3">{activeAgents.slice(0, 5).map((post) => <li key={`${post.author_id}-${post.id}`} className="flex items-center gap-2.5"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">{initials(post.author_name)}</span><span className="min-w-0"><span className="block truncate text-xs font-semibold text-stone-800 dark:text-stone-200">{post.author_name}</span><span className="text-[11px] text-stone-500">{post.region || 'Extension agent'}</span></span><BadgeCheck className="ml-auto h-4 w-4 shrink-0 text-emerald-700" /></li>)}</ul>
          </section>}
        </aside>
      </div>

      {selectedPost && <div className="fixed inset-0 z-40 flex justify-end bg-black/40" onClick={() => setSelectedPost(null)}>
        <section role="dialog" aria-modal="true" aria-label={selectedPost.title} onClick={(event) => event.stopPropagation()} className="flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl dark:bg-[#121A16]">
          <header className="flex items-start justify-between gap-4 border-b border-stone-200 p-5 dark:border-stone-800"><div><p className="text-xs capitalize text-stone-500">{selectedPost.post_type} · {relativeTime(selectedPost.created_at)}</p><h2 className="mt-1 text-lg font-bold text-stone-900 dark:text-stone-100">{selectedPost.title}</h2></div><button type="button" onClick={() => setSelectedPost(null)} aria-label={t('cancel')} className="rounded-full p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><X className="h-5 w-5" /></button></header>
          {detailLoading ? <div className="p-5"><LoadingSkeleton rows={3} /></div> : <>
            <div className="flex-1 overflow-y-auto p-5"><div className="mb-4 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 font-bold text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">{initials(selectedPost.author_name)}</span><div><p className="text-sm font-semibold text-stone-900 dark:text-stone-100">{selectedPost.author_name}</p><p className="text-xs text-stone-500">{selectedPost.author_role}{selectedPost.region ? ` · ${selectedPost.region}` : ''}</p></div>{selectedPost.author_verified && <BadgeCheck className="h-4 w-4 text-emerald-700" />}</div><p className="whitespace-pre-line text-sm leading-relaxed text-stone-700 dark:text-stone-300">{selectedPost.content}</p>{selectedPost.image_url && <img src={selectedPost.image_url} alt="Community post" className="mt-4 max-h-[420px] w-full rounded-xl bg-stone-100 object-contain dark:bg-stone-900" />}
              <div className="mt-5 border-t border-stone-200 pt-4 dark:border-stone-800"><h3 className="text-sm font-bold text-stone-900 dark:text-stone-100">{t('communityComment')}s ({selectedPost.replies?.length ?? selectedPost.replies_count ?? 0})</h3>{selectedPost.replies?.length ? <ul className="mt-4 space-y-4">{selectedPost.replies.map((reply) => <li key={String(reply.id)} className="flex gap-2.5"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-stone-100 text-xs font-bold text-stone-700 dark:bg-stone-800 dark:text-stone-300">{initials(reply.author_name)}</span><div className="min-w-0 flex-1 rounded-2xl bg-stone-50 p-3 dark:bg-stone-900"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold text-stone-800 dark:text-stone-200">{reply.author_name || t('communityMember')}</span><span className="text-[11px] text-stone-500">{relativeTime(reply.created_at)}</span></div><p className="mt-1 whitespace-pre-line text-sm text-stone-700 dark:text-stone-300">{reply.content}</p></div></li>)}</ul> : <p className="mt-3 text-xs text-stone-500">{t('communityNoComments')}</p>}</div>
            </div>
            <form onSubmit={handleSendComment} className="flex gap-2 border-t border-stone-200 p-4 dark:border-stone-800"><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder={t('communityWriteComment')} maxLength={10000} className="min-w-0 flex-1 rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm dark:border-stone-700 dark:bg-stone-900" /><button type="submit" disabled={sendingComment || !comment.trim()} className="inline-flex items-center gap-2 rounded-xl bg-emerald-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"><Send className="h-4 w-4" /><span className="hidden sm:inline">{t('communitySend')}</span></button></form>
          </>}
        </section>
      </div>}

      {composerOpen && <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby="community-composer-title"><section className="my-auto w-full max-w-xl rounded-2xl bg-white p-5 shadow-xl dark:bg-[#121A16] sm:p-6"><header className="mb-4 flex items-center justify-between border-b border-stone-200 pb-3 dark:border-stone-800"><h2 id="community-composer-title" className="text-lg font-bold text-stone-900 dark:text-stone-100">{editingPost ? t('communityEdit') : t('communityCreatePost')}</h2><button type="button" onClick={clearComposer} aria-label={t('cancel')} className="rounded-full p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><X className="h-5 w-5" /></button></header>
        <form onSubmit={handlePublish} className="space-y-4">
          <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 font-bold text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">{initials(user?.full_name || user?.name)}</span><span className="text-sm font-semibold text-stone-900 dark:text-stone-100">{user?.full_name || user?.name}</span></div>
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} placeholder={t('communityTitlePlaceholder')} className="w-full rounded-xl border border-stone-200 bg-stone-50 px-3.5 py-2.5 text-sm dark:border-stone-700 dark:bg-stone-900" />
          {!editingPost && canCreatePostTypes && <div className="grid grid-cols-2 gap-3"><select value={newType} onChange={(event) => setNewType(event.target.value as typeof newType)} className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900">{effectiveRole === 'admin' && <option value="question">{t('communityQuestions')}</option>}<option value="advisory">{t('communityAdvisories')}</option><option value="announcement">{t('communityAnnouncements')}</option><option value="alert">{t('communityAlerts')}</option></select><select value={newPriority} onChange={(event) => setNewPriority(event.target.value as typeof newPriority)} className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"><option value="normal">{t('communityNormal')}</option><option value="important">{t('communityImportant')}</option><option value="urgent">{t('communityUrgent')}</option></select></div>}
          <textarea required value={content} onChange={(event) => setContent(event.target.value)} maxLength={10000} rows={6} placeholder={t('communityPostPlaceholder')} className="w-full resize-y rounded-xl border border-stone-200 bg-stone-50 px-3.5 py-3 text-sm leading-relaxed dark:border-stone-700 dark:bg-stone-900" />
          {imagePreview && <div className="relative overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800"><img src={imagePreview} alt={t('communityImageLabel')} className="max-h-72 w-full bg-stone-100 object-contain dark:bg-stone-900" /><button type="button" onClick={() => { setImageFile(null); setImagePreview(null); setRemoveCurrentImage(Boolean(editingPost?.image_path)); }} className="absolute right-2 top-2 rounded-full bg-black/70 p-2 text-white" aria-label={t('communityRemoveImage')}><X className="h-4 w-4" /></button></div>}
          {removeCurrentImage && !imagePreview && <p className="text-xs text-stone-500">{t('communityRemoveImage')}</p>}
          <input ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleImageChange} className="hidden" />
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 p-3 dark:border-stone-800"><span className="text-xs font-semibold text-stone-600 dark:text-stone-300">{t('communityAddToPost')}</span><button type="button" onClick={() => imageInputRef.current?.click()} className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-950/40"><ImageIcon className="h-4 w-4" />{t('communityImage')}</button></div>
          <footer className="flex justify-end gap-2"><button type="button" onClick={clearComposer} className="rounded-xl bg-stone-100 px-4 py-2.5 text-sm font-semibold text-stone-700 dark:bg-stone-800 dark:text-stone-200">{t('cancel')}</button><button type="submit" disabled={publishing || !content.trim()} className="rounded-xl bg-emerald-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{publishing ? t('communityPublishing') : t('communityPublish')}</button></footer>
        </form>
      </section></div>}

      <ConfirmDialog open={Boolean(deleteTarget)} title={t('communityDelete')} description={t('communityDeleteConfirm')} confirmLabel={t('communityDelete')} cancelLabel={t('cancel')} variant="danger" loading={deleting} onConfirm={handleDeletePost} onCancel={() => setDeleteTarget(null)} />
    </AppShell>
  );
};
