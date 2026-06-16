import { useState, type ReactNode } from 'react';
import { resolveMediaUrl } from '../utils/url';

interface SafeImageProps {
  src: string;
  alt?: string;
  className?: string;
  fallback: ReactNode;
}

export function SafeImage({ src, alt = '', className = '', fallback }: SafeImageProps) {
  const [failed, setFailed] = useState(false);
  const resolved = resolveMediaUrl(src);

  if (!resolved || failed) {
    return <>{fallback}</>;
  }

  return (
    <img
      src={resolved}
      alt={alt}
      className={className}
      loading="eager"
      decoding="sync"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  );
}
