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

type MiniAppLike = {
  initData?: string;
  initDataUnsafe?: { user?: { id?: number } };
};

function hasMiniAppSession(app?: MiniAppLike | null): boolean {
  if (!app) return false;
  if ((app.initData || '').trim()) return true;
  const user = app.initDataUnsafe?.user;
  return Boolean(user && user.id);
}

function safeCall(fn?: () => void) {
  try {
    fn?.();
  } catch {
    /* SDK ممکن است خارج از کلاینت بله/تلگرام ناقص باشد */
  }
}

function detectKind(): PlatformKind {
  const w = window as Window & {
    Bale?: { WebApp?: BaleWebApp };
    Telegram?: { WebApp?: TelegramWebApp };
  };
  if (hasMiniAppSession(w.Bale?.WebApp)) return 'bale';
  if (hasMiniAppSession(w.Telegram?.WebApp)) return 'telegram';
  return 'browser';
}

function baleAdapter(app: BaleWebApp): WebAppAdapter {
  const back = app.BackButton;
  return {
    kind: 'bale',
    initData: app.initData || '',
    colorScheme: app.colorScheme || 'light',
    themeParams: (app.themeParams as Record<string, string>) || {},
    ready: () => safeCall(() => app.ready()),
    expand: () => safeCall(() => app.expand()),
    close: () => safeCall(() => app.close()),
    openInvoice: (params, cb) => safeCall(() => app.openInvoice(params, cb)),
    openLink: (url) => safeCall(() => app.openLink(url)),
    sendData: (data) => safeCall(() => app.sendData(data)),
    showBackButton: (onClick) => {
      if (!back?.onClick || !back?.show) return;
      safeCall(() => {
        back.onClick(onClick);
        back.show();
      });
    },
    hideBackButton: () => safeCall(() => back?.hide?.()),
    isSupported: app.isMiniAppSupported !== false,
  };
}

function telegramAdapter(app: TelegramWebApp): WebAppAdapter {
  const back = app.BackButton;
  return {
    kind: 'telegram',
    initData: app.initData || '',
    colorScheme: app.colorScheme || 'light',
    themeParams: (app.themeParams as Record<string, string>) || {},
    ready: () => safeCall(() => app.ready()),
    expand: () => safeCall(() => app.expand()),
    close: () => safeCall(() => app.close()),
    openInvoice: () => {},
    openLink: (url) => safeCall(() => app.openLink(url)),
    sendData: (data) => safeCall(() => app.sendData(data)),
    showBackButton: (onClick) => {
      if (!back?.onClick || !back?.show) return;
      safeCall(() => {
        back.onClick(onClick);
        back.show();
      });
    },
    hideBackButton: () => safeCall(() => back?.hide?.()),
    isSupported: true,
  };
}

export function createWebAppAdapter(_platformHint?: string): WebAppAdapter {
  const w = window as Window & {
    Bale?: { WebApp: BaleWebApp };
    Telegram?: { WebApp: TelegramWebApp };
  };
  const kind = detectKind();

  if (kind === 'bale' && w.Bale?.WebApp) {
    return baleAdapter(w.Bale.WebApp);
  }

  if (kind === 'telegram' && w.Telegram?.WebApp) {
    return telegramAdapter(w.Telegram.WebApp);
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
  initDataUnsafe?: { user?: { id?: number } };
  colorScheme: string;
  themeParams: unknown;
  isMiniAppSupported?: boolean;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openInvoice: (params: string, cb?: (s: { status: string }) => void) => void;
  openLink: (url: string) => void;
  sendData: (data: string) => void;
  BackButton?: { show: () => void; hide: () => void; onClick: (fn: () => void) => void };
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { id?: number } };
  colorScheme: string;
  themeParams: unknown;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openLink: (url: string) => void;
  sendData: (data: string) => void;
  BackButton?: { show: () => void; hide: () => void; onClick: (fn: () => void) => void };
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
