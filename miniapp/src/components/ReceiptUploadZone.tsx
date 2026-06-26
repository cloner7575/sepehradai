import { useRef, useState } from 'react';
import { IconUpload } from './Icons';

const MAX_BYTES = 10 * 1024 * 1024;

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ReceiptUploadZone({
  preview,
  file,
  disabled,
  onChange,
}: {
  preview: string | null;
  file: File | null;
  disabled?: boolean;
  onChange: (file: File | null, error?: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');

  const pick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleFile = (f: File | null) => {
    setError('');
    if (!f) {
      onChange(null);
      return;
    }
    if (!f.type.startsWith('image/')) {
      setError('فقط تصویر (JPG یا PNG) مجاز است.');
      onChange(null, 'فقط تصویر مجاز است');
      return;
    }
    if (f.size > MAX_BYTES) {
      setError('حداکثر حجم فایل ۱۰ مگابایت است.');
      onChange(null, 'حجم فایل زیاد است');
      return;
    }
    onChange(f);
  };

  return (
    <div className="receipt-upload-zone">
      <p className="text-sm font-semibold mb-3">آپلود رسید واریز</p>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="sr-only"
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0] || null)}
      />
      {preview ? (
        <div className="receipt-preview-wrap animate-fade-in">
          <button type="button" className="receipt-preview-btn" onClick={pick} disabled={disabled}>
            <img src={preview} alt="پیش‌نمایش رسید" className="receipt-preview-img" />
            <span className="receipt-preview-overlay">تغییر تصویر</span>
          </button>
          {file && (
            <div className="receipt-file-chip">
              <span className="truncate">{file.name}</span>
              <span className="shrink-0 text-muted">{formatFileSize(file.size)}</span>
            </div>
          )}
        </div>
      ) : (
        <button type="button" className="receipt-upload-placeholder" onClick={pick} disabled={disabled}>
          <div className="receipt-upload-icon">
            <IconUpload className="h-7 w-7" />
          </div>
          <span className="text-sm font-semibold">انتخاب تصویر رسید</span>
          <span className="text-xs text-muted">JPG یا PNG — حداکثر ۱۰ مگابایت</span>
        </button>
      )}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
