import type { CatalogItem, GroupMember, ItemMedia } from '../types';
import { getItemFiles, getItemVideos, fileNameFromUrl } from '../utils/media';
import { IconDownload, IconFile, IconLock, IconPlay } from './Icons';
import { useApp } from '../App';

type ContentSource = Pick<
  CatalogItem,
  'media' | 'download_url' | 'is_downloadable' | 'has_access' | 'requires_access'
> | GroupMember;

function isExternalVideo(url: string) {
  return url.includes('youtube.com') || url.includes('youtu.be') || url.includes('vimeo.com');
}

function VideoBlock({ video, poster }: { video: ItemMedia; poster?: string }) {
  const { adapter } = useApp();

  if (video.locked || !video.url) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-neutral-900">
        <div className="flex h-full flex-col items-center justify-center gap-2 text-white/90">
          <IconLock className="h-8 w-8" />
          <span className="text-xs">پس از خرید قابل مشاهده</span>
        </div>
      </div>
    );
  }

  if (isExternalVideo(video.url)) {
    return (
      <button
        type="button"
        className="flex aspect-video w-full items-center justify-center gap-2 rounded-xl bg-neutral-900 text-white"
        onClick={() => adapter.openLink(video.url)}
      >
        <IconPlay className="h-10 w-10" />
        <span className="text-sm font-medium">پخش در مرورگر</span>
      </button>
    );
  }

  return (
    <video
      src={video.url}
      controls
      playsInline
      preload="metadata"
      className="aspect-video w-full rounded-xl bg-black"
      poster={poster}
    >
      مرورگر شما از پخش ویدیو پشتیبانی نمی‌کند.
    </video>
  );
}

function FileRow({ file }: { file: ItemMedia }) {
  const { adapter } = useApp();

  if (file.locked || !file.url) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border bg-[var(--color-bg)] px-3 py-3 opacity-80">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-neutral-100 text-muted">
          <IconLock className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1 truncate text-sm font-medium text-muted">
          {file.title || 'فایل قفل‌شده'}
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface px-3 py-3 text-right transition active:scale-[0.99]"
      onClick={() => adapter.openLink(file.url)}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-primary">
        <IconFile className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold">{file.title || fileNameFromUrl(file.url)}</div>
      </div>
      <IconDownload className="h-4 w-4 shrink-0 text-primary" />
    </button>
  );
}

export function InlineContentPanel({ source }: { source: ContentSource }) {
  const { adapter } = useApp();
  const itemLike = {
    media: source.media || [],
    download_url: 'download_url' in source ? source.download_url || '' : '',
    is_downloadable: Boolean(source.is_downloadable),
    has_access: 'has_access' in source ? source.has_access : true,
    requires_access: 'requires_access' in source ? source.requires_access : false,
  };
  const videos = getItemVideos(itemLike as CatalogItem);
  const files = getItemFiles(itemLike as CatalogItem);
  const showMainDownload = Boolean(itemLike.is_downloadable && itemLike.download_url);

  if (!videos.length && !files.length && !showMainDownload) {
    return null;
  }

  return (
    <div className="space-y-3">
      {videos.map((video) => (
        <div key={video.id}>
          <VideoBlock video={video} />
          {video.title && <p className="mt-1.5 text-xs font-medium text-muted">{video.title}</p>}
        </div>
      ))}

      {showMainDownload && (
        <button
          type="button"
          className="btn-primary !py-3"
          onClick={() => adapter.openLink(itemLike.download_url)}
        >
          <span className="inline-flex items-center justify-center gap-2">
            <IconDownload className="h-4 w-4" />
            دانلود فایل
          </span>
        </button>
      )}

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file) => (
            <FileRow key={file.id} file={file} />
          ))}
        </div>
      )}
    </div>
  );
}
