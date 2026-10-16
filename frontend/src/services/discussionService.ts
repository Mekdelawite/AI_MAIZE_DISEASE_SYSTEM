import { apiRequest } from './api';
import { DiscussionPost, DiscussionReply } from '../types/api';
import { resolveMediaUrl } from '../utils/media';

export interface DiscussionFilterParams {
  search?: string;
  post_type?: string;
  priority?: string;
  page?: number;
  per_page?: number;
  mine?: boolean;
}

export interface CreatePostPayload {
  title: string;
  content: string;
  post_type?: 'question' | 'advisory' | 'announcement' | 'alert';
  priority?: 'normal' | 'important' | 'urgent';
  image_path?: string | null;
}

function normalizePost(raw: any): DiscussionPost {
  const author = raw?.author || {};
  const target = raw?.target_location || {};
  return {
    ...raw,
    author_id: raw?.author_id ?? author.id,
    author_name: raw?.author_name ?? author.full_name,
    author_role: raw?.author_role ?? author.role,
    author_verified: Boolean(raw?.author_verified),
    image_url: resolveMediaUrl(raw?.image_url ?? raw?.image_path),
    region: raw?.region ?? target.region,
    woreda: raw?.woreda ?? target.woreda,
    kebele: raw?.kebele ?? target.kebele,
    replies_count: Number(raw?.replies_count ?? raw?.reply_count ?? raw?.replies?.length ?? 0),
    likes_count: Number(raw?.likes_count ?? 0),
    liked_by_current_user: Boolean(raw?.liked_by_current_user),
    replies: Array.isArray(raw?.replies) ? raw.replies.map(normalizeReply) : undefined,
  };
}

function normalizeReply(raw: any): DiscussionReply {
  const author = raw?.author || {};
  return {
    ...raw,
    author_id: raw?.author_id ?? author.id,
    author_name: raw?.author_name ?? author.full_name,
    author_role: raw?.author_role ?? author.role,
  };
}

export const discussionService = {
  async getPosts(params: DiscussionFilterParams = {}): Promise<{
    posts: DiscussionPost[];
    total: number;
    page: number;
    pages: number;
  }> {
    const res = await apiRequest<any>('/api/discussion/posts', {
      method: 'GET',
      params: params as Record<string, string | number | boolean | undefined>,
    });

    const rows: any[] = Array.isArray(res)
      ? res
      : Array.isArray(res?.posts)
        ? res.posts
        : Array.isArray(res?.items)
          ? res.items
          : [];
    const posts = rows.map(normalizePost);
    const pagination = res?.pagination || {};

    return {
      posts,
      total: Number(res?.total ?? pagination.total_items ?? posts.length),
      page: Number(res?.page ?? pagination.page ?? params.page ?? 1),
      pages: Number(res?.pages ?? res?.total_pages ?? pagination.total_pages ?? 1),
    };
  },

  async createPost(payload: CreatePostPayload): Promise<DiscussionPost> {
    const res = await apiRequest<any>('/api/discussion/posts', {
      method: 'POST',
      body: payload,
    });
    return normalizePost(res?.post || res);
  },

  async getPostDetail(postId: string | number): Promise<DiscussionPost> {
    const res = await apiRequest<any>(`/api/discussion/posts/${encodeURIComponent(String(postId))}`, {
      method: 'GET',
    });
    const post = res?.post || res;
    return normalizePost(post);
  },

  async createReply(postId: string | number, content: string): Promise<DiscussionReply> {
    const res = await apiRequest<any>(`/api/discussion/posts/${encodeURIComponent(String(postId))}/replies`, {
      method: 'POST',
      body: { content: content.trim() },
    });
    return normalizeReply(res?.reply || res);
  },

  async uploadImage(file: File): Promise<{ image_path: string; image_url: string }> {
    const body = new FormData();
    body.append('image', file);
    return apiRequest('/api/discussion/posts/images', { method: 'POST', body });
  },

  async setLike(postId: string | number, liked: boolean): Promise<{ liked: boolean; likes_count: number }> {
    return apiRequest(`/api/discussion/posts/${encodeURIComponent(String(postId))}/like`, {
      method: liked ? 'POST' : 'DELETE',
    });
  },

  async updatePost(postId: string | number, payload: Pick<CreatePostPayload, 'title' | 'content' | 'image_path'>): Promise<DiscussionPost> {
    const res = await apiRequest<any>(`/api/discussion/posts/${encodeURIComponent(String(postId))}`, {
      method: 'PATCH',
      body: payload,
    });
    return normalizePost(res?.post || res);
  },

  async deletePost(postId: string | number): Promise<void> {
    await apiRequest(`/api/discussion/posts/${encodeURIComponent(String(postId))}`, {
      method: 'DELETE',
    });
  },
};
