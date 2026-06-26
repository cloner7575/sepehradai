import { useEffect, useState } from 'react';
import { fetchItems } from '../api';
import { AppHeader } from '../components/AppHeader';
import { ItemCard } from '../components/ItemCard';
import { ItemsSection } from '../components/ItemsSection';
import { IconPackage } from '../components/Icons';
import type { CatalogItem } from '../types';

export function FlashSalePage() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems({ source: 'flash_sale', limit: 48 })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="pb-6 animate-fade-in">
      <AppHeader title="حراج ویژه" subtitle={!loading ? `${items.length} محصول` : undefined} />

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
            <p className="text-xs text-muted">به‌زودی پیشنهادهای ویژه اضافه می‌شود</p>
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
