import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { formatPrice, updateCart } from '../api';
import type { CartLine } from '../types';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { CartLineCard } from '../components/CartLineCard';
import { CartSection } from '../components/CartSection';
import { CheckoutForm, useCheckoutForm } from '../components/CheckoutForm';
import { DiscountCodeField } from '../components/DiscountCodeField';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { SuccessView } from '../components/SuccessView';
import { IconCart, IconCheck, IconChevronLeft, IconSend } from '../components/Icons';
import { useCheckout } from '../hooks/useCheckout';

export function CartPage() {
  const {
    adapter,
    refreshCart,
    refreshSubscriber,
    cartTotal,
    cartSubtotal,
    cartShipping,
    cartDiscount,
    freeShipping,
    cartItems,
    config,
  } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [cartBusy, setCartBusy] = useState(false);
  const [discountCode, setDiscountCode] = useState('');
  const [appliedCode, setAppliedCode] = useState('');
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

  const submitted = params.get('submitted');
  const baleInvoice = params.get('bale_invoice');

  useEffect(() => {
    if (paid || submitted || baleInvoice) {
      refreshCart();
      refreshSubscriber();
    }
  }, [paid, submitted, baleInvoice, refreshCart, refreshSubscriber]);

  const applyDiscount = async () => {
    const code = discountCode.trim();
    await refreshCart({ discount_code: code || undefined });
    setAppliedCode(code);
  };

  const changeQty = async (line: CartLine, qty: number) => {
    if (!adapter.initData) {
      setError('احراز هویت لازم است');
      return;
    }
    setCartBusy(true);
    setError('');
    try {
      await updateCart(adapter.initData, { item_id: line.item_id, quantity: qty });
      await refreshCart({ discount_code: appliedCode || undefined });
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
      discount_code: appliedCode || undefined,
    });
    if (result?.payment_method === 'admin_cart') {
      navigate('/cart?submitted=1');
    } else if (result?.payment_method === 'card_to_card' || result?.method === 'card_to_card') {
      navigate(`/payment/${result.order_id}`);
    } else if (result?.payment_method === 'bale' || result?.method === 'bale_invoice') {
      navigate('/cart?bale_invoice=1');
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

  if (params.get('bale_invoice')) {
    return (
      <SuccessView
        icon={<IconSend className="h-7 w-7" />}
        title="صورت‌حساب ارسال شد"
        subtitle="صورت‌حساب به گفت‌وگوی شما در بله ارسال شد؛ برای تکمیل خرید، روی پرداخت بزنید."
      />
    );
  }

  return (
    <div className="cart-page pb-44 animate-fade-in">
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
                  <DiscountCodeField
                    value={discountCode}
                    appliedCode={appliedCode}
                    onChange={(v) => {
                      setDiscountCode(v);
                      if (!v.trim()) {
                        setAppliedCode('');
                        refreshCart();
                      }
                    }}
                    onApply={applyDiscount}
                    appliedAmount={cartDiscount}
                    disabled={busy}
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

        {error && <div className="cart-error-banner mt-4">{error}</div>}
      </div>

      {cartItems.length > 0 && (
        <div className="checkout-footer">
          <div className="checkout-footer-summary">
            <div>
              <p className="text-xs text-muted">مبلغ قابل پرداخت</p>
              <p className="checkout-footer-price">{formatPrice(cartTotal)}</p>
              {cartSubtotal > 0 && cartSubtotal !== cartTotal && (
                <p className="text-xs text-muted">جمع کالا {formatPrice(cartSubtotal)}</p>
              )}
              {cartShipping > 0 && (
                <p className="text-xs text-muted">ارسال {formatPrice(cartShipping)}</p>
              )}
              {freeShipping && cartSubtotal > 0 && (
                <p className="text-xs text-green-600">ارسال رایگان</p>
              )}
              {cartDiscount > 0 && (
                <p className="text-xs text-green-600">تخفیف {formatPrice(cartDiscount)}</p>
              )}
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
