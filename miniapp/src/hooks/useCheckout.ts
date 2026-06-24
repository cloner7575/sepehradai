import { useEffect, useState } from 'react';
import { checkout } from '../api';
import { useApp } from '../App';

function resolveDefaultMethod(
  methods: { id: string }[],
  preferred?: string,
): string {
  if (!methods.length) return '';
  if (preferred && methods.some((m) => m.id === preferred)) return preferred;
  return methods[0].id;
}

export function useCheckout() {
  const { adapter, refreshCart, config } = useApp();
  const methods = config?.payment_methods || [];
  const [paymentMethod, setPaymentMethod] = useState(() =>
    resolveDefaultMethod(methods, config?.payment_default),
  );

  useEffect(() => {
    const list = config?.payment_methods || [];
    setPaymentMethod(resolveDefaultMethod(list, config?.payment_default));
  }, [config?.payment_methods, config?.payment_default]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const runCheckout = async (body: Record<string, unknown>) => {
    if (!adapter.initData) {
      setError('احراز هویت لازم است');
      return null;
    }
    if (!methods.length || !paymentMethod) {
      setError('روش پرداخت فعالی برای این فروشگاه تنظیم نشده است');
      return null;
    }
    setBusy(true);
    setError('');
    try {
      const result = await checkout(adapter.initData, {
        payment_method: paymentMethod,
        ...body,
      });
      if (result.payment_method === 'zarinpal' && result.payment_url) {
        adapter.openLink(result.payment_url);
      } else if (result.payment_method === 'admin_cart') {
        await refreshCart();
      }
      return result;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'خطا در تسویه');
      return null;
    } finally {
      setBusy(false);
    }
  };

  return {
    paymentMethod,
    setPaymentMethod,
    busy,
    error,
    setError,
    runCheckout,
    methods,
    canPurchase: config?.can_purchase ?? (methods.length > 0 && config?.is_enabled !== false),
  };
}
