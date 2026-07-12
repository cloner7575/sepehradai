import { useEffect, useMemo, useState } from 'react';
import { fetchItems } from '../api';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { CountdownBanner } from '../components/CountdownBanner';
import { ItemCard } from '../components/ItemCard';
import { ItemsSection } from '../components/ItemsSection';
import { IconPackage } from '../components/Icons';
import type { CatalogItem } from '../types';

function resolveFlashSaleEndsAt(items: CatalogItem[]): string | null {
  const times = items
    .map((item) => item.flash_sale_ends_at)
    .filter(Boolean)
    .map((value) => new Date(value!).getTime())
    .filter((value) => !Number.isNaN(value));
  if (!times.length) return null;
  return new Date(Math.max(...times)).toISOString();
}

export function FlashSalePage() {
  const { adapter, config } = useApp();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const accent = config?.theme?.accent_color || '#c2402f';

  useEffect(() => {
    fetchItems({ source: 'flash_sale', limit: 48 }, adapter.initData || undefined)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [adapter.initData]);

  const endsAt = useMemo(() => resolveFlashSaleEndsAt(items), [items]);

  return (
    <div className="pb-6 animate-fade-in">
      <AppHeader title="حراج ویژه" subtitle={!loading ? `${items.length} محصول` : undefined} />

      {!loading && endsAt && (
        <CountdownBanner title="زمان باقی‌مانده تا پایان حراج" endsAt={endsAt} accent={accent} />
      )}

      <ItemsSection title="محصولات حراج" count={loading ? undefined : items.length}>
        {loading ? (
          <div className="items-grid">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-[4/5] rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconPackage className="h-8 w-8 text-muted/40" />
            <p className="text-sm font-semibold">فعلاً محصولی در حراج نیست</p>
            <p className="text-xs text-muted">محصولات را از پنل با گزینه «قرارگیری در حراج» علامت بزنید</p>
          </div>
        ) : (
          <div className="items-grid">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </ItemsSection>
    </div>
  );
}
