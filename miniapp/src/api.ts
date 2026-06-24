import type { AuthValidateResult, CartLine, CatalogConfig, CatalogItem, Category, CheckoutResult } from './types';

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

export async function fetchItems(params?: {
  category?: string;
  q?: string;
  sort?: string;
  featured?: boolean;
}) {
  const qs = new URLSearchParams();
  if (params?.category) qs.set('category', params.category);
  if (params?.q) qs.set('q', params.q);
  if (params?.sort) qs.set('sort', params.sort);
  if (params?.featured) qs.set('featured', '1');
  const suffix = qs.toString() ? `?${qs}` : '';
  const data = await request<{ items: CatalogItem[] }>(`/items/${suffix}`);
  return data.items;
}

export async function fetchItem(slug: string) {
  const data = await request<{ item: CatalogItem }>(`/items/${slug}/`);
  return data.item;
}

export async function fetchCart(initData: string) {
  return request<{ items: CartLine[]; total: number }>(`/cart/?initData=${encodeURIComponent(initData)}`);
}

export async function updateCart(initData: string, body: Record<string, unknown>) {
  return request<{ items: CartLine[]; total: number }>('/cart/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body }),
  });
}

export async function checkout(initData: string, body: Record<string, unknown> = {}) {
  return request<CheckoutResult>('/checkout/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body }),
  });
}

export async function submitRequest(initData: string, body: Record<string, unknown>) {
  return request<{ order_id: number }>('/request/', {
    method: 'POST',
    body: JSON.stringify({ initData, ...body }),
  });
}

export function formatPrice(amount: number | null | undefined) {
  if (amount == null) return 'تماس بگیرید';
  return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
}
