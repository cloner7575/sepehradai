import { IconTrash } from './Icons';

interface CartQuantityControlProps {
  quantity: number;
  disabled?: boolean;
  size?: 'sm' | 'lg';
  onChange: (quantity: number) => void;
}

export function CartQuantityControl({
  quantity,
  disabled,
  size = 'sm',
  onChange,
}: CartQuantityControlProps) {
  const large = size === 'lg';

  return (
    <div
      className={`flex items-center gap-1 rounded-2xl border border-border bg-surface ${
        large ? 'p-1.5' : 'p-1'
      }`}
    >
      <button
        type="button"
        className={`flex items-center justify-center rounded-xl transition active:scale-95 disabled:opacity-40 ${
          large ? 'h-11 w-11' : 'h-8 w-8'
        } ${quantity <= 1 ? 'text-red-500' : 'text-[var(--color-text)]'}`}
        disabled={disabled}
        onClick={() => onChange(quantity <= 1 ? 0 : quantity - 1)}
        aria-label={quantity <= 1 ? 'حذف از سبد' : 'کاهش'}
      >
        {quantity <= 1 ? (
          <IconTrash className={large ? 'h-5 w-5' : 'h-4 w-4'} />
        ) : (
          <span className={`font-medium ${large ? 'text-lg' : 'text-sm'}`}>−</span>
        )}
      </button>
      <span
        className={`min-w-[2rem] flex-1 text-center font-bold tabular-nums ${
          large ? 'text-base' : 'text-sm'
        }`}
      >
        {quantity}
      </span>
      <button
        type="button"
        className={`qty-btn ${large ? 'h-11 w-11 text-lg' : ''}`}
        disabled={disabled}
        onClick={() => onChange(quantity + 1)}
        aria-label="افزایش"
      >
        +
      </button>
    </div>
  );
}
