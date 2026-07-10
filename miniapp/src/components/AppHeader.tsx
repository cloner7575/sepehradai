import { Link } from 'react-router-dom';
import { useApp } from '../App';
import { IconBook, IconCart, IconGrid } from './Icons';
import { SafeImage } from './SafeImage';

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  showBrand?: boolean;
  showCart?: boolean;
}

export function AppHeader({
  title,
  subtitle,
  showBrand = false,
  showCart = true,
}: AppHeaderProps) {
  const { config, cartItems } = useApp();
  const cartCount = cartItems.reduce((s, l) => s + l.quantity, 0);
  const shopEnabled = config?.is_enabled !== false;

  return (
    <header className="app-header">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {showBrand && (
          <>
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
              {(config?.hero_subtitle || subtitle) && (
                <p className="truncate text-[11px] text-muted">
                  {subtitle || config?.hero_subtitle}
                </p>
              )}
            </div>
          </>
        )}
        {!showBrand && title && (
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold tracking-tight">{title}</h1>
            {subtitle && <p className="truncate text-[11px] text-muted">{subtitle}</p>}
          </div>
        )}
      </div>
      {showCart && shopEnabled && (
        <div className="flex shrink-0 items-center gap-1">
          <Link to="/library" className="cart-header-btn" aria-label="کتابخانه من">
            <IconBook className="h-5 w-5" />
          </Link>
          <Link to="/cart" className="cart-header-btn" aria-label="سبد خرید">
            <IconCart className="h-5 w-5" />
            {cartCount > 0 && (
              <span className="cart-header-badge">{cartCount > 99 ? '99+' : cartCount}</span>
            )}
          </Link>
        </div>
      )}
    </header>
  );
}
