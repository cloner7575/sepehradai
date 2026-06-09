import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchItem, formatPrice, submitRequest, updateCart } from '../api';
import { useApp } from '../App';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { MediaGallery } from '../components/MediaGallery';
import { IconDownload, IconPackage } from '../components/Icons';
import { useCheckout } from '../hooks/useCheckout';
import { fileNameFromUrl } from '../utils/media';

export function ItemPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { config, adapter, refreshCart } = useApp();
  const [item, setItem] = useState<Awaited<ReturnType<typeof fetchItem>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
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

  const downloadItem = () => {
    if (!item?.download_url) return;
    adapter.openLink(item.download_url);
  };

  const isBusy = busy || checkoutBusy;
  const shopEnabled = config?.is_enabled !== false;
  const showBuy = item?.is_buyable && shopEnabled;
  const showDownload = item?.is_downloadable && item.download_url;

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
        <p className="text-sm text-muted">آیتم یافت نشد</p>
      </div>
    );
  }

  return (
    <div className="pb-44">
      <div className="px-0">
        <MediaGallery item={item} />
      </div>

      <div className="px-4 pt-5">
        <h1 className="text-xl font-bold leading-snug tracking-tight">{item.title}</h1>
        {item.is_downloadable ? (
          <p className="mt-2 text-sm text-muted">
            {fileNameFromUrl(item.download_url)}
          </p>
        ) : (
          <p className="price-tag mt-2 text-lg">{formatPrice(item.price)}</p>
        )}
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
        {showBuy && methods.length > 0 && (
          <div className="mt-5">
            <PaymentMethodPicker methods={methods} value={paymentMethod} onChange={setPaymentMethod} />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      <div className="bottom-bar mx-auto max-w-lg space-y-2 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        {showDownload && (
          <button type="button" className="btn-primary" onClick={downloadItem}>
            <span className="inline-flex items-center justify-center gap-2">
              <IconDownload className="h-4 w-4" />
              {labels.download || 'دانلود'}
            </span>
          </button>
        )}
        {showBuy && (
          <>
            <button type="button" className="btn-primary" disabled={isBusy} onClick={buyNow}>
              {labels.buy_now || 'خرید'}
            </button>
            <button type="button" className="btn-secondary" disabled={isBusy} onClick={addToCart}>
              {labels.add_to_cart || 'افزودن به سبد'}
            </button>
          </>
        )}
        {item.is_requestable && shopEnabled && (
          <button type="button" className="btn-secondary" disabled={isBusy} onClick={requestItem}>
            {labels.request_quote || 'درخواست / تماس'}
          </button>
        )}
      </div>
    </div>
  );
}
