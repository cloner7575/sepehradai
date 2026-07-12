import { Link } from 'react-router-dom';
import { useApp } from '../App';
import { IconBook, IconCart } from './Icons';

interface HeaderActionsProps {
  variant?: 'default' | 'hero';
  showCart?: boolean;
  showLibrary?: boolean;
}

export function HeaderActions({
  variant = 'default',
  showCart = true,
  showLibrary = true,
}: HeaderActionsProps) {
  const { config, cartItems, adapter, hasLibrary } = useApp();
  const cartCount = cartItems.reduce((s, l) => s + l.quantity, 0);
  const shopEnabled = config?.is_enabled !== false;
  const canShowLibrary = showLibrary && Boolean(adapter.initData) && hasLibrary;
  const canShowCart = showCart && shopEnabled;

  if (!canShowLibrary && !canShowCart) return null;

  const btnClass =
    variant === 'hero'
      ? 'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/20'
      : 'cart-header-btn';

  return (
    <div className="flex shrink-0 items-center gap-2">
      {canShowLibrary && (
        <Link to="/library" className={btnClass} aria-label="کتابخانه من">
          <IconBook className="h-5 w-5" />
        </Link>
      )}
      {canShowCart && (
        <Link to="/cart" className={btnClass} aria-label="سبد خرید">
          <IconCart className="h-5 w-5" />
          {cartCount > 0 && (
            <span className="cart-header-badge">{cartCount > 99 ? '99+' : cartCount}</span>
          )}
        </Link>
      )}
    </div>
  );
}
