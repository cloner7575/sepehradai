import { useState } from 'react';
import { validateAuth } from '../api';
import type { AuthValidateResult } from '../types';
import type { WebAppAdapter } from '../platform';
import { IconAlert } from './Icons';

interface ChannelGateProps {
  adapter: WebAppAdapter;
  auth: AuthValidateResult;
  onUnlocked: (auth: AuthValidateResult) => void;
}

export function ChannelGate({ adapter, auth, onUnlocked }: ChannelGateProps) {
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');

  const recheck = async () => {
    if (!adapter.initData) return;
    setChecking(true);
    setError('');
    try {
      const result = await validateAuth(adapter.initData);
      if (result.is_channel_member) {
        onUnlocked(result);
      } else {
        setError('هنوز عضو کانال نشده‌اید. پس از عضویت دوباره بررسی کنید.');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'بررسی عضویت ناموفق بود');
    } finally {
      setChecking(false);
    }
  };

  const openInvite = () => {
    const link = (auth.channel_invite_link || '').trim();
    if (link) adapter.openLink(link);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[var(--color-bg)] p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50 text-amber-600">
        <IconAlert className="h-7 w-7" />
      </div>
      <div className="max-w-sm space-y-2">
        <h1 className="text-base font-semibold text-[var(--color-text)]">عضویت در کانال</h1>
        <p className="text-sm leading-relaxed text-muted">
          {auth.channel_message || 'برای استفاده از مینی‌اپ ابتدا در کانال ما عضو شوید.'}
        </p>
      </div>
      <div className="flex w-full max-w-xs flex-col gap-3">
        {auth.channel_invite_link ? (
          <button type="button" onClick={openInvite} className="btn-primary w-full">
            عضویت در کانال
          </button>
        ) : null}
        <button
          type="button"
          onClick={recheck}
          disabled={checking}
          className="btn-secondary w-full disabled:opacity-60"
        >
          {checking ? 'در حال بررسی…' : 'بررسی مجدد'}
        </button>
      </div>
      {error ? <p className="max-w-xs text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
