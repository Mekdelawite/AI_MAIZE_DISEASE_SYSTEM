import { apiRequest } from './api';
import { DiscussionPost, DiscussionReply } from '../types/api';

export interface DiscussionFilterParams {
  search?: string;
  post_type?: string;
  priority?: string;
  page?: number;
  per_page?: number;
}

export interface CreatePostPayload {
  title: string;
  content: string;
  post_type?: 'question' | 'advisory' | 'announcement' | 'alert';
  priority?: 'low' | 'normal' | 'medium' | 'high' | 'urgent';
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
      params: params as Record<string, string | number | undefined>,
    });

    const posts = Array.isArray(res)
      ? res
      : Array.isArray(res?.posts)
      ? res.posts
      : Array.isArray(res?.items)
      ? res.items
      : [];

    return {
      posts,
      total: Number(res?.total ?? posts.length),
      page: Number(res?.page ?? params.page ?? 1),
      pages: Number(res?.pages ?? res?.total_pages ?? 1),
    };
  },

  async createPost(payload: CreatePostPayload): Promise<DiscussionPost> {
    const res = await apiRequest<any>('/api/discussion/posts', {
      method: 'POST',
      body: payload,
    });
    return res?.post || res;
  },

  async getPostDetail(postId: string | number): Promise<DiscussionPost> {
    const res = await apiRequest<any>(`/api/discussion/posts/${encodeURIComponent(String(postId))}`, {
      method: 'GET',
    });
    return res?.post || res;
  },

  async createReply(postId: string | number, content: string): Promise<DiscussionReply> {
    const res = await apiRequest<any>(`/api/discussion/posts/${encodeURIComponent(String(postId))}/replies`, {
      method: 'POST',
      body: { content: content.trim() },
    });
    return res?.reply || res;
  },
};
