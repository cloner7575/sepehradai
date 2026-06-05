export interface PaymentMethodOption {
  id: string;
  label: string;
}

export interface CatalogConfig {
  platform: string;
  hero_title: string;
  hero_subtitle: string;
  theme: Record<string, string>;
  labels: Record<string, string>;
  logo_url: string;
  payment_methods?: PaymentMethodOption[];
  payment_default?: string;
}

export interface CheckoutResult {
  order_id: number;
  payment_method: string;
  status?: string;
  message?: string;
  payment_url?: string;
}

export interface Category {
  id: number;
  slug: string;
  name: string;
  icon: string;
  parent_id: number | null;
}

export interface CatalogItem {
  id: number;
  slug: string;
  title: string;
  short_description: string;
  description: string;
  item_type: string;
  price: number | null;
  sale_mode: string;
  is_buyable: boolean;
  is_requestable: boolean;
  is_featured: boolean;
  metadata: Record<string, unknown>;
  images: string[];
  category_id: number | null;
  category_slug: string | null;
}

export interface CartLine {
  item_id: number;
  slug: string;
  title: string;
  price: number | null;
  quantity: number;
  line_total: number;
  image?: string;
}
