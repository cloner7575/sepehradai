import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { ItemCard } from '../components/ItemCard';
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
      <section className="relative overflow-hidden rounded-b-3xl bg-gradient-to-br from-primary to-accent px-5 py-8 text-white">
        {config?.logo_url && (
          <img src={config.logo_url} alt="" className="mb-3 h-12 w-12 rounded-xl object-cover ring-2 ring-white/30" />
        )}
        <h1 className="text-2xl font-bold">{config?.hero_title || 'فروشگاه'}</h1>
        {config?.hero_subtitle && <p className="mt-2 text-sm text-white/85">{config.hero_subtitle}</p>}
      </section>

      <div className="px-4 pt-4">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="جستجو…"
            className="flex-1 rounded-2xl border border-slate-200 bg-surface px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button type="button" onClick={search} className="rounded-2xl bg-primary px-4 text-white">
            جستجو
          </button>
        </div>
      </div>

      {categories.length > 0 && (
        <section className="px-4 pt-5">
          <h2 className="mb-3 text-sm font-semibold text-muted">دسته‌بندی‌ها</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {categories.map((c) => (
              <Link
                key={c.id}
                to={`/category/${c.slug}`}
                className="card flex items-center gap-3 p-4"
              >
                <span className="text-2xl">{c.icon ? '' : '📁'}</span>
                <span className="font-medium">{c.name}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="px-4 pt-6">
        <h2 className="mb-3 text-sm font-semibold text-muted">همه آیتم‌ها</h2>
        {loading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton h-48" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="card p-8 text-center text-muted">آیتمی یافت نشد</div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
