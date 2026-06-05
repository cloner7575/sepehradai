import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchItems } from '../api';
import { ItemCard } from '../components/ItemCard';
import type { CatalogItem } from '../types';

export function CategoryPage() {
  const { slug } = useParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    fetchItems({ category: slug })
      .then(setItems)
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="px-4 py-4 pb-24">
      <h1 className="mb-4 text-xl font-bold">دسته: {slug}</h1>
      {loading ? (
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-48" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-8 text-center text-muted">آیتمی در این دسته نیست</div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
