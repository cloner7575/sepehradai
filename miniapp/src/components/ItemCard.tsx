import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';
import { IconPackage } from './Icons';

export function ItemCard({ item }: { item: CatalogItem }) {
  const img = item.images[0];
  return (
    <Link to={`/item/${item.slug}`} className="card-interactive group block">
      <div className="relative aspect-square overflow-hidden bg-[var(--color-primary-soft)]">
        {img ? (
          <img
            src={img}
            alt={item.title}
            className="h-full w-full object-cover transition duration-300 group-active:scale-[1.02]"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted/30">
            <IconPackage className="h-10 w-10" />
          </div>
        )}
        {item.is_featured && (
          <span className="badge absolute top-2.5 right-2.5 bg-primary text-white">ویژه</span>
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-semibold leading-snug line-clamp-2">{item.title}</h3>
        {item.short_description && (
          <p className="mt-1 text-xs leading-relaxed text-muted line-clamp-2">{item.short_description}</p>
        )}
        <p className="price-tag mt-2">{formatPrice(item.price)}</p>
      </div>
    </Link>
  );
}
