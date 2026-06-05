export type PlatformKind = 'bale' | 'telegram' | 'browser';

export interface WebAppAdapter {
  kind: PlatformKind;
  initData: string;
  colorScheme: string;
  themeParams: Record<string, string>;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openInvoice: (params: string, callback?: (status: { status: string }) => void) => void;
  openLink: (url: string) => void;
  sendData: (data: string) => void;
  showBackButton: (onClick: () => void) => void;
  hideBackButton: () => void;
  isSupported: boolean;
}

function platformMetaHint(): PlatformKind | null {
  const raw = document.querySelector('meta[name="miniapp-platform"]')?.getAttribute('content');
  if (raw === 'bale' || raw === 'telegram') {
    return raw;
  }
  return null;
}

function detectKind(): PlatformKind {
  const hint = platformMetaHint();
  const w = window as Window & {
    Bale?: { WebApp?: unknown };
    Telegram?: { WebApp?: { initData?: string } };
  };
  if (hint === 'bale' || (w.Bale?.WebApp && (w.Bale.WebApp as { initData?: string }).initData !== undefined)) {
    return 'bale';
  }
  if (hint === 'telegram' || w.Telegram?.WebApp?.initData || w.Telegram?.WebApp) {
    return 'telegram';
  }
  return 'browser';
}

export function createWebAppAdapter(platformHint?: string): WebAppAdapter {
  const w = window as Window & {
    Bale?: { WebApp: BaleWebApp };
    Telegram?: { WebApp: TelegramWebApp };
  };
  const kind: PlatformKind =
    platformHint === 'telegram'
      ? 'telegram'
      : platformHint === 'bale'
        ? 'bale'
        : detectKind();

  if (kind === 'bale' && w.Bale?.WebApp) {
    const app = w.Bale.WebApp;
    return {
      kind: 'bale',
      initData: app.initData || '',
      colorScheme: app.colorScheme || 'light',
      themeParams: (app.themeParams as Record<string, string>) || {},
      ready: () => app.ready(),
      expand: () => app.expand(),
      close: () => app.close(),
      openInvoice: (params, cb) => app.openInvoice(params, cb),
      openLink: (url) => app.openLink(url),
      sendData: (data) => app.sendData(data),
      showBackButton: (onClick) => {
        app.BackButton.onClick(onClick);
        app.BackButton.show();
      },
      hideBackButton: () => app.BackButton.hide(),
      isSupported: app.isMiniAppSupported !== false,
    };
  }

  if (w.Telegram?.WebApp) {
    const app = w.Telegram.WebApp;
    return {
      kind: 'telegram',
      initData: app.initData || '',
      colorScheme: app.colorScheme || 'light',
      themeParams: (app.themeParams as Record<string, string>) || {},
      ready: () => app.ready(),
      expand: () => app.expand(),
      close: () => app.close(),
      openInvoice: () => {},
      openLink: (url) => app.openLink(url),
      sendData: (data) => app.sendData(data),
      showBackButton: (onClick) => {
        app.BackButton.onClick(onClick);
        app.BackButton.show();
      },
      hideBackButton: () => app.BackButton.hide(),
      isSupported: true,
    };
  }

  return {
    kind: 'browser',
    initData: '',
    colorScheme: 'light',
    themeParams: {},
    ready: () => {},
    expand: () => {},
    close: () => {},
    openInvoice: () => {},
    openLink: (url) => { window.open(url, '_blank'); },
    sendData: () => {},
    showBackButton: () => {},
    hideBackButton: () => {},
    isSupported: true,
  };
}

interface BaleWebApp {
  initData: string;
  colorScheme: string;
  themeParams: unknown;
  isMiniAppSupported?: boolean;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openInvoice: (params: string, cb?: (s: { status: string }) => void) => void;
  openLink: (url: string) => void;
  sendData: (data: string) => void;
  BackButton: { show: () => void; hide: () => void; onClick: (fn: () => void) => void };
}

interface TelegramWebApp {
  initData: string;
  colorScheme: string;
  themeParams: unknown;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openLink: (url: string) => void;
  sendData: (data: string) => void;
  BackButton: { show: () => void; hide: () => void; onClick: (fn: () => void) => void };
}

export function applyTheme(configTheme: Record<string, string>, adapter: WebAppAdapter) {
  const tp = adapter.themeParams;
  const root = document.documentElement;
  const primary = configTheme.primary_color || tp.button_color || '#2563eb';
  const accent = configTheme.accent_color || '#7c3aed';
  const bg = tp.bg_color || (adapter.colorScheme === 'dark' ? '#0f172a' : '#f8fafc');
  const surface = tp.secondary_bg_color || (adapter.colorScheme === 'dark' ? '#1e293b' : '#ffffff');
  const text = tp.text_color || (adapter.colorScheme === 'dark' ? '#f1f5f9' : '#0f172a');
  root.style.setProperty('--color-primary', primary);
  root.style.setProperty('--color-accent', accent);
  root.style.setProperty('--color-bg', bg);
  root.style.setProperty('--color-surface', surface);
  root.style.setProperty('--color-text', text);
  root.style.setProperty('--color-muted', tp.hint_color || '#64748b');
}
