import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchOrderPayment, formatPrice, uploadOrderReceipt } from '../api';
import type { CardToCardDetails } from '../types';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { IconCheck, IconChevronLeft } from '../components/Icons';

function copyText(value: string, label: string) {
  if (!value) return;
  navigator.clipboard.writeText(value).then(() => {
    // eslint-disable-next-line no-alert
    alert(`${label} کپی شد`);
  });
}

function BankCardGraphic({
  card,
  amount,
}: {
  card: CardToCardDetails;
  amount: number;
}) {
  return (
    <div className="bank-card-visual">
      <div className="bank-card-visual-bg" aria-hidden />
      <div className="bank-card-visual-chip" aria-hidden />
      <p className="bank-card-visual-label">شماره کارت</p>
      <button
        type="button"
        className="bank-card-visual-number"
        dir="ltr"
        onClick={() => copyText(card.number, 'شماره کارت')}
      >
        {card.number_display || card.number}
      </button>
      <div className="bank-card-visual-row">
        <div>
          <p className="bank-card-visual-label">نام صاحب حساب</p>
          <p className="bank-card-visual-holder">{card.holder}</p>
        </div>
        <div className="text-left">
          <p className="bank-card-visual-label">مبلغ</p>
          <p className="bank-card-visual-amount">{formatPrice(amount)}</p>
        </div>
      </div>
    </div>
  );
}

function ShebaBlock({ card }: { card: CardToCardDetails }) {
  return (
    <div className="sheba-block">
      <div>
        <p className="text-xs text-muted">شماره شبا</p>
        <p className="sheba-block-value" dir="ltr">
          {card.sheba_display || card.sheba}
        </p>
      </div>
      <button
        type="button"
        className="btn-secondary shrink-0 px-3 py-2 text-xs"
        onClick={() => copyText(card.sheba, 'شماره شبا')}
      >
        کپی شبا
      </button>
    </div>
  );
}

export function CardToCardPaymentPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { adapter, refreshCart } = useApp();
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [amount, setAmount] = useState(0);
  const [card, setCard] = useState<CardToCardDetails | null>(null);
  const [receiptUploaded, setReceiptUploaded] = useState(false);
  const [receiptPreview, setReceiptPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [done, setDone] = useState(false);
  const [paid, setPaid] = useState(false);

  useEffect(() => {
    if (!adapter.initData || !orderId) {
      setError('اطلاعات سفارش نامعتبر است');
      setLoading(false);
      return;
    }
    fetchOrderPayment(adapter.initData, Number(orderId))
      .then((data) => {
        setAmount(data.amount);
        setCard(data.card);
        setReceiptUploaded(data.receipt_uploaded);
        setPaid(data.status === 'paid');
        if (data.receipt_url) setReceiptPreview(data.receipt_url);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
      })
      .finally(() => setLoading(false));
  }, [adapter.initData, orderId]);

  const onFileChange = (file: File | null) => {
    setSelectedFile(file);
    if (file) {
      setReceiptPreview(URL.createObjectURL(file));
    }
  };

  const submitReceipt = async () => {
    if (!adapter.initData || !orderId || !selectedFile) return;
    setBusy(true);
    setError('');
    try {
      await uploadOrderReceipt(adapter.initData, Number(orderId), selectedFile);
      setReceiptUploaded(true);
      setDone(true);
      await refreshCart();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'آپلود ناموفق');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-muted">
        در حال بارگذاری...
      </div>
    );
  }

  if (paid) {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center px-8 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-primary">
          <IconCheck className="h-7 w-7" />
        </div>
        <h1 className="text-lg font-bold">سفارش شما تأیید شد</h1>
        <p className="mt-2 text-sm text-muted">پرداخت شما تأیید شده است.</p>
        <Link to="/" className="btn-primary mt-8 max-w-xs">
          بازگشت به ویترین
        </Link>
      </div>
    );
  }

  if (done || (receiptUploaded && !selectedFile)) {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center px-8 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-primary">
          <IconCheck className="h-7 w-7" />
        </div>
        <h1 className="text-lg font-bold">رسید دریافت شد</h1>
        <p className="mt-2 text-sm text-muted">
          پس از بررسی واریز، نتیجه از طریق ربات به شما اطلاع داده می‌شود.
        </p>
        <Link to="/" className="btn-primary mt-8 max-w-xs">
          بازگشت به ویترین
        </Link>
      </div>
    );
  }

  if (!card) {
    return (
      <div className="px-4 py-8 text-center text-sm text-red-600">
        {error || 'اطلاعات پرداخت یافت نشد'}
      </div>
    );
  }

  return (
    <div className="card-to-card-page pb-32">
      <AppHeader title="پرداخت کارت به کارت" subtitle={`سفارش #${orderId}`} showCart={false} />

      <div className="space-y-5 px-4 pt-3">
        <div className="payment-steps-banner">
          <span className="payment-step is-active">۱. واریز</span>
          <span className="payment-step">۲. آپلود رسید</span>
          <span className="payment-step">۳. تأیید</span>
        </div>

        <BankCardGraphic card={card} amount={amount} />
        <ShebaBlock card={card} />

        <div className="payment-instructions">
          <p className="text-sm font-semibold">راهنمای پرداخت</p>
          <ol className="mt-2 list-decimal space-y-1 pr-4 text-xs text-muted">
            <li>مبلغ {formatPrice(amount)} را به کارت بالا واریز کنید.</li>
            <li>از رسید واریز عکس بگیرید یا اسکرین‌شات بگیرید.</li>
            <li>تصویر رسید را در بخش زیر آپلود کنید.</li>
          </ol>
        </div>

        <div className="receipt-upload-panel">
          <p className="text-sm font-semibold mb-3">آپلود رسید واریز</p>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="sr-only"
            onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          />
          {receiptPreview ? (
            <button type="button" className="receipt-preview-btn" onClick={() => fileRef.current?.click()}>
              <img src={receiptPreview} alt="پیش‌نمایش رسید" className="receipt-preview-img" />
              <span className="text-xs text-muted">برای تغییر تصویر بزنید</span>
            </button>
          ) : (
            <button type="button" className="receipt-upload-placeholder" onClick={() => fileRef.current?.click()}>
              <span className="text-3xl">📎</span>
              <span className="text-sm font-medium">انتخاب تصویر رسید</span>
              <span className="text-xs text-muted">JPG یا PNG — حداکثر ۱۰ مگابایت</span>
            </button>
          )}
        </div>

        {error && <div className="cart-error-banner">{error}</div>}
      </div>

      <div className="checkout-footer">
        <button
          type="button"
          className="btn-primary checkout-footer-btn"
          disabled={busy || !selectedFile}
          onClick={submitReceipt}
        >
          <span>ارسال رسید</span>
          <IconChevronLeft className="h-4 w-4" />
        </button>
        <button type="button" className="btn-secondary w-full mt-2" onClick={() => navigate('/cart')}>
          بازگشت به سبد
        </button>
      </div>
    </div>
  );
}
