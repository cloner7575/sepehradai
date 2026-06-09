import type { ReactNode } from 'react';

export function ItemsSection({
  title,
  count,
  children,
  action,
}: {
  title: string;
  count?: number;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="px-4 pt-6">
      <div className="section-header">
        <div>
          <h2 className="section-title mb-0">{title}</h2>
          {count !== undefined && <p className="section-meta">{count} مورد</p>}
        </div>
        {action}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}
