import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';
import { ItemThumbnail } from './MediaGallery';

export function ItemCard({ item }: { item: CatalogItem }) {
  return (
    <Link to={`/item/${item.slug}`} className="product-card group block">
      <div className="product-card-media">
        <ItemThumbnail item={item} />
        {item.is_downloadable && (
          <span className="badge absolute top-2 right-2 bg-primary text-white">دانلود</span>
        )}
        {item.is_featured && !item.is_downloadable && (
          <span className="badge absolute top-2 right-2 bg-amber-500 text-white">ویژه</span>
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-bold leading-snug line-clamp-2">{item.title}</h3>
        {item.short_description && (
          <p className="mt-1 text-xs leading-relaxed text-muted line-clamp-2">{item.short_description}</p>
        )}
        <div className="mt-2.5">
          {item.is_downloadable ? (
            <span className="text-xs font-semibold text-primary">رایگان</span>
          ) : (
            <span className="price-tag">{formatPrice(item.price)}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
