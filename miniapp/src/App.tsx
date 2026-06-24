import { Component, createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { fetchCart, fetchConfig, validateAuth } from './api';
import { applyTheme, createWebAppAdapter, type WebAppAdapter } from './platform';
import { setMediaBaseUrl } from './utils/url';
import type { AuthValidateResult, CartLine, CatalogConfig } from './types';
import { HomePage } from './pages/HomePage';
import { CategoryPage } from './pages/CategoryPage';
import { ItemPage } from './pages/ItemPage';
import { CartPage } from './pages/CartPage';
import { ChannelGate } from './components/ChannelGate';
import { IconAlert } from './components/Icons';

interface AppContextValue {
  config: CatalogConfig | null;
  adapter: WebAppAdapter;
  auth: AuthValidateResult | null;
  cartItems: CartLine[];
  cartTotal: number;
  refreshCart: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

class AppErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  state = { error: '' };

  static getDerivedStateFromError(error: Error) {
    return { error: error.message || 'خطای نمایش مینی‌اپ' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('miniapp render error', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-red-500">
            <IconAlert className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted">{this.state.error}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp outside provider');
  return ctx;
}

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-b border-amber-200/60 bg-amber-50 px-4 py-2.5 text-center text-xs text-amber-800">
      {children}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { adapter } = useApp();

  useEffect(() => {
    if (location.pathname === '/') {
      adapter.hideBackButton();
      return;
    }
    adapter.showBackButton(() => navigate(-1));
    return () => adapter.hideBackButton();
  }, [location.pathname, adapter, navigate]);

  return (
    <div className="mx-auto min-h-screen max-w-lg bg-[var(--color-bg)]">
      {children}
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/category/:slug" element={<CategoryPage />} />
      <Route path="/item/:slug" element={<ItemPage />} />
      <Route path="/cart" element={<CartPage />} />
    </Routes>
  );
}

export default function App() {
  const [config, setConfig] = useState<CatalogConfig | null>(null);
  const [adapter, setAdapter] = useState<WebAppAdapter>(() => createWebAppAdapter());
  const [cartItems, setCartItems] = useState<CartLine[]>([]);
  const [cartTotal, setCartTotal] = useState(0);
  const [auth, setAuth] = useState<AuthValidateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [unsupported, setUnsupported] = useState(false);

  const refreshCart = useCallback(async () => {
    if (!adapter.initData) return;
    try {
      const data = await fetchCart(adapter.initData);
      setCartItems(data.items);
      setCartTotal(data.total);
    } catch {
      setCartItems([]);
      setCartTotal(0);
    }
  }, [adapter.initData]);

  useEffect(() => {
    const ad = createWebAppAdapter();
    setAdapter(ad);
    ad.ready();
    ad.expand();

    fetchConfig()
      .then(async (cfg) => {
        setLoadError('');
        setMediaBaseUrl(cfg.public_base_url || '');
        setConfig(cfg);
        const platformAdapter = createWebAppAdapter();
        setAdapter(platformAdapter);
        if (!platformAdapter.isSupported) setUnsupported(true);
        applyTheme(cfg.theme || {}, platformAdapter);
        platformAdapter.ready();
        platformAdapter.expand();

        if (platformAdapter.initData) {
          try {
            const authResult = await validateAuth(platformAdapter.initData);
            setAuth(authResult);
          } catch {
            /* بدون initData معتبر، فقط مشاهده محدود */
          }
        }

        if (cfg.is_enabled && platformAdapter.initData) {
          fetchCart(platformAdapter.initData)
            .then((d) => {
              setCartItems(d.items);
              setCartTotal(d.total);
            })
            .catch(() => {});
        }
      })
      .catch((e: unknown) => {
        setLoadError(e instanceof Error ? e.message : 'بارگذاری مینی‌اپ ناموفق بود');
      })
      .finally(() => setLoading(false));
  }, []);

  const channelBlocked =
    auth?.channel_required === true && auth?.is_channel_member === false;

  const value = useMemo(
    () => ({ config, adapter, auth, cartItems, cartTotal, refreshCart }),
    [config, adapter, auth, cartItems, cartTotal, refreshCart],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[var(--color-bg)]">
        <div className="skeleton h-10 w-10 rounded-full" />
        <p className="text-xs text-muted">در حال بارگذاری…</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[var(--color-bg)] p-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-red-500">
          <IconAlert className="h-6 w-6" />
        </div>
        <p className="text-sm text-muted">{loadError}</p>
      </div>
    );
  }

  if (channelBlocked && auth) {
    return (
      <AppErrorBoundary>
        <AppContext.Provider value={value}>
          <ChannelGate
            adapter={adapter}
            auth={auth}
            onUnlocked={(result) => setAuth(result)}
          />
        </AppContext.Provider>
      </AppErrorBoundary>
    );
  }

  return (
    <AppErrorBoundary>
      <AppContext.Provider value={value}>
        {config && config.is_enabled === false && (
          <Banner>
            مینی‌اپ در حال آماده‌سازی است — مشاهده محتوا ممکن است، خرید هنوز فعال نشده.
          </Banner>
        )}
        {config && config.is_enabled !== false && config.can_purchase === false && (
          <Banner>
            روش پرداخت هنوز کامل تنظیم نشده — مشاهده محصولات ممکن است، خرید موقتاً غیرفعال است.
          </Banner>
        )}
        {unsupported && (
          <Banner>
            لطفاً اپلیکیشن بله/تلگرام را به‌روزرسانی کنید.
          </Banner>
        )}
        <MemoryRouter>
          <Shell>
            <AppRoutes />
          </Shell>
        </MemoryRouter>
      </AppContext.Provider>
    </AppErrorBoundary>
  );
}
