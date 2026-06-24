import { useMemo, useState } from 'react';
import type { CheckoutFormConfig, CheckoutFormField } from '../types';

export function useCheckoutForm(config: CheckoutFormConfig | undefined) {
  const fields = useMemo(
    () => (config?.enabled ? config.fields || [] : []),
    [config?.enabled, config?.fields],
  );

  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const setValue = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {};
    fields.forEach((field) => {
      const value = (values[field.key] || '').trim();
      if (field.required && !value) {
        nextErrors[field.key] = `${field.label} الزامی است`;
        return;
      }
      if (value && field.type === 'email' && !value.includes('@')) {
        nextErrors[field.key] = `${field.label} معتبر نیست`;
      }
    });
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const customerData = useMemo(() => {
    const data: Record<string, string> = {};
    fields.forEach((field) => {
      const value = (values[field.key] || '').trim();
      if (value) data[field.key] = value;
    });
    return data;
  }, [fields, values]);

  return {
    fields,
    title: config?.title || 'اطلاعات تحویل',
    hasForm: fields.length > 0,
    values,
    errors,
    setValue,
    validate,
    customerData,
  };
}

interface CheckoutFormProps {
  title?: string;
  fields: CheckoutFormField[];
  values: Record<string, string>;
  errors: Record<string, string>;
  onChange: (key: string, value: string) => void;
  disabled?: boolean;
  embedded?: boolean;
}

export function CheckoutForm({
  title,
  fields,
  values,
  errors,
  onChange,
  disabled,
  embedded = false,
}: CheckoutFormProps) {
  if (!fields.length) return null;

  return (
    <div className={embedded ? 'space-y-3' : 'card mb-4 p-4'}>
      {title && !embedded && <h2 className="mb-3 text-sm font-bold">{title}</h2>}
      <div className="space-y-3">
        {fields.map((field) => (
          <div key={field.key}>
            <label className="checkout-field-label" htmlFor={`checkout-${field.key}`}>
              {field.label}
              {field.required && <span className="text-red-500"> *</span>}
            </label>
            {field.type === 'textarea' ? (
              <textarea
                id={`checkout-${field.key}`}
                className="input-field min-h-[88px] resize-y"
                placeholder={`${field.label} را وارد کنید`}
                value={values[field.key] || ''}
                disabled={disabled}
                onChange={(e) => onChange(field.key, e.target.value)}
              />
            ) : (
              <input
                id={`checkout-${field.key}`}
                type={field.type === 'tel' ? 'tel' : field.type === 'email' ? 'email' : 'text'}
                className="input-field"
                placeholder={`${field.label} را وارد کنید`}
                value={values[field.key] || ''}
                disabled={disabled}
                dir={field.type === 'tel' || field.type === 'email' ? 'ltr' : undefined}
                onChange={(e) => onChange(field.key, e.target.value)}
              />
            )}
            {errors[field.key] && <p className="mt-1 text-xs text-red-600">{errors[field.key]}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
