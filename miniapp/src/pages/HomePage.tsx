import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { ItemCard } from '../components/ItemCard';
import { IconGrid, IconSearch } from '../components/Icons';
import type { Category, CatalogItem } from '../types';
import { useApp } from '../App';

export function HomePage() {
  const { config } = useApp();
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
    <div className="pb-24">
      <header className="page-header px-5 py-5">
        <div className="flex items-center gap-3">
          {config?.logo_url ? (
            <img
              src={config.logo_url}
              alt=""
              className="h-11 w-11 shrink-0 rounded-xl border border-border object-cover"
            />
          ) : (
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-primary">
              <IconGrid className="h-5 w-5" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-bold tracking-tight">
              {config?.hero_title || 'فروشگاه'}
            </h1>
            {config?.hero_subtitle && (
              <p className="mt-0.5 truncate text-xs text-muted">{config.hero_subtitle}</p>
            )}
          </div>
        </div>
      </header>

      <div className="px-4 pt-4">
        <div className="relative">
          <IconSearch className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="جستجوی محصول…"
            className="input-field pr-10"
          />
        </div>
      </div>

      {categories.length > 0 && (
        <section className="px-4 pt-6">
          <h2 className="section-title mb-3">دسته‌بندی‌ها</h2>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
            {categories.map((c) => (
              <Link
                key={c.id}
                to={`/category/${c.slug}`}
                className="shrink-0 rounded-full border border-border bg-surface px-4 py-2 text-sm font-medium transition active:scale-95 active:bg-[var(--color-primary-soft)]"
              >
                {c.name}
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="px-4 pt-6">
        <h2 className="section-title mb-3">محصولات</h2>
        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-[3/4] rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconSearch className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">محصولی یافت نشد</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
