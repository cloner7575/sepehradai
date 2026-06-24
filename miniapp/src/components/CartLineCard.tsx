import { Link } from 'react-router-dom';
import { formatPrice } from '../api';
import type { CartLine } from '../types';
import { CartQuantityControl } from './CartQuantityControl';
import { IconPackage } from './Icons';

interface CartLineCardProps {
  line: CartLine;
  disabled?: boolean;
  onChangeQty: (qty: number) => void;
}

export function CartLineCard({ line, disabled, onChangeQty }: CartLineCardProps) {
  return (
    <article className="cart-line-card">
      <Link to={`/item/${line.slug}`} className="cart-line-thumb" aria-label={line.title}>
        {line.image ? (
          <img src={line.image} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-muted/30">
            <IconPackage className="h-7 w-7" />
          </div>
        )}
      </Link>

      <div className="cart-line-body">
        <div className="flex items-start justify-between gap-3">
          <Link to={`/item/${line.slug}`} className="cart-line-title">
            {line.title}
          </Link>
          <span className="cart-line-total">{formatPrice(line.line_total)}</span>
        </div>

        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="text-xs text-muted">
            {formatPrice(line.price)}
            <span className="mx-1 text-border">·</span>
            {line.quantity} عدد
          </span>
          <CartQuantityControl
            quantity={line.quantity}
            disabled={disabled}
            onChange={onChangeQty}
          />
        </div>
      </div>
    </article>
  );
}
