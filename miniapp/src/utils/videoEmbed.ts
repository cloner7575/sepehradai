import type { ItemMedia } from '../types';

export function isEmbeddableVideo(video: Pick<ItemMedia, 'url' | 'embed_url'>) {
  return Boolean(video.embed_url);
}

export function isExternalVideoPage(url: string) {
  return (
    url.includes('youtube.com') ||
    url.includes('youtu.be') ||
    url.includes('vimeo.com') ||
    url.includes('aparat.com')
  );
}
