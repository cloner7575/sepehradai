import { Link } from 'react-router-dom';
import type { Category } from '../types';
import { IconGrid } from './Icons';
import { SafeImage } from './SafeImage';

export function CategoryCard({ category }: { category: Category }) {
  return (
    <Link to={`/category/${category.slug}`} className="category-card">
      <div className="category-card-media">
        {category.image_url ? (
          <SafeImage
            src={category.image_url}
            className="h-full w-full object-cover"
            fallback={
              <div className="flex h-full items-center justify-center bg-[var(--color-primary-soft)] text-muted/40">
                <IconGrid className="h-8 w-8" />
              </div>
            }
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[var(--color-primary-soft)] text-muted/40">
            <IconGrid className="h-8 w-8" />
          </div>
        )}
        <div className="category-card-overlay" />
        <span className="category-card-title">{category.name}</span>
      </div>
    </Link>
  );
}
