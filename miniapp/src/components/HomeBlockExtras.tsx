import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchItems, formatPrice, updateCart } from '../api';
import { useApp } from '../App';
import type {
  AnnouncementBarBlock,
  BannerGridBlock,
  BundleBlock,
  CountdownBlock,
  CouponBlock,
  FaqBlock,
  HomeBlock,
  InfoBlock,
  ProductCarouselBlock,
  RichTextBlock,
  StoryBarBlock,
  TestimonialsBlock,
  TrustBadgesBlock,
  VideoBlock,
} from '../types';
import { ItemCard } from './ItemCard';
import { CopyButton } from './CopyButton';
import { ItemsSection } from './ItemsSection';
import { SafeImage } from './SafeImage';
import { resolveMediaUrl } from '../utils/url';
import { CountdownBanner } from './CountdownBanner';
import { StoryViewer, resolveStorySlides } from './StoryViewer';

function useBlockTargetNav() {
  const navigate = useNavigate();
  return (target?: BlockTarget) => {
    if (!target?.kind) return;
    const kind = target.kind;
    const value = target.value;
    if (kind === 'category' && value) navigate(`/category/${encodeURIComponent(value)}`);
    else if (kind === 'item' && value) navigate(`/item/${encodeURIComponent(value)}`);
    else if (kind === 'tag' && value) navigate(`/?tag=${encodeURIComponent(value)}`);
    else if (kind === 'flash_sale') navigate('/sale');
    else if (kind === 'home') navigate('/');
    else if (kind === 'url' && value) window.open(value, '_blank', 'noopener,noreferrer');
  };
}

export function AnnouncementBarView({ block }: { block: AnnouncementBarBlock }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  const inner = (
    <span className="text-xs font-medium">{block.text}</span>
  );
  return (
    <div
      className="sticky top-0 z-40 flex items-center justify-between gap-2 px-4 py-2 text-center"
      style={{ background: block.bg || '#111', color: block.color || '#fff' }}
    >
      {block.link ? (
        <a href={block.link} className="flex-1" target="_blank" rel="noreferrer">
          {inner}
        </a>
      ) : (
        <div className="flex-1">{inner}</div>
      )}
      {block.dismissible !== false && (
        <button
          type="button"
          className="shrink-0 opacity-70"
          aria-label="بستن"
          onClick={() => setDismissed(true)}
        >
          ×
        </button>
      )}
    </div>
  );
}

export function StoryBarView({
  block,
  afterHero = false,
}: {
  block: StoryBarBlock;
  afterHero?: boolean;
}) {
  const items = (block.items || []).filter((s) => resolveStorySlides(s).length > 0);
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);
  if (!items.length) return null;
  return (
    <>
      <section className={`story-bar-section px-4 ${afterHero ? 'story-bar-after-hero' : 'pt-4'}`}>
        <div className="flex gap-3 overflow-x-auto pb-1">
          {items.map((story, i) => (
            <button
              key={`${block.id}-${i}`}
              type="button"
              className="flex w-[4.5rem] shrink-0 flex-col items-center gap-1.5"
              onClick={() => setViewerIndex(i)}
            >
              <div className="story-ring">
                <div className="story-ring-inner">
                  <SafeImage
                    src={resolveMediaUrl(story.image || story.slides?.[0]?.image || '')}
                    className="h-full w-full object-cover"
                    fallback={
                      <div className="flex h-full w-full items-center justify-center bg-[var(--color-primary-soft)] text-xs text-primary">
                        {story.title?.slice(0, 2)}
                      </div>
                    }
                  />
                </div>
              </div>
              <span className="w-full truncate text-center text-[10px] text-muted">{story.title}</span>
            </button>
          ))}
        </div>
      </section>
      {viewerIndex !== null && (
        <StoryViewer
          stories={items}
          startIndex={viewerIndex}
          onClose={() => setViewerIndex(null)}
        />
      )}
    </>
  );
}

