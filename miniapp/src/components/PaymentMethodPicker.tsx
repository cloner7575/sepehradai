import type { PaymentMethodOption } from '../types';

export function PaymentMethodPicker({
  methods,
  value,
  onChange,
  embedded = false,
}: {
  methods: PaymentMethodOption[];
  value: string;
  onChange: (id: string) => void;
  embedded?: boolean;
}) {
  if (!methods.length) return null;

  if (methods.length === 1) {
    return (
      <div className={embedded ? '' : 'mb-5'}>
        {!embedded && <div className="section-title mb-3">روش پرداخت</div>}
        <div className="payment-method-single">
          <span className="payment-method-dot" aria-hidden />
          <span className="text-sm font-medium">{methods[0].label}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? 'space-y-2' : 'mb-5'}>
      {!embedded && <div className="section-title mb-3">روش پرداخت</div>}
      <div className="space-y-2">
        {methods.map((m) => {
          const selected = value === m.id;
          return (
            <label
              key={m.id}
              className={`payment-method-option ${selected ? 'payment-method-option--selected' : ''}`}
            >
              <span className={`payment-method-radio ${selected ? 'payment-method-radio--selected' : ''}`}>
                {selected && <span className="payment-method-radio-dot" />}
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
