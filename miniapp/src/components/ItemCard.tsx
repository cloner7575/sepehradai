import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';

export function ItemCard({ item }: { item: CatalogItem }) {
  const img = item.images[0];
  return (
    <Link to={`/item/${item.slug}`} className="card block">
      <div className="aspect-[4/3] bg-slate-100 relative overflow-hidden">
        {img ? (
          <img src={img} alt={item.title} className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl text-slate-300">📦</div>
        )}
        {item.is_featured && (
          <span className="absolute top-2 right-2 rounded-full bg-accent px-2 py-0.5 text-xs text-white">ویژه</span>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-semibold line-clamp-2">{item.title}</h3>
        {item.short_description && (
          <p className="mt-1 text-sm text-muted line-clamp-2">{item.short_description}</p>
        )}
        <p className="mt-2 text-sm font-bold text-primary">{formatPrice(item.price)}</p>
      </div>
    </Link>
  );
}
