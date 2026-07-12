import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchLibrary } from '../api';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { IconBook, IconLock, IconPackage, IconPlay } from '../components/Icons';
import { SafeImage } from '../components/SafeImage';
import { itemTypeLabel } from '../utils/itemType';
import type { CatalogItem } from '../types';

function LibraryItemCard({ item }: { item: CatalogItem }) {
  const image = item.images[0] || item.cover_url;
  const isCourse = item.item_type === 'course';
  const isPackage = item.item_type === 'package';
  const FallbackIcon = isCourse ? IconBook : isPackage ? IconPackage : IconPlay;
  return (
    <Link to={`/item/${item.slug}`} className="card flex gap-3 p-3.5 transition active:scale-[0.98]">
      <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-[var(--color-primary-soft)]">
        {image ? (
          <SafeImage src={image} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-primary/40">
            <FallbackIcon className="h-7 w-7" />
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs text-muted">{itemTypeLabel(item.item_type)}</div>
        <div className="truncate font-semibold">{item.title}</div>
        {item.short_description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted">{item.short_description}</p>
        )}
      </div>
    </Link>
  );
}

export function LibraryPage() {
  const { adapter } = useApp();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!adapter.initData) {
      setError('برای مشاهده کتابخانه باید از داخل بله/تلگرام وارد شوید.');
      setLoading(false);
      return;
    }
    fetchLibrary(adapter.initData)
      .then(setItems)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [adapter.initData]);

  return (
    <div className="pb-8">
      <AppHeader title="کتابخانه من" showBrand={false} showCart showLibrary={false} />
      {loading && (
        <div className="space-y-3 p-4">
          <div className="skeleton h-20 rounded-2xl" />
          <div className="skeleton h-20 rounded-2xl" />
        </div>
      )}
      {!loading && error && (
        <div className="empty-state mx-4 mt-8">
          <IconLock className="h-8 w-8 text-muted/40" />
          <p className="text-sm text-muted">{error}</p>
        </div>
      )}
      {!loading && !error && items.length === 0 && (
        <div className="empty-state mx-4 mt-8">
          <IconBook className="h-8 w-8 text-muted/40" />
          <p className="text-sm text-muted">هنوز دوره یا پکیجی در کتابخانه شما نیست.</p>
        </div>
      )}
      {!loading && !error && items.length > 0 && (
        <div className="space-y-3 p-4">
          {items.map((item) => (
            <LibraryItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
