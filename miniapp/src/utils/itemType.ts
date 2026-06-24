const LABELS: Record<string, string> = {
  product: 'محصول',
  download: 'فایل دانلود',
  video: 'ویدیو و آموزش',
  showcase: 'معرفی و نمونه‌کار',
  portfolio: 'معرفی و نمونه‌کار',
};

export function itemTypeLabel(type: string): string {
  return LABELS[type] || 'آیتم';
}

export function isShowcaseType(type: string): boolean {
  return type === 'showcase' || type === 'portfolio';
}

export function isVideoType(type: string): boolean {
  return type === 'video';
}