export function CountdownView({ block }: { block: CountdownBlock }) {
  const go = useBlockTargetNav();
  const { config } = useApp();
  const accent = block.accent || config?.theme?.accent_color || '#c2402f';

  if (!block.ends_at) {
    return (
      <section className="mx-4 mt-4 rounded-2xl border border-dashed border-border bg-surface p-4 text-center text-sm text-muted">
        {block.title || 'شمارش معکوس'} — تاریخ پایان را در پنل تنظیم کنید
      </section>
    );
  }

  return (
    <CountdownBanner
      title={block.title}
      endsAt={block.ends_at}
      accent={accent}
      ctaLabel={block.cta_label}
      onCtaClick={block.cta_label ? () => go(block.cta_target) : undefined}
    />
  );
}

export function CouponBlockView({ block }: { block: CouponBlock }) {
  return (
    <section className="coupon-block">
      {block.title && <h2 className="coupon-block-title">{block.title}</h2>}
      {block.subtitle && <p className="coupon-block-subtitle">{block.subtitle}</p>}
      <div className="coupon-block-row">
        <code className="coupon-code">{block.code}</code>
        <CopyButton
          value={block.code || ''}
          label={block.copy_label || 'کپی'}
          copiedLabel="کپی شد"
          className="coupon-copy-btn"
        />
      </div>
    </section>
  );
}

