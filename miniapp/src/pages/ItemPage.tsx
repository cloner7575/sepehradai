import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchItem, formatPrice, submitRequest, updateCart } from '../api';
import { useApp } from '../App';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
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

  if (loading) return <div className="p-4"><div className="skeleton h-64 rounded-2xl" /></div>;
  if (!item) return <div className="p-8 text-center text-muted">آیتم یافت نشد</div>;

  const images = item.images.length ? item.images : [];

  return (
    <div className="pb-40">
      <div className="aspect-square bg-slate-100 relative">
        {images[imgIdx] ? (
          <img src={images[imgIdx]} alt={item.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-6xl text-slate-300">📦</div>
        )}
        {images.length > 1 && (
          <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-2">
            {images.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setImgIdx(i)}
                className={`h-2 w-2 rounded-full ${i === imgIdx ? 'bg-primary' : 'bg-white/70'}`}
              />
            ))}
          </div>
        )}
      </div>
      <div className="px-4 pt-4">
        <h1 className="text-2xl font-bold">{item.title}</h1>
        <p className="mt-2 text-lg font-semibold text-primary">{formatPrice(item.price)}</p>
        {item.short_description && <p className="mt-2 text-muted">{item.short_description}</p>}
        {item.description && (
          <div className="mt-4 whitespace-pre-wrap text-sm leading-7">{item.description}</div>
        )}
        {Object.keys(item.metadata || {}).length > 0 && (
          <dl className="mt-4 card divide-y text-sm">
            {Object.entries(item.metadata).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 px-4 py-2">
                <dt className="text-muted">{k}</dt>
                <dd className="font-medium">{String(v)}</dd>
              </div>
            ))}
          </dl>
        )}
        {item.is_buyable && methods.length > 0 && (
          <div className="mt-4">
            <PaymentMethodPicker methods={methods} value={paymentMethod} onChange={setPaymentMethod} />
          </div>
        )}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>
      <div className="fixed bottom-0 left-0 right-0 border-t border-slate-200 bg-surface/95 p-4 backdrop-blur space-y-2">
        {item.is_buyable && (
          <>
            <button type="button" className="btn-primary" disabled={isBusy} onClick={buyNow}>
              {labels.buy_now || 'خرید'}
            </button>
            <button type="button" className="btn-secondary" disabled={isBusy} onClick={addToCart}>
              {labels.add_to_cart || 'افزودن به سبد'}
            </button>
          </>
        )}
        {item.is_requestable && (
          <button type="button" className="btn-secondary" disabled={isBusy} onClick={requestItem}>
            {labels.request_quote || 'درخواست / تماس'}
          </button>
        )}
      </div>
    </div>
  );
}
