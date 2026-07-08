import { useState } from 'react';
import { formatPrice } from '../api';
import { IconTag } from './Icons';

function bringFieldIntoView(target: HTMLElement) {
  target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
  window.setTimeout(() => {
    target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
  }, 220);
}

export function DiscountCodeField({
  value,
  appliedCode,
  onChange,
  onApply,
  appliedAmount,
  disabled,
}: {
  value: string;
  appliedCode?: string;
  onChange: (v: string) => void;
  onApply: () => void | Promise<void>;
  appliedAmount: number;
  disabled?: boolean;
}) {
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  const applied = Boolean(appliedCode?.trim());

  const apply = async () => {
    setError('');
    setApplying(true);
    try {
      await onApply();
    } finally {
      setApplying(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      apply();
    }
  };

  return (
    <div className="discount-code-card">
      <div className="discount-code-card-head">
        <div className="discount-code-icon">
          <IconTag className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold">کد تخفیف</p>
          <p className="text-xs text-muted">در صورت داشتن کد، اینجا وارد کنید</p>
        </div>
      </div>
      {applied ? (
        <div className="discount-applied-banner">
          <div>
            <p className="text-xs text-muted">کد اعمال‌شده</p>
            <p className="font-mono text-sm font-bold tracking-wider">{appliedCode}</p>
            {appliedAmount > 0 ? (
              <p className="mt-1 text-xs text-green-600">تخفیف {formatPrice(appliedAmount)}</p>
            ) : (
              <p className="mt-1 text-xs text-amber-600">کد نامعتبر یا منقضی است</p>
            )}
          </div>
          <button
            type="button"
            className="text-xs font-semibold text-red-600"
            disabled={disabled || applying}
            onClick={() => {
              onChange('');
              setError('');
            }}
          >
            حذف
          </button>
        </div>
      ) : (
        <>
          <input
            id="discount-code"
            className="discount-code-input"
            value={value}
            onChange={(e) => {
              setError('');
              onChange(e.target.value);
            }}
            onKeyDown={handleKey}
            placeholder="مثلاً WELCOME10"
            disabled={disabled || applying}
            dir="ltr"
            onFocus={(e) => bringFieldIntoView(e.currentTarget)}
          />
          <button
            type="button"
            className="btn-primary discount-apply-btn"
            disabled={disabled || applying || !value.trim()}
            onClick={apply}
          >
            {applying ? 'در حال بررسی…' : 'اعمال کد تخفیف'}
          </button>
          {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
        </>
      )}
    </div>
  );
}
