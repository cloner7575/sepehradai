import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

export function SuccessView({
  icon,
  title,
  subtitle,
  actionLabel = 'بازگشت به ویترین',
  actionTo = '/',
}: {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  actionLabel?: string;
  actionTo?: string;
}) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-8 text-center animate-fade-in">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-primary">
        {icon}
      </div>
      <h1 className="text-lg font-bold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-2 text-sm text-muted">{subtitle}</p>}
      <Link to={actionTo} className="btn-primary mt-8 max-w-xs">
        {actionLabel}
      </Link>
    </div>
  );
}
