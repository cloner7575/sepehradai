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
    <div className="mb-4 space-y-2">
      <div className="text-sm font-semibold text-muted">روش پرداخت</div>
      {methods.map((m) => (
        <label
          key={m.id}
          className={`card flex cursor-pointer items-center gap-3 p-3 ${value === m.id ? 'ring-2 ring-primary' : ''}`}
        >
          <input
            type="radio"
            name="payment_method"
            value={m.id}
            checked={value === m.id}
            onChange={() => onChange(m.id)}
            className="accent-primary"
          />
          <span className="font-medium">{m.label}</span>
        </label>
      ))}
    </div>
  );
}
