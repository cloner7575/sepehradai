let mediaBaseUrl = '';

function ensureHttps(url: string): string {
  if (!url.startsWith('http://')) return url;
  try {
    const host = new URL(url).hostname.toLowerCase();
    if (host === 'localhost' || host === '127.0.0.1') return url;
  } catch {
    /* ignore */
  }
  return `https://${url.slice(7)}`;
}

export function setMediaBaseUrl(base: string) {
  mediaBaseUrl = ensureHttps((base || '').replace(/\/$/, ''));
}

export function getMediaBaseUrl() {
  return mediaBaseUrl;
}

export function resolveMediaUrl(url: string): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return ensureHttps(url);
  }
  const path = url.startsWith('/') ? url : `/${url}`;
  const base =
    mediaBaseUrl ||
    (typeof window !== 'undefined' ? window.location.origin.replace(/\/$/, '') : '');
  return ensureHttps(`${base}${path}`);
}
