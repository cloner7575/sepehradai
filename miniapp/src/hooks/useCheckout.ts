import { useEffect, useState } from 'react';
import { checkout } from '../api';
import { useApp } from '../App';

export function useCheckout() {
  const { adapter, refreshCart, config } = useApp();
  const [paymentMethod, setPaymentMethod] = useState('admin_cart');

  useEffect(() => {
    if (config?.payment_default) {
      setPaymentMethod(config.payment_default);
    } else if (config?.payment_methods?.[0]?.id) {
      setPaymentMethod(config.payment_methods[0].id);
    }
  }, [config?.payment_default, config?.payment_methods]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const runCheckout = async (body: Record<string, unknown>) => {
    if (!adapter.initData) {
      setError('احراز هویت لازم است');
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
    methods: config?.payment_methods || [],
  };
}
