import { useEffect, type ReactNode } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { formatPrice, updateCart } from '../api';
import type { CartLine } from '../types';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { CheckoutForm, useCheckoutForm } from '../components/CheckoutForm';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { IconCart, IconCheck, IconPackage, IconSend, IconTrash } from '../components/Icons';
import { useCheckout } from '../hooks/useCheckout';

function SuccessView({
  icon,
  title,
  subtitle,
}: {
  icon: ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-8 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-primary">
        {icon}
      </div>
      <h1 className="text-lg font-bold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-2 text-sm text-muted">{subtitle}</p>}
      <Link to="/" className="btn-primary mt-8 max-w-xs">
        بازگشت به ویترین
      </Link>
    </div>
  );
}

export function CartPage() {
  const { adapter, refreshCart, cartTotal, cartItems, config } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const paid = params.get('paid');
  const {
    paymentMethod,
    setPaymentMethod,
    busy,
    error,
    setError,
    runCheckout,
    methods,
    canPurchase,
  } = useCheckout();
  const checkoutForm = useCheckoutForm(config?.checkout_form);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const changeQty = async (line: CartLine, qty: number) => {
    if (!adapter.initData) return;
    setError('');
    try {
      await updateCart(adapter.initData, { item_id: line.item_id, quantity: qty });
      await refreshCart();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'خطا');
    }
  };

  const removeLine = async (line: CartLine) => {
    await changeQty(line, 0);
  };

  const checkoutCart = async () => {
    if (checkoutForm.hasForm && !checkoutForm.validate()) return;
    const result = await runCheckout({
      use_cart: true,
      customer_data: checkoutForm.customerData,
    });
    if (result?.payment_method === 'admin_cart') {
      navigate('/cart?submitted=1');
    }
  };

  const labels = config?.labels || {};

  if (paid) {
    return (
      <SuccessView
        icon={<IconCheck className="h-7 w-7" />}
        title="پرداخت موفق"
        subtitle="سفارش شما با موفقیت ثبت شد."
      />
    );
  }

  if (params.get('submitted')) {
    return (
      <SuccessView
        icon={<IconSend className="h-7 w-7" />}
        title="سفارش ثبت شد"
        subtitle="به‌زودی با شما تماس گرفته می‌شود."
      />
    );
  }

  return (
    <div className="pb-36">
      <AppHeader
        title={labels.cart || 'سبد خرید'}
        subtitle={cartItems.length > 0 ? `${cartItems.length} قلم` : undefined}
        showCart={false}
      />

      <div className="px-4 pt-4">
        {cartItems.length === 0 ? (
          <div className="empty-state">
            <IconCart className="h-8 w-8 text-muted/40" />
            <p className="text-sm text-muted">سبد خرید خالی است</p>
            <Link to="/" className="btn-primary mt-2 max-w-xs">
              مشاهده محصولات
            </Link>
          </div>
        ) : (
          <>
            <CheckoutForm
              title={checkoutForm.title}
              fields={checkoutForm.fields}
              values={checkoutForm.values}
              errors={checkoutForm.errors}
              onChange={checkoutForm.setValue}
              disabled={busy}
            />
            <PaymentMethodPicker methods={methods} value={paymentMethod} onChange={setPaymentMethod} />
            {!canPurchase && (
              <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
                پرداخت هنوز در این فروشگاه فعال نشده است. لطفاً بعداً دوباره تلاش کنید.
              </p>
            )}
            <div className="space-y-3">
              {cartItems.map((line) => (
                <div key={line.item_id} className="card flex gap-3 p-3">
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-[var(--color-primary-soft)]">
                    {line.image ? (
                      <img src={line.image} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted/30">
                        <IconPackage className="h-6 w-6" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate text-sm font-semibold">{line.title}</div>
                      <button
                        type="button"
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-red-500 transition active:scale-95 disabled:opacity-40"
                        disabled={busy}
                        onClick={() => removeLine(line)}
                        aria-label={labels.remove_from_cart || 'حذف'}
                        title={labels.remove_from_cart || 'حذف'}
                      >
                        <IconTrash className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="price-tag mt-0.5">{formatPrice(line.price)}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        type="button"
                        className="qty-btn"
                        disabled={busy}
                        onClick={() => changeQty(line, line.quantity - 1)}
                        aria-label="کاهش"
                      >
                        −
                      </button>
                      <span className="w-6 text-center text-sm font-medium">{line.quantity}</span>
                      <button
                        type="button"
                        className="qty-btn"
                        disabled={busy}
                        onClick={() => changeQty(line, line.quantity + 1)}
                        aria-label="افزایش"
                      >
                        +
                      </button>
                    </div>
                  </div>
                  <div className="shrink-0 text-sm font-bold">{formatPrice(line.line_total)}</div>
                </div>
              ))}
            </div>
          </>
        )}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>

      {cartItems.length > 0 && (
        <div className="bottom-bar mx-auto max-w-lg p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm text-muted">جمع کل</span>
            <span className="text-lg font-bold text-primary">{formatPrice(cartTotal)}</span>
          </div>
          <button type="button" className="btn-primary" disabled={busy || !canPurchase} onClick={checkoutCart}>
            {labels.checkout || 'تسویه حساب'}
          </button>
        </div>
      )}
    </div>
  );
}
