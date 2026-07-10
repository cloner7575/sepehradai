import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { ItemCard } from '../components/ItemCard';
import { ItemsSection } from '../components/ItemsSection';
import { IconPackage } from '../components/Icons';
import type { CatalogItem, Category } from '../types';

export function CategoryPage() {
  const { slug } = useParams();
  const { adapter } = useApp();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [category, setCategory] = useState<Category | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    Promise.all([fetchItems({ category: slug }, adapter.initData || undefined), fetchCategories()])
      .then(([its, cats]) => {
        setItems(its);
        setCategory(cats.find((c) => c.slug === slug) || null);
      })
      .finally(() => setLoading(false));
  }, [slug, adapter.initData]);

  return (
    <div className="pb-6">
      <AppHeader
        title={category?.name || slug}
        subtitle={!loading ? `${items.length} مورد` : undefined}
      />

      <ItemsSection title="آیتم‌های این دسته" count={loading ? undefined : items.length}>
        {loading ? (
          <div className="items-grid">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-[4/5] rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconPackage className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">آیتمی در این دسته نیست</p>
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
