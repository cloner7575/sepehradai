import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Link, MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { fetchCart, fetchConfig } from './api';
import { applyTheme, createWebAppAdapter, type WebAppAdapter } from './platform';
import type { CartLine, CatalogConfig } from './types';
import { HomePage } from './pages/HomePage';
import { CategoryPage } from './pages/CategoryPage';
import { ItemPage } from './pages/ItemPage';
import { CartPage } from './pages/CartPage';

interface AppContextValue {
  config: CatalogConfig | null;
  adapter: WebAppAdapter;
  cartItems: CartLine[];
  cartTotal: number;
  refreshCart: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp outside provider');
  return ctx;
}

function Shell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { adapter, cartItems } = useApp();

  useEffect(() => {
    if (location.pathname === '/') {
      adapter.hideBackButton();
      return;
    }
    adapter.showBackButton(() => navigate(-1));
    return () => adapter.hideBackButton();
  }, [location.pathname, adapter, navigate]);

  const cartCount = cartItems.reduce((s, l) => s + l.quantity, 0);

  return (
    <div className="mx-auto min-h-screen max-w-lg">
      {children}
      <nav className="fixed bottom-0 left-1/2 z-50 flex w-full max-w-lg -translate-x-1/2 border-t border-slate-200 bg-surface/95 px-6 py-2 backdrop-blur md:hidden">
        <div className="flex w-full justify-around text-xs">
          <Link to="/" className={`flex flex-col items-center gap-1 ${location.pathname === '/' ? 'text-primary' : 'text-muted'}`}>
            <span>🏠</span><span>خانه</span>
          </Link>
          <Link to="/cart" className={`relative flex flex-col items-center gap-1 ${location.pathname === '/cart' ? 'text-primary' : 'text-muted'}`}>
            <span>🛒</span><span>سبد</span>
            {cartCount > 0 && (
              <span className="absolute -top-1 left-6 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] text-white">
                {cartCount}
              </span>
            )}
          </Link>
        </div>
      </nav>
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
  const [loading, setLoading] = useState(true);
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
    fetchConfig()
      .then((cfg) => {
        setConfig(cfg);
        const ad = createWebAppAdapter(cfg.platform);
        setAdapter(ad);
        if (!ad.isSupported) setUnsupported(true);
        applyTheme(cfg.theme || {}, ad);
        ad.ready();
        ad.expand();
        if (ad.initData) {
          fetchCart(ad.initData)
            .then((d) => {
              setCartItems(d.items);
              setCartTotal(d.total);
            })
            .catch(() => {});
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(
    () => ({ config, adapter, cartItems, cartTotal, refreshCart }),
    [config, adapter, cartItems, cartTotal, refreshCart],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="skeleton h-12 w-12 rounded-full" />
      </div>
    );
  }

  return (
    <AppContext.Provider value={value}>
      {unsupported && (
        <div className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">
          لطفاً اپلیکیشن بله/تلگرام را به‌روزرسانی کنید.
        </div>
      )}
      <MemoryRouter>
        <Shell>
          <AppRoutes />
        </Shell>
      </MemoryRouter>
    </AppContext.Provider>
  );
}
