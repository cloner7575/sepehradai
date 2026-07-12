import { useEffect, useMemo, useState } from 'react';

function CountdownUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex min-w-[3rem] flex-col items-center rounded-xl bg-white/15 px-2 py-1.5">
      <span className="text-lg font-bold tabular-nums">{String(value).padStart(2, '0')}</span>
      <span className="text-[10px] opacity-80">{label}</span>
    </div>
  );
}

export function CountdownBanner({
  title,
  endsAt,
  accent = '#c2402f',
  ctaLabel,
  onCtaClick,
  expiredMessage = 'فروش ویژه به پایان رسید',
}: {
  title?: string;
  endsAt: string | number | Date | null | undefined;
  accent?: string;
  ctaLabel?: string;
  onCtaClick?: () => void;
  expiredMessage?: string;
}) {
  const endsAtMs = useMemo(() => {
    if (endsAt == null || endsAt === '') return NaN;
    if (typeof endsAt === 'number') return endsAt;
    if (endsAt instanceof Date) return endsAt.getTime();
    return new Date(endsAt).getTime();
  }, [endsAt]);

  const [now, setNow] = useState(Date.now());
  const invalidDate = Number.isNaN(endsAtMs);

  useEffect(() => {
    if (invalidDate) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [invalidDate]);

  if (invalidDate) return null;

  const diff = endsAtMs - now;
  if (diff <= 0) {
    return (
      <section className="mx-4 mt-4 rounded-2xl bg-surface p-4 text-center text-sm text-muted">
        {expiredMessage}
      </section>
    );
  }

  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  const secs = Math.floor((diff % 60000) / 1000);

  return (
    <section
      className="mx-4 mt-4 rounded-2xl p-4 text-white"
      style={{ background: `linear-gradient(135deg, ${accent}, color-mix(in srgb, ${accent} 70%, #000))` }}
    >
      {title && <h2 className="mb-3 text-center text-sm font-bold">{title}</h2>}
      <div className="flex justify-center gap-2">
        {days > 0 && <CountdownUnit value={days} label="روز" />}
        <CountdownUnit value={hours} label="ساعت" />
        <CountdownUnit value={mins} label="دقیقه" />
        <CountdownUnit value={secs} label="ثانیه" />
      </div>
      {ctaLabel && onCtaClick && (
        <button
          type="button"
          className="btn-primary mt-4 w-full bg-white text-sm font-bold"
          style={{ color: accent }}
          onClick={onCtaClick}
        >
          {ctaLabel}
        </button>
      )}
    </section>
  );
}
