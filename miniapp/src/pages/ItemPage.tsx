import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchItem, formatPrice, submitRequest, updateCart } from '../api';
import { useApp } from '../App';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { IconPackage } from '../components/Icons';
import { useCheckout } from '../hooks/useCheckout';

export function ItemPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { config, adapter, refreshCart } = useApp();
  const [item, setItem] = useState<Awaited<ReturnType<typeof fetchItem>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [imgIdx, setImgIdx] = useState(0);
  const labels = config?.labels || {};
  const {
    paymentMethod,
    setPaymentMethod,
    busy: checkoutBusy,
    error,
    runCheckout,
    methods,
  } = useCheckout();

  useEffect(() => {
    if (!slug) return;
    fetchItem(slug)
      .then(setItem)
      .finally(() => setLoading(false));
  }, [slug]);

  const buyNow = async () => {
    if (!item) return;
    const result = await runCheckout({
      item_id: item.id,
      quantity: 1,
      use_cart: false,
    });
    if (result?.payment_method === 'admin_cart') {
      navigate('/cart?submitted=1');
    }
  };

  const addToCart = async () => {
    if (!item || !adapter.initData) return;
    setBusy(true);
    try {
      await updateCart(adapter.initData, { item_id: item.id, quantity: 1 });
      await refreshCart();
      navigate('/cart');
    } finally {
      setBusy(false);
    }
  };

  const requestItem = async () => {
    if (!item) return;
    setBusy(true);
    try {
      if (adapter.initData) {
        await submitRequest(adapter.initData, { item_id: item.id, note: 'درخواست از صفحه آیتم' });
      } else {
        adapter.sendData(JSON.stringify({ item_id: item.id, note: 'درخواست' }));
      }
      alert('درخواست شما ثبت شد');
    } finally {
      setBusy(false);
    }
  };

  const isBusy = busy || checkoutBusy;

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton aspect-square rounded-2xl" />
        <div className="mt-4 space-y-2">
          <div className="skeleton h-6 w-2/3" />
          <div className="skeleton h-5 w-1/3" />
        </div>
      </div>
    );
  }
  if (!item) {
    return (
      <div className="empty-state mx-4 mt-8">
        <IconPackage className="h-8 w-8 text-muted/40" />
        <p className="text-sm text-muted">محصول یافت نشد</p>
      </div>
    );
  }

  const images = item.images.length ? item.images : [];

  return (
    <div className="pb-44">
      <div className="relative aspect-square bg-[var(--color-primary-soft)]">
        {images[imgIdx] ? (
          <img src={images[imgIdx]} alt={item.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-muted/30">
            <IconPackage className="h-16 w-16" />
          </div>
        )}
        {images.length > 1 && (
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-1.5">
            {images.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setImgIdx(i)}
                className={`h-1.5 rounded-full transition-all ${
                  i === imgIdx ? 'w-5 bg-primary' : 'w-1.5 bg-white/60'
                }`}
                aria-label={`تصویر ${i + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      <div className="px-4 pt-5">
        <h1 className="text-xl font-bold leading-snug tracking-tight">{item.title}</h1>
        <p className="price-tag mt-2 text-lg">{formatPrice(item.price)}</p>
        {item.short_description && (
          <p className="mt-3 text-sm leading-relaxed text-muted">{item.short_description}</p>
        )}
        {item.description && (
          <div className="mt-5 whitespace-pre-wrap text-sm leading-7 text-[var(--color-text)]/80">
            {item.description}
          </div>
        )}
        {Object.keys(item.metadata || {}).length > 0 && (
          <dl className="mt-5 overflow-hidden rounded-2xl border border-border text-sm">
            {Object.entries(item.metadata).map(([k, v], idx) => (
              <div
                key={k}
                className={`flex justify-between gap-4 px-4 py-3 ${idx > 0 ? 'border-t border-border' : ''}`}
              >
                <dt className="text-muted">{k}</dt>
                <dd className="font-medium">{String(v)}</dd>
              </div>
            ))}
          </dl>
        )}
        {item.is_buyable && config?.is_enabled !== false && methods.length > 0 && (
          <div className="mt-5">
            <PaymentMethodPicker methods={methods} value={paymentMethod} onChange={setPaymentMethod} />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      <div className="bottom-bar mx-auto max-w-lg space-y-2 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        {item.is_buyable && config?.is_enabled !== false && (
          <>
            <button type="button" className="btn-primary" disabled={isBusy} onClick={buyNow}>
              {labels.buy_now || 'خرید'}
            </button>
            <button type="button" className="btn-secondary" disabled={isBusy} onClick={addToCart}>
              {labels.add_to_cart || 'افزودن به سبد'}
            </button>
          </>
        )}
        {item.is_requestable && config?.is_enabled !== false && (
          <button type="button" className="btn-secondary" disabled={isBusy} onClick={requestItem}>
            {labels.request_quote || 'درخواست / تماس'}
          </button>
        )}
      </div>
    </div>
  );
}
