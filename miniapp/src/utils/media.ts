import type { CatalogItem, ItemMedia, MediaType } from '../types';

export function getItemMedia(item: CatalogItem): ItemMedia[] {
  if (item.media?.length) return item.media;
  return (item.images || []).map((url, i) => ({
    id: i,
    type: 'image' as MediaType,
    url,
    title: '',
  }));
}

export function getItemImages(item: CatalogItem): string[] {
  const media = getItemMedia(item);
  const fromMedia = media.filter((m) => m.type === 'image').map((m) => m.url);
  const images = fromMedia.length ? fromMedia : (item.images || []);
  if (item.cover_url && !images.includes(item.cover_url)) {
    return [item.cover_url, ...images];
  }
  if (item.cover_url) return images;
  return images;
}

export function getItemVideos(item: CatalogItem): ItemMedia[] {
  return getItemMedia(item).filter((m) => m.type === 'video');
}

export function getItemFiles(item: CatalogItem): ItemMedia[] {
  return getItemMedia(item).filter((m) => m.type === 'file');
}

export function getItemThumbnail(item: CatalogItem): { type: MediaType; url: string } | null {
  if (item.cover_url) return { type: 'image', url: item.cover_url };
  const media = getItemMedia(item);
  const image = media.find((m) => m.type === 'image');
  if (image) return { type: 'image', url: image.url };
  const video = media.find((m) => m.type === 'video');
  if (video) return { type: 'video', url: video.url };
  return null;
}

export function fileNameFromUrl(url: string): string {
  try {
    const path = new URL(url, window.location.origin).pathname;
    return decodeURIComponent(path.split('/').pop() || 'فایل');
  } catch {
    return url.split('/').pop() || 'فایل';
  }
}
