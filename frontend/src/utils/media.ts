const DEFAULT_API_BASE_URL = 'http://127.0.0.1:5000';
const STORAGE_URL_OVERRIDE_KEY = 'maizecare_api_base_url_override';

export function getApiBaseUrl(): string {
  try {
    const override = localStorage.getItem(STORAGE_URL_OVERRIDE_KEY);
    if (override && override.trim().length > 0) {
      return override.trim().replace(/\/+$/, '');
    }
  } catch {
    // ignore storage access issues
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return DEFAULT_API_BASE_URL;
}

export function setApiBaseUrlOverride(url: string | null): void {
  try {
    if (!url || !url.trim()) {
      localStorage.removeItem(STORAGE_URL_OVERRIDE_KEY);
    } else {
      localStorage.setItem(STORAGE_URL_OVERRIDE_KEY, url.trim().replace(/\/+$/, ''));
    }
  } catch {
    // ignore
  }
}

/**
 * Resolves relative media URLs or heatmap filenames against the configured Flask backend base URL.
 * Rejects local server filesystem paths (such as Windows C:\ or D:\ paths or Linux /var/ paths).
 */
export function resolveMediaUrl(rawPath?: string | null, fallbackHeatmapFilename?: string | null): string | null {
  const baseUrl = getApiBaseUrl();

  const candidate = rawPath || (fallbackHeatmapFilename ? `/api/heatmaps/${encodeURIComponent(fallbackHeatmapFilename)}` : null);
  if (!candidate || typeof candidate !== 'string') {
    return null;
  }

  const trimmed = candidate.trim();
  if (!trimmed) return null;

  // Never expose local Windows or Unix filesystem paths as public URLs
  if (/^[a-zA-Z]:\\/.test(trimmed) || trimmed.includes('\\') || /^\/(home|var|tmp|Users|opt)\//.test(trimmed)) {
    // If it's a filesystem path ending with a filename inside heatmaps, extract only if safe, otherwise reject
    const heatmapMatch = trimmed.match(/heatmaps[/\\]([^/\\]+\.(?:png|jpg|jpeg|webp))$/i);
    if (heatmapMatch && heatmapMatch[1]) {
      return `${baseUrl}/api/heatmaps/${encodeURIComponent(heatmapMatch[1])}`;
    }
    return null;
  }

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return trimmed;
  }

  if (trimmed.startsWith('/')) {
    return `${baseUrl}${trimmed}`;
  }

  return `${baseUrl}/${trimmed}`;
}

export function formatConfidence(confidence?: number | null): string {
  if (confidence === undefined || confidence === null || Number.isNaN(Number(confidence))) {
    return '—';
  }
  const num = Number(confidence);
  const percentage = num <= 1 ? num * 100 : num;
  return `${percentage.toFixed(1)}%`;
}

export function normalizeConfidencePercent(confidence?: number | null): number {
  if (confidence === undefined || confidence === null || Number.isNaN(Number(confidence))) {
    return 0;
  }
  const num = Number(confidence);
  return Math.max(0, Math.min(100, num <= 1 ? num * 100 : num));
}

export function formatDateTime(isoString?: string | null): string {
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
