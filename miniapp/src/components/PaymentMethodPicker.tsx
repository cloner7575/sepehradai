import type { PaymentMethodOption } from '../types';

export function PaymentMethodPicker({
  methods,
  value,
  onChange,
}: {
  methods: PaymentMethodOption[];
  value: string;
  onChange: (id: string) => void;
}) {
  if (methods.length <= 1) return null;
  return (
    <div className="mb-5">
      <div className="section-title mb-3">روش پرداخت</div>
      <div className="space-y-2">
        {methods.map((m) => {
          const selected = value === m.id;
          return (
            <label
              key={m.id}
              className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3.5 transition ${
                selected
                  ? 'border-primary bg-[var(--color-primary-soft)]'
                  : 'border-border bg-surface'
              }`}
            >
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition ${
                  selected ? 'border-primary' : 'border-border'
                }`}
              >
                {selected && <span className="h-2 w-2 rounded-full bg-primary" />}
              </span>
              <input
                type="radio"
                name="payment_method"
                value={m.id}
                checked={selected}
                onChange={() => onChange(m.id)}
                className="sr-only"
              />
              <span className="text-sm font-medium">{m.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
