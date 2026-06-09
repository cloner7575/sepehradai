import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';
import { ItemThumbnail } from './MediaGallery';

export function ItemCard({ item }: { item: CatalogItem }) {
  return (
    <Link to={`/item/${item.slug}`} className="card-interactive group block">
      <div className="relative aspect-square overflow-hidden bg-[var(--color-primary-soft)]">
        <ItemThumbnail item={item} />
        {item.is_downloadable && (
          <span className="badge absolute top-2.5 right-2.5 bg-primary text-white">دانلود</span>
        )}
        {item.is_featured && !item.is_downloadable && (
          <span className="badge absolute top-2.5 right-2.5 bg-primary text-white">ویژه</span>
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-semibold leading-snug line-clamp-2">{item.title}</h3>
        {item.short_description && (
          <p className="mt-1 text-xs leading-relaxed text-muted line-clamp-2">{item.short_description}</p>
        )}
        {item.is_downloadable ? (
          <p className="mt-2 text-xs font-semibold text-primary">فایل رایگان</p>
        ) : (
          <p className="price-tag mt-2">{formatPrice(item.price)}</p>
        )}
      </div>
    </Link>
  );
}
