import { Link } from 'react-router-dom';
import type { CatalogItem } from '../types';
import { formatPrice } from '../api';
import { ItemThumbnail } from './MediaGallery';
import { itemTypeLabel } from '../utils/itemType';

export function ItemCard({ item }: { item: CatalogItem }) {
  const typeLabel = itemTypeLabel(item.item_type);

  return (
    <Link to={`/item/${item.slug}`} className="product-card group block">
      <div className="product-card-media">
        <ItemThumbnail item={item} />
        <div className="product-card-badges">
          {item.is_downloadable ? (
            <span className="badge bg-primary text-white">دانلود</span>
          ) : item.is_featured ? (
            <span className="badge bg-amber-500 text-white">ویژه</span>
          ) : null}
        </div>
      </div>
      <div className="product-card-body">
        <span className="item-type-chip">{typeLabel}</span>
        <h3 className="product-card-title">{item.title}</h3>
        {item.short_description && (
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
          <span className="product-card-cta">مشاهده</span>
        </div>
      </div>
    </Link>
  );
}
