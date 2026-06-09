const LABELS: Record<string, string> = {
  product: 'محصول',
  portfolio: 'نمونه‌کار',
  service: 'خدمت',
  download: 'دانلود',
};

export function itemTypeLabel(type: string): string {
  return LABELS[type] || 'آیتم';
}
