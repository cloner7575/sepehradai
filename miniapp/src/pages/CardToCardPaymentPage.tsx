import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchOrderPayment, formatPrice, uploadOrderReceipt } from '../api';
import type { CardToCardDetails } from '../types';
import { useApp } from '../App';
import { AppHeader } from '../components/AppHeader';
import { CopyButton } from '../components/CopyButton';
import { PaymentStepper } from '../components/PaymentStepper';
import { ReceiptUploadZone } from '../components/ReceiptUploadZone';
import { SuccessView } from '../components/SuccessView';
import { IconCheck, IconChevronLeft } from '../components/Icons';

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
      <p className="bank-card-visual-number" dir="ltr">
        {card.number_display || card.number}
      </p>
      <CopyButton value={card.number} label="کپی شماره کارت" className="copy-btn copy-btn--on-dark" />
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
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted">شماره شبا</p>
        <p className="sheba-block-value" dir="ltr">
          {card.sheba_display || card.sheba}
        </p>
      </div>
      <CopyButton value={card.sheba} label="کپی شبا" className="copy-btn shrink-0" />
    </div>
  );
}

function PaymentSkeleton() {
  return (
    <div className="space-y-5 px-4 pt-3 animate-pulse">
      <div className="skeleton h-10 rounded-2xl" />
      <div className="skeleton h-48 rounded-3xl" />
      <div className="skeleton h-16 rounded-2xl" />
      <div className="skeleton h-40 rounded-2xl" />
    </div>
  );
}

export function CardToCardPaymentPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { adapter, refreshCart, refreshSubscriber } = useApp();
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
  const previewUrlRef = useRef<string | null>(null);

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
        setReceiptUploaded(data.receipt_uploaded || data.status === 'c2c_pending');
        setPaid(data.status === 'paid');
        if (data.receipt_uploaded || data.status === 'c2c_pending') {
          setDone(true);
        }
        if (data.receipt_url) setReceiptPreview(data.receipt_url);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
      })
      .finally(() => setLoading(false));
  }, [adapter.initData, orderId]);

  const onFileChange = (file: File | null) => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setSelectedFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      previewUrlRef.current = url;
      setReceiptPreview(url);
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
      await refreshSubscriber();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'آپلود ناموفق');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (paid) {
      refreshCart();
      refreshSubscriber();
    }
  }, [paid, refreshCart, refreshSubscriber]);

  if (loading) {
    return (
      <div className="card-to-card-page">
        <AppHeader title="پرداخت کارت به کارت" showCart={false} />
        <PaymentSkeleton />
      </div>
    );
  }

  if (paid) {
    return (
      <SuccessView
        icon={<IconCheck className="h-7 w-7" />}
        title="سفارش شما تأیید شد"
        subtitle="پرداخت شما تأیید شده است."
      />
    );
  }

  if (done || (receiptUploaded && !selectedFile)) {
    return (
      <SuccessView
        icon={<IconCheck className="h-7 w-7" />}
        title="رسید دریافت شد"
        subtitle="پس از بررسی واریز، نتیجه از طریق ربات به شما اطلاع داده می‌شود."
      />
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
    <div className="card-to-card-page pb-36 animate-fade-in">
      <AppHeader title="پرداخت کارت به کارت" subtitle={`سفارش #${orderId}`} showCart={false} />

      <div className="space-y-5 px-4 pt-3">
        <PaymentStepper activeStep={selectedFile ? 1 : 0} />

        <div className="order-summary-strip">
          <div>
            <p className="text-xs text-muted">مبلغ قابل واریز</p>
            <p className="text-lg font-bold text-primary">{formatPrice(amount)}</p>
          </div>
          <span className="order-summary-badge">در انتظار پرداخت</span>
        </div>

        <BankCardGraphic card={card} amount={amount} />
        <ShebaBlock card={card} />

        <div className="payment-instructions">
          <p className="text-sm font-semibold">راهنمای پرداخت</p>
          <ol className="mt-2 list-decimal space-y-1.5 pr-4 text-xs leading-relaxed text-muted">
            <li>مبلغ {formatPrice(amount)} را به کارت بالا واریز کنید.</li>
            <li>از رسید واریز عکس بگیرید یا اسکرین‌شات بگیرید.</li>
            <li>تصویر رسید را در بخش زیر آپلود کنید.</li>
          </ol>
        </div>

        <ReceiptUploadZone
          preview={receiptPreview}
          file={selectedFile}
          disabled={busy}
          onChange={onFileChange}
        />

        {error && <div className="cart-error-banner">{error}</div>}
      </div>

      <div className="checkout-footer">
        {!selectedFile && (
          <p className="mb-3 text-center text-xs text-muted">ابتدا تصویر رسید را انتخاب کنید</p>
        )}
        <button
          type="button"
          className="btn-primary checkout-footer-btn"
          disabled={busy || !selectedFile}
          onClick={submitReceipt}
        >
          <span>ارسال رسید</span>
          <IconChevronLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="mt-3 w-full text-center text-sm font-semibold text-muted"
          onClick={() => navigate('/cart')}
        >
          بازگشت به سبد
        </button>
      </div>
    </div>
  );
}
