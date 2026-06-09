import { useEffect, useState } from 'react';
import { fetchCategories, fetchItems } from '../api';
import { AppHeader } from '../components/AppHeader';
import { CategoryCard } from '../components/CategoryCard';
import { ItemCard } from '../components/ItemCard';
import { ItemsSection } from '../components/ItemsSection';
import { IconSearch } from '../components/Icons';
import type { Category, CatalogItem } from '../types';

export function HomePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchCategories(), fetchItems()])
      .then(([cats, its]) => {
        setCategories(cats.filter((c) => !c.parent_id));
        setItems(its);
      })
      .finally(() => setLoading(false));
  }, []);

  const search = () => {
    setLoading(true);
    fetchItems({ q }).then(setItems).finally(() => setLoading(false));
  };

  return (
    <div className="pb-6">
      <AppHeader showBrand />

      <div className="px-4 pt-4">
        <div className="relative">
          <IconSearch className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="جستجو در فروشگاه…"
            className="input-field pr-11"
          />
        </div>
      </div>

      {categories.length > 0 && (
        <section className="px-4 pt-6">
          <h2 className="section-title mb-3">دسته‌بندی‌ها</h2>
          <div className="grid grid-cols-2 gap-3">
            {categories.map((c) => (
              <CategoryCard key={c.id} category={c} />
            ))}
          </div>
        </section>
      )}

      <ItemsSection title="آیتم‌ها" count={loading ? undefined : items.length}>
        {loading ? (
          <div className="items-grid">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-[4/5] rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconSearch className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">موردی یافت نشد</p>
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
