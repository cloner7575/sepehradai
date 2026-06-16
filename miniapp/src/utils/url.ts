let mediaBaseUrl = '';

export function setMediaBaseUrl(base: string) {
  mediaBaseUrl = (base || '').replace(/\/$/, '');
}

export function getMediaBaseUrl() {
  return mediaBaseUrl;
}

export function resolveMediaUrl(url: string): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const path = url.startsWith('/') ? url : `/${url}`;
  const base =
    mediaBaseUrl ||
    (typeof window !== 'undefined' ? window.location.origin.replace(/\/$/, '') : '');
  return `${base}${path}`;
}
