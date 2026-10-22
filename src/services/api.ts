import { getApiBaseUrl } from '../utils/media';

const TOKEN_STORAGE_KEY = 'maizecare_jwt_token';

export class ApiError extends Error {
  public status: number;
  public code: string;
  public details?: unknown;
  public isNetworkError: boolean;

  constructor(message: string, status = 0, code = 'API_ERROR', details?: unknown, isNetworkError = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.isNetworkError = isNetworkError;
  }
}

export function getStoredToken(): string | null {
  try {
    // Remove tokens saved by older versions so they cannot keep a persistent session.
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem('maize_token');
    localStorage.removeItem('maizecare_jwt_token');
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (!token) {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem('maize_token');
    localStorage.removeItem('maizecare_jwt_token');
  } catch {
    // ignore storage errors
  }
}

let unauthorizedHandler: (() => void) | null = null;

export function setOnUnauthorized(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  timeoutMs?: number;
  skipAuth?: boolean;
}

function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined | null>): string {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = new URL(`${baseUrl}${cleanEndpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

function extractErrorMessage(payload: any, fallbackStatusText: string, status: number): { message: string; code: string; details?: unknown } {
  if (payload && typeof payload === 'object') {
    if (payload.error && typeof payload.error === 'object') {
      return {
        message: payload.error.message || payload.message || `Request failed (${status})`,
        code: payload.error.code || `HTTP_${status}`,
        details: payload.error.details || payload.details,
      };
    }
    if (typeof payload.error === 'string') {
      return {
        message: payload.error,
        code: payload.code || `HTTP_${status}`,
        details: payload.details,
      };
    }
    if (typeof payload.message === 'string') {
      return {
        message: payload.message,
        code: payload.code || `HTTP_${status}`,
        details: payload.errors || payload.details,
      };
    }
  }
  return {
    message: fallbackStatusText || `Server returned HTTP ${status}`,
    code: `HTTP_${status}`,
  };
}

export async function apiRequest<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, timeoutMs = 45000, skipAuth = false, headers: customHeaders, ...rest } = options;
  const url = buildUrl(endpoint, params);

  const headers = new Headers(customHeaders || {});
  if (!skipAuth) {
    const token = getStoredToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  let preparedBody: BodyInit | undefined;
  if (body instanceof FormData) {
    // Let browser set multipart/form-data boundary automatically
    preparedBody = body;
  } else if (body !== undefined && body !== null) {
    headers.set('Content-Type', 'application/json');
    preparedBody = JSON.stringify(body);
  }

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...rest,
      headers,
      body: preparedBody,
      signal: controller.signal,
    });

    const contentType = response.headers.get('content-type') || '';
    let parsed: any = null;

    if (contentType.includes('application/json')) {
      try {
        parsed = await response.json();
      } catch {
        parsed = null;
      }
    } else {
      const text = await response.text();
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = { message: text };
      }
    }

    if (response.status === 401 && !skipAuth) {
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
    }

    if (!response.ok || (parsed && typeof parsed === 'object' && parsed.success === false)) {
      const { message, code, details } = extractErrorMessage(parsed, response.statusText, response.status);
      throw new ApiError(message, response.status, code, details, false);
    }

    // Unwrap standard envelope `{ success: true, data: ... }` when present, or return parsed directly
    if (parsed && typeof parsed === 'object' && 'data' in parsed && parsed.data !== undefined && parsed.data !== null) {
      return parsed.data as T;
    }

    return parsed as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err?.name === 'AbortError') {
      throw new ApiError(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s while waiting for ${getApiBaseUrl()}.`,
        408,
        'TIMEOUT_ERROR',
        undefined,
        true
      );
    }
    throw new ApiError(
      `Unable to reach the Flask API server at ${getApiBaseUrl()}. Verify that the backend is running and CORS is enabled.`,
      0,
      'NETWORK_ERROR',
      undefined,
      true
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function apiDownloadBlob(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined | null>
): Promise<{ blob: Blob; filename: string }> {
  const url = buildUrl(endpoint, params);
  const headers = new Headers();
  const token = getStoredToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    const contentType = response.headers.get('content-type') || '';

    // If the server returned a JSON error payload instead of a binary file
    if (!response.ok || contentType.includes('application/json')) {
      let errorPayload: any = null;
      try {
        errorPayload = await response.json();
      } catch {
        // ignore
      }
      const { message, code, details } = extractErrorMessage(errorPayload, response.statusText, response.status);
      throw new ApiError(message, response.status, code, details, false);
    }

    const blob = await response.blob();
    if (blob.size === 0) {
      throw new ApiError('Server returned an empty report file.', response.status, 'EMPTY_FILE');
    }

    const disposition = response.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/i);
    const defaultExt = endpoint.includes('pdf') ? 'pdf' : 'csv';
    const filename = match?.[1] || `maizecare-report-${new Date().toISOString().slice(0, 10)}.${defaultExt}`;

    return { blob, filename };
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      `Unable to download report from ${getApiBaseUrl()}. Ensure the Flask backend is reachable.`,
      0,
      'NETWORK_ERROR',
      undefined,
      true
    );
  }
}
