import type { AuthValidateResult, CartLine, CartSummary, CatalogConfig, CatalogItem, Category, CheckoutResult, OrderPaymentInfo } from './types';

function getPublicId(): string {
  const parts = window.location.pathname.split('/').filter(Boolean);
  const shopIdx = parts.indexOf('shop');
  if (shopIdx >= 0 && parts[shopIdx + 1]) {
    return parts[shopIdx + 1];
  }
  return parts[0] || '';
}

const PUBLIC_ID = getPublicId();
const API_BASE = `/api/shop/${PUBLIC_ID}`;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  let data: { ok?: boolean; error?: string };
  try {
    data = await res.json();
  } catch {
    throw new Error(res.status === 404 ? 'مینی‌اپ یافت نشد' : `خطای سرور (${res.status})`);
  }
  if (!data.ok) {
    throw new Error(data.error || 'خطای سرور');
  }
  return data as T;
}

export function getPublicIdValue() {
  return PUBLIC_ID;
}

export async function fetchConfig(): Promise<CatalogConfig & { ok?: boolean }> {
  return request<CatalogConfig & { ok?: boolean }>('/config/');
}

export async function validateAuth(initData: string): Promise<AuthValidateResult> {
  return request<AuthValidateResult>('/auth/validate/', {
    method: 'POST',
    body: JSON.stringify({ initData }),
  });
}

export async function fetchCategories() {
  const data = await request<{ categories: Category[] }>('/categories/');
  return data.categories;
}

export async function fetchItems(
  params?: {
    category?: string;
    q?: string;
    sort?: string;
    featured?: boolean;
    source?: string;
    tag?: string;
    limit?: number;
  },
  initData?: string,
) {
  const qs = new URLSearchParams();
  if (params?.category) qs.set('category', params.category);
  if (params?.q) qs.set('q', params.q);
  if (params?.sort) qs.set('sort', params.sort);
  if (params?.featured) qs.set('featured', '1');
  if (params?.source) qs.set('source', params.source);
  if (params?.tag) qs.set('tag', params.tag);
  if (params?.limit) qs.set('limit', String(params.limit));
  if (initData) qs.set('initData', initData);
  const suffix = qs.toString() ? `?${qs}` : '';
  const data = await request<{ items: CatalogItem[] }>(`/items/${suffix}`);
  return data.items;
}

export async function fetchItem(slug: string, initData?: string) {
  const qs = initData ? `?initData=${encodeURIComponent(initData)}` : '';
  const data = await request<{ item: CatalogItem }>(`/items/${slug}${qs}`);
  return data.item;
}

export async function fetchItemContent(slug: string, initData: string) {
  const data = await request<{ item: CatalogItem }>(`/items/${slug}/content/`, {
    method: 'POST',
    body: JSON.stringify({ initData }),
  });
  return data.item;
}

export async function fetchLibrary(initData: string) {
  const data = await request<{ items: CatalogItem[] }>('/library/', {
    method: 'POST',
    body: JSON.stringify({ initData }),
  });
  return data.items;
}

export async function fetchCart(
  initData: string,
  params?: { province?: string; discount_code?: string },
) {
  const qs = new URLSearchParams({ initData });
  if (params?.province) qs.set('province', params.province);
  if (params?.discount_code) qs.set('discount_code', params.discount_code);
  return request<CartSummary & { ok?: boolean }>(`/cart/?${qs}`);
}

export async function updateCart(
  initData: string,
  body: Record<string, unknown>,
  params?: { province?: string; discount_code?: string },
) {
  return request<CartSummary & { ok?: boolean }>('/cart/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body, ...params }),
  });
}

export async function checkout(initData: string, body: Record<string, unknown> = {}) {
  return request<CheckoutResult>('/checkout/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body }),
  });
}

export async function fetchOrderPayment(initData: string, orderId: number) {
  const qs = new URLSearchParams({ initData });
  return request<OrderPaymentInfo>(`/orders/${orderId}/payment/?${qs}`);
}

export async function uploadOrderReceipt(initData: string, orderId: number, file: File) {
  const form = new FormData();
  form.append('initData', initData);
  form.append('receipt', file);
  const res = await fetch(`${API_BASE}/orders/${orderId}/receipt/`, {
    method: 'POST',
    body: form,
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.error || 'خطای سرور');
  }
  return data;
}

export async function submitRequest(initData: string, body: Record<string, unknown>) {
  return request<{ order_id: number }>('/request/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body }),
  });
}

export function formatPrice(amount: number | null | undefined) {
  if (amount == null) return 'تماس بگیرید';
  const toman = Math.floor(amount / 10);
  return new Intl.NumberFormat('fa-IR').format(toman) + ' تومان';
}
