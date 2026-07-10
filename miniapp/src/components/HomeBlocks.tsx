import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCategories, fetchItems } from '../api';
import { useApp } from '../App';
import type {
  CatalogItem,
  Category,
  HomeBlock,
  ProductsHomeBlock,
  SliderHomeBlock,
} from '../types';
import { CategoryCard } from './CategoryCard';
import { IconCart, IconGrid, IconSearch } from './Icons';
import { ItemCard } from './ItemCard';
import { ItemsSection } from './ItemsSection';
import { SafeImage } from './SafeImage';
import { BlockRenderer } from './HomeBlockExtras';
import { resolveMediaUrl } from '../utils/url';

interface HomeBlocksProps {
  blocks: HomeBlock[];
  searchInput: string;
  searchQuery: string;
  onSearchInputChange: (value: string) => void;
  onSearch: () => void;
  searchLoading: boolean;
}

function HeroBlockView({ block }: { block: HomeBlock }) {
  const { config, cartItems } = useApp();
  const cartCount = cartItems.reduce((s, l) => s + l.quantity, 0);
  const shopEnabled = config?.is_enabled !== false;
  const variant = block.type === 'hero' ? block.variant || 'banner' : 'banner';
  const primary = config?.theme?.primary_color || '#334155';
  const heroBackground = resolveMediaUrl(config?.hero_background_url || '');

  if (variant === 'compact') {
    return (
      <header className="app-header">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {config?.logo_url ? (
            <SafeImage
              src={config.logo_url}
              className="h-10 w-10 shrink-0 rounded-2xl object-cover ring-1 ring-border"
              fallback={
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-primary">
                  <IconGrid className="h-4 w-4" />
                </div>
              }
            />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-primary">
              <IconGrid className="h-4 w-4" />
            </div>
          )}
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold tracking-tight">
              {config?.hero_title || 'ویترین'}
            </h1>
            {config?.hero_subtitle && (
              <p className="truncate text-[11px] text-muted">{config.hero_subtitle}</p>
            )}
          </div>
        </div>
        {shopEnabled && (
          <Link to="/cart" className="cart-header-btn" aria-label="سبد خرید">
            <IconCart className="h-5 w-5" />
            {cartCount > 0 && (
              <span className="cart-header-badge">{cartCount > 99 ? '99+' : cartCount}</span>
            )}
          </Link>
        )}
      </header>
    );
  }

  return (
    <section
      className="home-hero-banner relative mx-4 mt-4 overflow-hidden rounded-3xl px-4 py-5 text-white"
      style={
        heroBackground
          ? {
              backgroundImage: `linear-gradient(to top, rgba(15,23,42,0.82), rgba(15,23,42,0.35)), url(${heroBackground})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }
          : {
              background: `linear-gradient(135deg, ${primary}, color-mix(in srgb, ${primary} 72%, #000))`,
            }
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {config?.logo_url ? (
            <SafeImage
              src={config.logo_url}
              className="h-12 w-12 shrink-0 rounded-2xl object-cover ring-2 ring-white/20"
              fallback={
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15">
                  <IconGrid className="h-5 w-5" />
                </div>
              }
            />
          ) : (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/15">
              <IconGrid className="h-5 w-5" />
            </div>
          )}
          <div className="min-w-0">
            <h1 className="truncate text-lg font-bold">{config?.hero_title || 'ویترین'}</h1>
            {config?.hero_subtitle && (
              <p className="mt-0.5 truncate text-xs text-white/85">{config.hero_subtitle}</p>
            )}
          </div>
        </div>
        {shopEnabled && (
          <Link
            to="/cart"
            className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/20"
            aria-label="سبد خرید"
          >
            <IconCart className="h-5 w-5" />
            {cartCount > 0 && (
              <span className="cart-header-badge">{cartCount > 99 ? '99+' : cartCount}</span>
            )}
          </Link>
        )}
      </div>
    </section>
  );
}

function SearchBlockView({
  block,
  searchInput,
  onSearchInputChange,
  onSearch,
}: {
  block: HomeBlock;
  searchInput: string;
  onSearchInputChange: (value: string) => void;
  onSearch: () => void;
}) {
  const placeholder = block.type === 'search' ? block.placeholder || 'جستجو…' : 'جستجو…';
  return (
    <div className="px-4 pt-4">
      <div className="relative">
        <IconSearch className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          value={searchInput}
          onChange={(e) => onSearchInputChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          placeholder={placeholder}
          className="input-field pr-11"
        />
      </div>
    </div>
  );
}

function SliderBlockView({ block }: { block: SliderHomeBlock }) {
  const slides = block.slides || [];
  if (!slides.length) return null;

  return (
    <section className="px-4 pt-4">
      <div className="home-slider-track flex gap-3 overflow-x-auto pb-1">
        {slides.map((slide, index) => {
          const imageUrl = resolveMediaUrl(slide.image_url || '');
          const inner = (
            <div
              className="home-slider-slide relative min-h-[9rem] w-full overflow-hidden rounded-2xl bg-primary p-4 text-white"
              style={
                imageUrl
                  ? {
                      backgroundImage: `linear-gradient(to top, rgba(15,23,42,0.78), rgba(15,23,42,0.2)), url(${imageUrl})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    }
                  : undefined
              }
            >
              <div className="relative z-10 flex h-full min-h-[7rem] flex-col justify-end gap-1">
                {slide.title && <strong className="text-sm">{slide.title}</strong>}
                {slide.subtitle && <span className="text-xs text-white/85">{slide.subtitle}</span>}
              </div>
            </div>
          );
          const slideKey = `${block.id}-${index}`;
          if (slide.link_url) {
            return (
              <a
                key={slideKey}
                href={slide.link_url}
                target="_blank"
                rel="noreferrer"
                className="block w-[82%] shrink-0 snap-start"
              >
                {inner}
              </a>
            );
          }
          return (
            <div key={slideKey} className="w-[82%] shrink-0 snap-start">
              {inner}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CategoriesBlockView({ block }: { block: HomeBlock }) {
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    fetchCategories()
      .then((cats) => setCategories(cats.filter((c) => !c.parent_id)))
      .catch(() => setCategories([]));
  }, []);

  if (block.type !== 'categories') return null;
  const limit = block.limit || 8;
  const columns = block.columns === 3 ? 3 : 2;
  const list = categories.slice(0, limit);
  if (!list.length) return null;

  return (
    <section className="px-4 pt-6">
      <h2 className="section-title mb-3">{block.title || 'دسته‌بندی‌ها'}</h2>
      <div className={columns === 3 ? 'grid grid-cols-3 gap-3' : 'grid grid-cols-2 gap-3'}>
        {list.map((c) => (
          <CategoryCard key={c.id} category={c} />
        ))}
      </div>
    </section>
  );
}

function FeaturedBlockView({ block }: { block: HomeBlock }) {
  const { adapter } = useApp();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (block.type !== 'featured') return;
    setLoading(true);
    fetchItems({ featured: true }, adapter.initData || undefined)
      .then((list) => setItems(list.slice(0, block.limit || 6)))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [block.type, block.id, block.limit, adapter.initData]);

  if (block.type !== 'featured') return null;
  if (!loading && !items.length) return null;

  const layout = block.layout === 'grid' ? 'grid' : 'scroll';

  return (
    <ItemsSection title={block.title || 'محصولات ویژه'} count={loading ? undefined : items.length}>
      {loading ? (
        <div className="flex gap-3 overflow-x-auto">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-36 w-36 shrink-0 rounded-2xl" />
          ))}
        </div>
      ) : layout === 'scroll' ? (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {items.map((item) => (
            <div key={item.id} className="w-40 shrink-0">
              <ItemCard item={item} compact />
            </div>
          ))}
        </div>
      ) : (
        <div className="items-grid">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </ItemsSection>
  );
}

function ProductsBlockView({
  block,
  items,
  loading,
}: {
  block: ProductsHomeBlock;
  items: CatalogItem[];
  loading: boolean;
}) {
  const { config } = useApp();
  const layout = block.layout || config?.theme?.layout || 'grid';
  const limit = block.limit || 0;
  const list = limit > 0 ? items.slice(0, limit) : items;

  return (
    <ItemsSection title={block.title || 'همه محصولات'} count={loading ? undefined : list.length}>
      {loading ? (
        <div className={layout === 'list' ? 'flex flex-col gap-3' : 'items-grid'}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={`skeleton rounded-2xl ${layout === 'list' ? 'h-24' : 'aspect-[4/5]'}`}
            />
          ))}
        </div>
      ) : list.length === 0 ? (
        <div className="empty-state">
          <IconSearch className="h-8 w-8 text-muted/40" />
          <p className="text-sm text-muted">موردی یافت نشد</p>
        </div>
      ) : layout === 'list' ? (
        <div className="flex flex-col gap-3">
          {list.map((item) => (
            <ItemCard key={item.id} item={item} layout="list" />
          ))}
        </div>
      ) : (
        <div className="items-grid">
          {list.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </ItemsSection>
  );
}

function SpacerBlockView({ block }: { block: HomeBlock }) {
  if (block.type !== 'spacer') return null;
  const size = block.size || 'md';
  const height = size === 'sm' ? '0.75rem' : size === 'lg' ? '2rem' : '1.25rem';
  return <div aria-hidden style={{ height }} />;
}

export function HomeBlocks({
  blocks,
  searchInput,
  searchQuery,
  onSearchInputChange,
  onSearch,
  searchLoading,
}: HomeBlocksProps) {
  const { adapter } = useApp();
  const hasProductsBlock = useMemo(
    () => blocks.some((b) => b.type === 'products'),
    [blocks],
  );
  const [productItems, setProductItems] = useState<CatalogItem[]>([]);
  const [productsLoading, setProductsLoading] = useState(hasProductsBlock);

  useEffect(() => {
    if (!hasProductsBlock) return;
    setProductsLoading(true);
    const params = searchQuery.trim() ? { q: searchQuery.trim() } : undefined;
    fetchItems(params, adapter.initData || undefined)
      .then(setProductItems)
      .finally(() => setProductsLoading(false));
  }, [hasProductsBlock, searchQuery, adapter.initData]);

  return (
    <>
      {blocks.map((block, index) => {
        const prevType = index > 0 ? blocks[index - 1].type : null;
        const afterHero = block.type === 'story_bar' && prevType === 'hero';
        switch (block.type) {
          case 'hero':
            return <HeroBlockView key={block.id} block={block} />;
          case 'search':
            return (
              <SearchBlockView
                key={block.id}
                block={block}
                searchInput={searchInput}
                onSearchInputChange={onSearchInputChange}
                onSearch={onSearch}
              />
            );
          case 'slider':
            return <SliderBlockView key={block.id} block={block} />;
          case 'categories':
            return <CategoriesBlockView key={block.id} block={block} />;
          case 'featured':
            return <FeaturedBlockView key={block.id} block={block} />;
          case 'products':
            return (
              <ProductsBlockView
                key={block.id}
                block={block}
                items={productItems}
                loading={productsLoading || searchLoading}
              />
            );
          case 'spacer':
            return <SpacerBlockView key={block.id} block={block} />;
          case 'announcement_bar':
          case 'story_bar':
          case 'countdown':
          case 'coupon':
          case 'product_carousel':
          case 'banner_grid':
          case 'video':
          case 'testimonials':
          case 'trust_badges':
          case 'faq':
          case 'info':
          case 'bundle':
          case 'rich_text':
            return <BlockRenderer key={block.id} block={block} afterHero={afterHero} />;
          default:
            return null;
        }
      })}
    </>
  );
}
