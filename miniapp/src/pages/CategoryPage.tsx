import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { ItemCard } from '../components/ItemCard';
import { IconGrid, IconPackage } from '../components/Icons';
import type { CatalogItem, Category } from '../types';

export function CategoryPage() {
  const { slug } = useParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [category, setCategory] = useState<Category | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    Promise.all([fetchItems({ category: slug }), fetchCategories()])
      .then(([its, cats]) => {
        setItems(its);
        setCategory(cats.find((c) => c.slug === slug) || null);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="pb-24">
      <header className="page-header px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl border border-border bg-[var(--color-primary-soft)]">
            {category?.image_url ? (
              <img src={category.image_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-muted/30">
                <IconGrid className="h-5 w-5" />
              </div>
            )}
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">{category?.name || slug}</h1>
            {!loading && (
              <p className="mt-0.5 text-xs text-muted">{items.length} آیتم</p>
            )}
          </div>
        </div>
      </header>

      <div className="px-4 pt-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-[3/4] rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconPackage className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">محصولی در این دسته وجود ندارد</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