export function ProductCarouselView({ block }: { block: ProductCarouselBlock }) {
  const { adapter } = useApp();
  const navigate = useNavigate();
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchItems>>>([]);
  const [loading, setLoading] = useState(true);
  const isFlashSale = block.source === 'flash_sale';

  useEffect(() => {
    setLoading(true);
    const params: Parameters<typeof fetchItems>[0] = {
      source: block.source || 'featured',
      limit: block.limit || 10,
    };
    if (block.source === 'category' && block.category) params.category = block.category;
    if (block.source === 'tag' && block.tag) params.tag = block.tag;
    fetchItems(params, adapter.initData || undefined)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [block.id, block.source, block.category, block.tag, block.limit, adapter.initData]);

  if (!loading && !items.length) return null;

  return (
    <ItemsSection
      title={block.title || 'محصولات'}
      count={loading ? undefined : items.length}
      action={
        isFlashSale ? (
          <button
            type="button"
            className="text-xs font-semibold text-primary"
            onClick={() => navigate('/sale')}
          >
            مشاهده همه
          </button>
        ) : undefined
      }
    >
      {loading ? (
        <div className="flex gap-3 overflow-x-auto">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-36 w-36 shrink-0 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {items.map((item) => (
            <div key={item.id} className="w-40 shrink-0">
              <ItemCard item={item} compact />
            </div>
          ))}
        </div>
      )}
    </ItemsSection>
  );
}

export function BannerGridView({ block }: { block: BannerGridBlock }) {
  const go = useBlockTargetNav();
  const cols = block.columns === 3 ? 3 : block.columns === 4 ? 4 : 2;
  const items = block.items || [];
  if (!items.length) return null;
  return (
    <section className="grid gap-2 px-4 pt-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
      {items.map((banner, i) => (
        <button
          key={`${block.id}-${i}`}
          type="button"
          className="overflow-hidden rounded-2xl"
          onClick={() => go(banner.target)}
        >
          <SafeImage
            src={resolveMediaUrl(banner.image || '')}
            className="aspect-[4/3] w-full object-cover"
            fallback={<div className="aspect-[4/3] bg-[var(--color-primary-soft)]" />}
          />
        </button>
      ))}
    </section>
  );
}

export function VideoBlockView({ block }: { block: VideoBlock }) {
  const url = resolveMediaUrl(block.url || '');
  return (
    <section className="px-4 pt-4">
      {block.title && <h2 className="section-title mb-3">{block.title}</h2>}
      {url ? (
        <video
          className="w-full rounded-2xl bg-black"
          controls
          playsInline
          poster={block.poster ? resolveMediaUrl(block.poster) : undefined}
          src={url}
        />
      ) : (
        <div className="flex aspect-video items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-sm text-muted">
          ویدیو — آدرس را در پنل وارد کنید
        </div>
      )}
    </section>
  );
}

export function TestimonialsView({ block }: { block: TestimonialsBlock }) {
  const items = block.items || [];
  if (!items.length) return null;
  return (
    <ItemsSection title={block.title || 'نظر مشتری‌ها'}>
      <div className="flex gap-3 overflow-x-auto pb-1">
        {items.map((t, i) => (
          <div key={`${block.id}-${i}`} className="w-64 shrink-0 rounded-2xl border border-border bg-surface p-4">
            <div className="mb-2 text-amber-500">
              {'★'.repeat(t.rating || 5)}{'☆'.repeat(5 - (t.rating || 5))}
            </div>
            <p className="text-sm leading-relaxed text-muted">{t.text}</p>
            {t.name && <p className="mt-2 text-xs font-bold">{t.name}</p>}
          </div>
        ))}
      </div>
    </ItemsSection>
  );
}

export function TrustBadgesView({ block }: { block: TrustBadgesBlock }) {
  const items = block.items || [];
  if (!items.length) return null;
  return (
    <section className="flex flex-wrap justify-center gap-3 px-4 pt-4">
      {items.map((badge, i) => (
        <div
          key={`${block.id}-${i}`}
          className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs"
        >
          {badge.icon && <span>{badge.icon}</span>}
          <span>{badge.label}</span>
        </div>
      ))}
    </section>
  );
}

export function FaqBlockView({ block }: { block: FaqBlock }) {
  const [open, setOpen] = useState<number | null>(null);
  const items = block.items || [];
  if (!items.length) return null;
  return (
    <section className="px-4 pt-4">
      <h2 className="section-title mb-3">{block.title || 'سوالات متداول'}</h2>
      <div className="flex flex-col gap-2">
        {items.map((item, i) => (
          <div key={`${block.id}-${i}`} className="rounded-2xl border border-border bg-surface">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 px-4 py-3 text-right text-sm font-semibold"
              onClick={() => setOpen(open === i ? null : i)}
            >
              {item.q}
              <span className="text-muted">{open === i ? '−' : '+'}</span>
            </button>
            {open === i && (
              <div className="border-t border-border px-4 py-3 text-sm leading-relaxed text-muted">
                {item.a}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export function InfoBlockView({ block }: { block: InfoBlock }) {
  const loc = block.location;
  const mapUrl = loc
    ? `https://www.google.com/maps/search/?api=1&query=${loc.lat},${loc.lng}`
    : '';
  return (
    <section className="mx-4 mt-4 rounded-2xl border border-border bg-surface p-4 text-sm">
      {block.about && <p className="leading-relaxed text-muted">{block.about}</p>}
      {block.phones?.length ? (
        <div className="mt-3">
          <strong className="text-xs text-muted">تماس</strong>
          <div className="mt-1 flex flex-wrap gap-2">
            {block.phones.map((p) => (
              <a key={p} href={`tel:${p}`} className="font-mono text-primary">
                {p}
              </a>
            ))}
          </div>
        </div>
      ) : null}
      {block.address && (
        <p className="mt-3">
          <strong className="text-xs text-muted">آدرس: </strong>
          {block.address}
        </p>
      )}
      {block.hours && (
        <p className="mt-2">
          <strong className="text-xs text-muted">ساعت کاری: </strong>
          {block.hours}
        </p>
      )}
      {mapUrl && (
        <a href={mapUrl} target="_blank" rel="noreferrer" className="btn-primary mt-4 inline-flex text-xs">
          مسیریابی
        </a>
      )}
      {block.socials && (
        <div className="mt-3 flex flex-wrap gap-2">
          {block.socials.instagram && (
            <a href={block.socials.instagram} className="text-xs text-primary" target="_blank" rel="noreferrer">
              اینستاگرام
            </a>
          )}
          {block.socials.telegram && (
            <a href={block.socials.telegram} className="text-xs text-primary" target="_blank" rel="noreferrer">
              تلگرام
            </a>
          )}
        </div>
      )}
    </section>
  );
}

export function BundleBlockView({ block }: { block: BundleBlock }) {
  const { adapter, refreshCart } = useApp();
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchItems>>>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const slugs = block.item_slugs || [];
    if (!slugs.length) return;
    fetchItems(undefined, adapter.initData || undefined)
      .then((all) => setItems(all.filter((i) => slugs.includes(i.slug))))
      .catch(() => setItems([]));
  }, [block.item_slugs, adapter.initData]);

  const addAll = async () => {
    if (!adapter?.initData) return;
    setBusy(true);
    try {
      for (const item of items) {
        if (item.is_buyable && !item.has_access) {
          await updateCart(adapter.initData, { item_id: item.id, quantity: 1 });
        }
      }
      await refreshCart();
    } finally {
      setBusy(false);
    }
  };

  if (!items.length) return null;

  return (
    <section className="mx-4 mt-4 rounded-2xl border border-primary/20 bg-[var(--color-primary-soft)] p-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-bold">{block.title || 'ست ویژه'}</h2>
        {block.badge && (
          <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white">
            {block.badge}
          </span>
        )}
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto">
        {items.map((item) => (
          <Link key={item.id} to={`/item/${item.slug}`} className="w-20 shrink-0">
            <SafeImage
              src={item.cover_url || item.images?.[0] || ''}
              className="aspect-square rounded-xl object-cover"
              fallback={<div className="aspect-square rounded-xl bg-surface" />}
            />
          </Link>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between">
        {block.bundle_price ? (
          <span className="price-tag">{formatPrice(block.bundle_price)}</span>
        ) : null}
        <button type="button" className="btn-primary btn-sm text-xs" onClick={addAll} disabled={busy}>
          افزودن همه به سبد
        </button>
      </div>
    </section>
  );
}

export function RichTextBlockView({ block }: { block: RichTextBlock }) {
  const align = block.align || 'right';
  return (
    <section className="px-4 pt-4" style={{ textAlign: align }}>
      {block.title && <h2 className="section-title mb-2">{block.title}</h2>}
      <div
        className="prose-shop text-sm leading-relaxed text-muted"
        dangerouslySetInnerHTML={{ __html: block.html || '' }}
      />
    </section>
  );
}

export function BlockRenderer({
  block,
  afterHero,
  searchInput,
  onSearchInputChange,
  onSearch,
  productItems,
  productsLoading,
  searchLoading,
}: {
  block: HomeBlock;
  afterHero?: boolean;
  searchInput?: string;
  onSearchInputChange?: (v: string) => void;
  onSearch?: () => void;
  productItems?: import('../types').CatalogItem[];
  productsLoading?: boolean;
  searchLoading?: boolean;
}) {
  switch (block.type) {
    case 'announcement_bar':
      return <AnnouncementBarView block={block} />;
    case 'story_bar':
      return <StoryBarView block={block} afterHero={afterHero} />;
    case 'countdown':
      return <CountdownView block={block} />;
    case 'coupon':
      return <CouponBlockView block={block} />;
    case 'product_carousel':
      return <ProductCarouselView block={block} />;
    case 'banner_grid':
      return <BannerGridView block={block} />;
    case 'video':
      return <VideoBlockView block={block} />;
    case 'testimonials':
      return <TestimonialsView block={block} />;
    case 'trust_badges':
      return <TrustBadgesView block={block} />;
    case 'faq':
      return <FaqBlockView block={block} />;
    case 'info':
      return <InfoBlockView block={block} />;
    case 'bundle':
      return <BundleBlockView block={block} />;
    case 'rich_text':
      return <RichTextBlockView block={block} />;
    default:
      return null;
  }
}
