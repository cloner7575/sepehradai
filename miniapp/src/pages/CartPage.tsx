import { useEffect, useState, type ReactNode } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { formatPrice, updateCart } from '../api';
import type { CartLine } from '../types';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { CartLineCard } from '../components/CartLineCard';
import { CartSection } from '../components/CartSection';
import { CheckoutForm, useCheckoutForm } from '../components/CheckoutForm';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { IconCart, IconCheck, IconChevronLeft, IconSend } from '../components/Icons';
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
  const [cartBusy, setCartBusy] = useState(false);
  const paid = params.get('paid');
  const {
    paymentMethod,
    setPaymentMethod,
    busy: checkoutBusy,
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
    if (!adapter.initData) {
      setError('احراز هویت لازم است');
      return;
    }
    setCartBusy(true);
    setError('');
    try {
      await updateCart(adapter.initData, { item_id: line.item_id, quantity: qty });
      await refreshCart();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'خطا');
    } finally {
      setCartBusy(false);
    }
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
  const busy = cartBusy || checkoutBusy;
  const itemCount = cartItems.reduce((sum, line) => sum + line.quantity, 0);
  const hasCheckoutStep = checkoutForm.hasForm || methods.length > 0;

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
    <div className="cart-page pb-44">
      <AppHeader
        title={labels.cart || 'سبد خرید'}
        subtitle={cartItems.length > 0 ? `${itemCount} قلم` : undefined}
        showCart={false}
      />

      <div className="px-4 pt-3">
        {cartItems.length === 0 ? (
          <div className="empty-state mt-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-muted/50">
              <IconCart className="h-7 w-7" />
            </div>
            <p className="text-sm font-semibold">سبد خرید خالی است</p>
            <p className="text-xs text-muted">محصولی انتخاب نکرده‌اید</p>
            <Link to="/" className="btn-primary mt-2 max-w-xs">
              مشاهده محصولات
            </Link>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="cart-summary-banner">
              <div className="flex items-center gap-3">
                <div className="cart-summary-icon">
                  <IconCart className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold">{itemCount} قلم در سبد</p>
                  <p className="text-xs text-muted">جمع موقت {formatPrice(cartTotal)}</p>
                </div>
              </div>
              <Link to="/" className="cart-continue-link">
                ادامه خرید
              </Link>
            </div>

            <CartSection step={1} title="محصولات" subtitle="موارد انتخاب‌شده در سبد">
              <div className="cart-lines-panel">
                {cartItems.map((line, idx) => (
                  <div key={line.item_id}>
                    {idx > 0 && <div className="cart-line-divider" />}
                    <CartLineCard
                      line={line}
                      disabled={busy}
                      onChangeQty={(qty) => changeQty(line, qty)}
                    />
                  </div>
                ))}
              </div>
            </CartSection>

            {hasCheckoutStep && (
              <CartSection
                step={2}
                title="تکمیل سفارش"
                subtitle="اطلاعات و روش پرداخت را وارد کنید"
              >
                <div className="cart-checkout-panel">
                  {checkoutForm.hasForm && (
                    <CheckoutForm
                      fields={checkoutForm.fields}
                      values={checkoutForm.values}
                      errors={checkoutForm.errors}
                      onChange={checkoutForm.setValue}
                      disabled={busy}
                      embedded
                    />
                  )}
                  {checkoutForm.hasForm && methods.length > 0 && (
                    <div className="cart-checkout-divider" />
                  )}
                  <PaymentMethodPicker
                    methods={methods}
                    value={paymentMethod}
                    onChange={setPaymentMethod}
                    embedded
                  />
                  {!canPurchase && (
                    <p className="cart-warning">
                      پرداخت هنوز در این فروشگاه فعال نشده است. لطفاً بعداً دوباره تلاش کنید.
                    </p>
                  )}
                </div>
              </CartSection>
            )}
          </div>
        )}

        {error && (
          <div className="cart-error-banner mt-4">
            {error}
          </div>
        )}
      </div>

      {cartItems.length > 0 && (
        <div className="checkout-footer">
          <div className="checkout-footer-summary">
            <div>
              <p className="text-xs text-muted">مبلغ قابل پرداخت</p>
              <p className="checkout-footer-price">{formatPrice(cartTotal)}</p>
            </div>
            <div className="text-left">
              <p className="text-xs text-muted">تعداد</p>
              <p className="text-sm font-bold">{itemCount} قلم</p>
            </div>
          </div>
          <button
            type="button"
            className="btn-primary checkout-footer-btn"
            disabled={busy || !canPurchase}
            onClick={checkoutCart}
          >
            <span>{labels.checkout || 'تسویه حساب'}</span>
            <IconChevronLeft className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
