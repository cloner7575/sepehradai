import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';
import { ItemThumbnail } from './MediaGallery';
import { itemTypeLabel } from '../utils/itemType';

export function ItemCard({
  item,
  compact = false,
  layout = 'grid',
}: {
  item: CatalogItem;
  compact?: boolean;
  layout?: 'grid' | 'list';
}) {
  const typeLabel = itemTypeLabel(item.item_type);

  if (layout === 'list') {
    return (
      <Link
        to={`/item/${item.slug}`}
        className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-3 transition active:scale-[0.99]"
      >
        <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-[var(--color-primary-soft)]">
          <ItemThumbnail item={item} />
        </div>
        <div className="min-w-0 flex-1">
          <span className="item-type-chip">{typeLabel}</span>
          <h3 className="mt-1 text-sm font-bold leading-snug line-clamp-2">{item.title}</h3>
          <div className="mt-1">
            {item.is_downloadable ? (
              <span className="text-xs font-semibold text-primary">رایگان</span>
            ) : item.price ? (
              <span className="price-tag">{formatPrice(item.price)}</span>
            ) : (
              <span className="text-xs font-medium text-muted">تماس بگیرید</span>
            )}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link to={`/item/${item.slug}`} className="product-card group block">
      <div className={`product-card-media ${compact ? 'aspect-square' : ''}`}>
        <ItemThumbnail item={item} />
        <div className="product-card-badges">
          {item.is_downloadable ? (
            <span className="badge bg-primary text-white">دانلود</span>
          ) : item.is_featured ? (
            <span className="badge bg-amber-500 text-white">ویژه</span>
          ) : null}
        </div>
      </div>
      <div className={`product-card-body ${compact ? 'p-2.5' : ''}`}>
        {!compact && <span className="item-type-chip">{typeLabel}</span>}
        <h3 className={`product-card-title ${compact ? 'text-xs' : ''}`}>{item.title}</h3>
        {!compact && item.short_description && (
          <p className="product-card-desc">{item.short_description}</p>
        )}
        <div className="product-card-footer">
          {item.is_downloadable ? (
            <span className="text-xs font-semibold text-primary">رایگان</span>
          ) : item.price ? (
            <span className="price-tag">{formatPrice(item.price)}</span>
          ) : (
            <span className="text-xs font-medium text-muted">تماس بگیرید</span>
          )}
          {!compact && <span className="product-card-cta">مشاهده</span>}
        </div>
      </div>
    </Link>
  );
}
