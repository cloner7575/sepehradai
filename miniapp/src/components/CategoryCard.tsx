import { Link } from 'react-router-dom';
import type { Category } from '../types';
import { IconGrid } from './Icons';

export function CategoryCard({ category }: { category: Category }) {
  return (
    <Link
      to={`/category/${category.slug}`}
      className="card-interactive shrink-0 w-28 overflow-hidden"
    >
      <div className="aspect-square bg-[var(--color-primary-soft)]">
        {category.image_url ? (
          <img
            src={category.image_url}
            alt={category.name}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted/30">
            <IconGrid className="h-8 w-8" />
          </div>
        )}
      </div>
      <div className="px-2 py-2.5 text-center">
        <span className="line-clamp-2 text-xs font-semibold leading-snug">{category.name}</span>
      </div>
    </Link>
  );
}
