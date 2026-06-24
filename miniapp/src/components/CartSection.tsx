import type { ReactNode } from 'react';

export function CartSection({
  step,
  title,
  subtitle,
  children,
}: {
  step?: number;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="cart-section">
      <div className="cart-section-head">
        {step != null && <span className="cart-section-step">{step}</span>}
        <div className="min-w-0">
          <h2 className="cart-section-title">{title}</h2>
          {subtitle && <p className="cart-section-subtitle">{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}
