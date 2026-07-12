import { useApp } from '../App';
import { IconGrid } from './Icons';
import { HeaderActions } from './HeaderActions';
import { SafeImage } from './SafeImage';

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  showBrand?: boolean;
  showCart?: boolean;
  showLibrary?: boolean;
}

export function AppHeader({
  title,
  subtitle,
  showBrand = false,
  showCart = true,
  showLibrary = true,
}: AppHeaderProps) {
  const { config } = useApp();

  return (
    <header className="app-header">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {showBrand && (
          <>
            {config?.logo_url ? (
              <SafeImage
                src={config.logo_url}
                className="h-10 w-10 shrink-0 rounded-2xl object-cover ring-1 ring-border"
                fallback={
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-primary">
                    <IconGrid className="h-4 w-4" />
                  </div>
                }
              />
            ) : (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-primary">
                <IconGrid className="h-4 w-4" />
              </div>
            )}
            <div className="min-w-0">
              <h1 className="truncate text-base font-bold tracking-tight">
                {config?.hero_title || 'ویترین'}
              </h1>
              {(config?.hero_subtitle || subtitle) && (
                <p className="truncate text-[11px] text-muted">
                  {subtitle || config?.hero_subtitle}
                </p>
              )}
            </div>
          </>
        )}
        {!showBrand && title && (
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold tracking-tight">{title}</h1>
            {subtitle && <p className="truncate text-[11px] text-muted">{subtitle}</p>}
          </div>
        )}
      </div>
      <HeaderActions showCart={showCart} showLibrary={showLibrary} />
    </header>
  );
}
