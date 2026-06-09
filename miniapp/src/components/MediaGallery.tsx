import { useState } from 'react';
import type { CatalogItem } from '../types';
import { getItemFiles, getItemImages, getItemVideos } from '../utils/media';
import { IconDownload, IconFile, IconPackage, IconPlay } from './Icons';
import { fileNameFromUrl } from '../utils/media';
import { SafeImage } from './SafeImage';

export function MediaGallery({ item }: { item: CatalogItem }) {
  const images = getItemImages(item);
  const videos = getItemVideos(item);
  const files = getItemFiles(item);
  const [imgIdx, setImgIdx] = useState(0);

  const hasVisual = images.length > 0 || videos.length > 0;

  return (
    <div className="space-y-4">
      {images.length > 0 && (
        <div className="relative aspect-[4/3] bg-[var(--color-primary-soft)]">
          <SafeImage
            src={images[imgIdx]}
            className="h-full w-full object-cover"
            fallback={
              <div className="flex h-full items-center justify-center text-muted/30">
                <IconPackage className="h-16 w-16" />
              </div>
            }
          />
          {images.length > 1 && (
            <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-1.5">
              {images.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setImgIdx(i)}
                  className={`h-1.5 rounded-full transition-all ${
                    i === imgIdx ? 'w-5 bg-white' : 'w-1.5 bg-white/50'
                  }`}
                  aria-label={`تصویر ${i + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {videos.map((video) => (
        <div key={video.id} className="overflow-hidden rounded-2xl border border-border bg-black">
          <video
            src={video.url}
            controls
            playsInline
            preload="metadata"
            className="aspect-video w-full"
            poster={images[0]}
          >
            مرورگر شما از پخش ویدیو پشتیبانی نمی‌کند.
          </video>
        </div>
      ))}

      {files.length > 0 && !item.is_downloadable && (
        <div>
          <div className="section-title mb-3">فایل‌های قابل دانلود</div>
          <div className="space-y-2">
            {files.map((file) => (
              <a
                key={file.id}
                href={file.url}
                target="_blank"
                rel="noopener noreferrer"
                download
                className="card flex items-center gap-3 p-3.5 transition active:scale-[0.98]"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-primary">
                  <IconFile className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1 truncate text-sm font-semibold">
                  {file.title || fileNameFromUrl(file.url)}
                </div>
                <IconDownload className="h-4 w-4 shrink-0 text-muted" />
              </a>
            ))}
          </div>
        </div>
      )}

      {!hasVisual && files.length === 0 && (
        <div className="flex aspect-[4/3] items-center justify-center bg-[var(--color-primary-soft)] text-muted/30">
          <IconPackage className="h-16 w-16" />
        </div>
      )}
    </div>
  );
}

export function ItemThumbnail({ item }: { item: CatalogItem }) {
  const images = getItemImages(item);
  const videos = getItemVideos(item);

  if (item.is_downloadable && !images[0]) {
    return (
      <div className="flex h-full items-center justify-center bg-[var(--color-primary-soft)] text-primary/50">
        <IconDownload className="h-9 w-9" />
      </div>
    );
  }

  if (images[0]) {
    return (
      <SafeImage
        src={images[0]}
        className="h-full w-full object-cover transition duration-300 group-active:scale-[1.02]"
        fallback={
          <div className="flex h-full items-center justify-center text-muted/30">
            <IconPackage className="h-9 w-9" />
          </div>
        }
      />
    );
  }

  if (videos[0]) {
    return (
      <div className="relative h-full w-full bg-neutral-900">
        <div className="flex h-full items-center justify-center text-white/80">
          <IconPlay className="h-9 w-9" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center text-muted/25">
      <IconPackage className="h-9 w-9" />
    </div>
  );
}
