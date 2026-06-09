import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { AppHeader } from '../components/AppHeader';
import { ItemCard } from '../components/ItemCard';
import { IconPackage } from '../components/Icons';
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
    <div className="pb-6">
      <AppHeader
        title={category?.name || slug}
        subtitle={!loading ? `${items.length} مورد` : undefined}
      />

      <div className="px-4 pt-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton aspect-square rounded-2xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <IconPackage className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">آیتمی در این دسته نیست</p>
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
