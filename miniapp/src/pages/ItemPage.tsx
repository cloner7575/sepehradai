import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchItem, formatPrice, submitRequest, updateCart } from '../api';
import { useApp } from '../App';
import { CartQuantityControl } from '../components/CartQuantityControl';
import { MediaGallery } from '../components/MediaGallery';
import { IconCart, IconDownload, IconPackage } from '../components/Icons';
import { fileNameFromUrl } from '../utils/media';
import { itemTypeLabel, isShowcaseType } from '../utils/itemType';

export function ItemPage() {
  const { slug } = useParams();
  const { config, adapter, refreshCart, cartItems } = useApp();
  const [item, setItem] = useState<Awaited<ReturnType<typeof fetchItem>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const labels = config?.labels || {};

  useEffect(() => {
    if (!slug) return;
    fetchItem(slug)
      .then(setItem)
      .finally(() => setLoading(false));
  }, [slug]);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const cartQty = item ? cartItems.find((l) => l.item_id === item.id)?.quantity ?? 0 : 0;

  const updateQty = async (qty: number) => {
    if (!item || !adapter.initData) return;
    setBusy(true);
    try {
      await updateCart(adapter.initData, { item_id: item.id, quantity: qty });
      await refreshCart();
    } finally {
      setBusy(false);
    }
  };

  const addToCart = () => updateQty(1);

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

  const showcase = item ? isShowcaseType(item.item_type) : false;
  const showBuy = item?.is_buyable && config?.can_purchase !== false;
  const showDownload = item?.is_downloadable && item.download_url;
  const showRequest = item?.is_requestable && config?.is_enabled !== false;
  const lineTotal = item?.price != null && cartQty > 0 ? item.price * cartQty : null;

  if (loading) {
    return (
      <div className="p-4">
        <div className="skeleton aspect-[4/3] rounded-2xl" />
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
    <div className="pb-40">
      <MediaGallery item={item} />

      <div className="item-detail-panel mx-4">
        <div className="flex items-start justify-between gap-3">
          <span className="item-detail-badge">{itemTypeLabel(item.item_type)}</span>
          {cartQty > 0 && (
            <span className="inline-flex items-center gap-1 rounded-xl bg-[var(--color-primary-soft)] px-2.5 py-1 text-xs font-semibold text-primary">
              <IconCart className="h-3.5 w-3.5" />
              {cartQty} در سبد
            </span>
          )}
        </div>
        <h1 className="mt-2 text-xl font-bold leading-snug tracking-tight">{item.title}</h1>

        {!showcase && (
          <div className="item-detail-price-row mt-4">
            {item.is_downloadable && item.download_url ? (
              <p className="truncate text-sm text-muted" dir="ltr">
                {fileNameFromUrl(item.download_url)}
              </p>
            ) : item.price != null ? (
              <>
                <span className="text-2xl font-bold tracking-tight text-primary">
                  {formatPrice(item.price)}
                </span>
                {lineTotal != null && cartQty > 1 && (
                  <span className="text-xs text-muted">
                    جمع {cartQty} عدد: {formatPrice(lineTotal)}
                  </span>
                )}
              </>
            ) : (
              <span className="text-sm font-medium text-muted">تماس بگیرید</span>
            )}
          </div>
        )}

        {showcase && (
          <p className="mt-4 text-sm leading-relaxed text-muted">
            برای سفارش یا همکاری درخواست ثبت کنید.
          </p>
        )}

        {item.short_description && (
          <p className="mt-4 text-sm leading-relaxed text-muted">{item.short_description}</p>
        )}

        {item.description && (
          <div className="mt-6">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">توضیحات</h2>
            <div className="whitespace-pre-wrap text-sm leading-7 text-[var(--color-text)]/85">
              {item.description}
            </div>
          </div>
        )}

        {Object.keys(item.metadata || {}).length > 0 && (
          <dl className="mt-6 overflow-hidden rounded-2xl border border-border text-sm">
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
      </div>

      <div className="bottom-bar mx-auto max-w-lg space-y-2 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        {showBuy && (
          <div className="space-y-2">
            {cartQty > 0 ? (
              <div className="flex items-center gap-2">
                <CartQuantityControl
                  quantity={cartQty}
                  disabled={busy}
                  size="lg"
                  onChange={updateQty}
                />
                <Link to="/cart" className="btn-secondary !w-auto shrink-0 px-5">
                  <span className="inline-flex items-center gap-1.5">
                    <IconCart className="h-4 w-4" />
                    سبد
                  </span>
                </Link>
              </div>
            ) : (
              <button type="button" className="btn-primary" disabled={busy} onClick={addToCart}>
                {labels.add_to_cart || 'افزودن به سبد'}
              </button>
            )}
          </div>
        )}
        {showDownload && (
          <button type="button" className="btn-primary" onClick={downloadItem}>
            <span className="inline-flex items-center justify-center gap-2">
              <IconDownload className="h-4 w-4" />
              {labels.download || 'دانلود'}
            </span>
          </button>
        )}
        {showRequest && (
          <button
            type="button"
            className={showBuy || showDownload ? 'btn-secondary' : 'btn-primary'}
            disabled={busy}
            onClick={requestItem}
          >
            {labels.request_quote || (showcase ? 'درخواست همکاری' : 'درخواست / تماس')}
          </button>
        )}
      </div>
    </div>
  );
}
