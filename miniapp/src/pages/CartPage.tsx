import { useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { formatPrice, updateCart } from '../api';
import type { CartLine } from '../types';
import { useApp } from '../App';
import { PaymentMethodPicker } from '../components/PaymentMethodPicker';
import { useCheckout } from '../hooks/useCheckout';

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
  } = useCheckout();

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

  const checkoutCart = async () => {
    const result = await runCheckout({ use_cart: true });
    if (result?.payment_method === 'admin_cart') {
      navigate('/cart?submitted=1');
    }
  };

  const labels = config?.labels || {};

  if (paid) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
        <div className="text-5xl mb-4">✅</div>
        <h1 className="text-xl font-bold">پرداخت موفق</h1>
        <Link to="/" className="btn-primary mt-6 max-w-xs">بازگشت به فروشگاه</Link>
      </div>
    );
  }

  if (params.get('submitted')) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
        <div className="text-5xl mb-4">📨</div>
        <h1 className="text-xl font-bold">سبد برای ادمین ارسال شد</h1>
        <p className="mt-2 text-muted">به‌زودی با شما تماس گرفته می‌شود.</p>
        <Link to="/" className="btn-primary mt-6 max-w-xs">بازگشت به فروشگاه</Link>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 pb-32">
      <h1 className="mb-4 text-xl font-bold">{labels.cart || 'سبد خرید'}</h1>
      {cartItems.length === 0 ? (
        <div className="card p-8 text-center text-muted">
          سبد خرید خالی است
          <Link to="/" className="btn-primary mt-4 inline-block">مشاهده محصولات</Link>
        </div>
      ) : (
        <>
          <PaymentMethodPicker methods={methods} value={paymentMethod} onChange={setPaymentMethod} />
          <div className="space-y-3">
            {cartItems.map((line) => (
              <div key={line.item_id} className="card flex gap-3 p-3">
                <div className="flex-1">
                  <div className="font-semibold">{line.title}</div>
                  <div className="text-sm text-primary">{formatPrice(line.price)}</div>
                  <div className="mt-2 flex items-center gap-3">
                    <button
                      type="button"
                      className="h-8 w-8 rounded-lg bg-slate-100"
                      disabled={busy}
                      onClick={() => changeQty(line, line.quantity - 1)}
                    >
                      −
                    </button>
                    <span>{line.quantity}</span>
                    <button
                      type="button"
                      className="h-8 w-8 rounded-lg bg-slate-100"
                      disabled={busy}
                      onClick={() => changeQty(line, line.quantity + 1)}
                    >
                      +
                    </button>
                  </div>
                </div>
                <div className="text-sm font-bold">{formatPrice(line.line_total)}</div>
              </div>
            ))}
          </div>
        </>
      )}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {cartItems.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 border-t bg-surface/95 p-4 backdrop-blur">
          <div className="mb-3 flex justify-between font-bold">
            <span>جمع کل</span>
            <span className="text-primary">{formatPrice(cartTotal)}</span>
          </div>
          <button type="button" className="btn-primary" disabled={busy} onClick={checkoutCart}>
            {labels.checkout || 'تسویه'}
          </button>
        </div>
      )}
    </div>
  );
}
