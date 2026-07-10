import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchItem, fetchItemContent, formatPrice, submitRequest, updateCart } from '../api';
import { useApp } from '../App';
import { CartQuantityControl } from '../components/CartQuantityControl';
import { CheckoutForm, useCheckoutForm } from '../components/CheckoutForm';
import { MediaGallery } from '../components/MediaGallery';
import { GroupContentList } from '../components/GroupContentList';
import { IconCart, IconDownload, IconLock, IconPackage } from '../components/Icons';
import { fileNameFromUrl } from '../utils/media';
import { itemTypeLabel, isGroupParentType, isShowcaseType } from '../utils/itemType';
import type { CatalogItem } from '../types';

export function ItemPage() {
  const { slug } = useParams();
  const { config, adapter, refreshCart, cartItems } = useApp();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [requestError, setRequestError] = useState('');
  const [requestDone, setRequestDone] = useState(false);
  const labels = config?.labels || {};
  const requestForm = useCheckoutForm(config?.checkout_form);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const preview = await fetchItem(slug, adapter.initData || undefined);
        if (cancelled) return;
        if (adapter.initData && (preview.requires_access || preview.has_access)) {
          try {
            const unlocked = await fetchItemContent(slug, adapter.initData);
            if (!cancelled) setItem(unlocked);
            return;
          } catch {
            if (!cancelled) setItem(preview);
            return;
          }
        }
        if (!cancelled) setItem(preview);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug, adapter.initData]);

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
    if (!adapter.initData) {
      setRequestError('برای ثبت درخواست باید از داخل بله/تلگرام وارد شوید.');
      return;
    }
    if (requestForm.hasForm && !requestForm.validate()) {
      setRequestError('لطفاً اطلاعات تماس را کامل کنید.');
      return;
    }
    setBusy(true);
    setRequestError('');
    try {
      await submitRequest(adapter.initData, {
        item_id: item.id,
        note: 'درخواست از صفحه آیتم',
        customer_data: requestForm.customerData,
      });
      setRequestDone(true);
    } catch (e: unknown) {
      setRequestError(e instanceof Error ? e.message : 'ثبت درخواست ناموفق بود');
    } finally {
      setBusy(false);
    }
  };

  const downloadItem = () => {
    if (!item?.download_url) return;
    adapter.openLink(item.download_url);
  };

  const showcase = item ? isShowcaseType(item.item_type) : false;
  const groupParent = item ? isGroupParentType(item.item_type) : false;
  const showBuy =
    item?.is_buyable && !item?.has_access && config?.can_purchase !== false;
  const showDownload = Boolean(item?.is_downloadable && item.download_url && !groupParent);
  const showLockedDownload = Boolean(
    item?.is_downloadable && item.requires_access && !item.has_access && !item.download_url,
  );
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

        {item.requires_access && !item.has_access && !groupParent && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            <IconLock className="h-4 w-4 shrink-0" />
            برای دسترسی به محتوا، ابتدا خرید کنید.
          </div>
        )}

        {item.has_access && item.requires_access && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
            <IconDownload className="h-4 w-4 shrink-0" />
            {groupParent
              ? 'محتوای دوره در همین صفحه قابل مشاهده و دانلود است.'
              : 'شما به این محتوا دسترسی دارید.'}
          </div>
        )}

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
              <span className="text-sm font-medium text-muted">رایگان</span>
            )}
          </div>
        )}

        {groupParent && (item.group_members?.length ?? 0) > 0 && (
          <GroupContentList
            members={item.group_members || []}
            parentType={item.item_type === 'package' ? 'package' : 'course'}
          />
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

        {showRequest && requestForm.hasForm && !requestDone && (
          <div className="mt-6">
            <CheckoutForm
              title={requestForm.title || 'اطلاعات تماس'}
              fields={requestForm.fields}
              values={requestForm.values}
              errors={requestForm.errors}
              onChange={requestForm.setValue}
              disabled={busy}
            />
          </div>
        )}

        {requestError && (
          <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {requestError}
          </p>
        )}

        {requestDone && (
          <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            درخواست شما ثبت شد. به‌زودی با شما تماس گرفته می‌شود.
          </p>
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
        {showLockedDownload && showBuy && (
          <button type="button" className="btn-secondary" disabled>
            <span className="inline-flex items-center justify-center gap-2">
              <IconLock className="h-4 w-4" />
              دانلود پس از خرید
            </span>
          </button>
        )}
        {showRequest && !requestDone && (
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
