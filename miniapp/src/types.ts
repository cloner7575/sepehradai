export interface PaymentMethodOption {
  id: string;
  label: string;
}

export interface CheckoutFormField {
  key: string;
  label: string;
  type: 'text' | 'tel' | 'email' | 'textarea';
  required: boolean;
}

export interface CheckoutFormConfig {
  enabled: boolean;
  title: string;
  fields: CheckoutFormField[];
}

export type HomeBlockType =
  | 'hero'
  | 'search'
  | 'slider'
  | 'categories'
  | 'featured'
  | 'products'
  | 'spacer';

export interface HomeBlockBase {
  id: string;
  type: HomeBlockType;
}

export interface HeroHomeBlock extends HomeBlockBase {
  type: 'hero';
  variant?: 'banner' | 'compact';
}

export interface SearchHomeBlock extends HomeBlockBase {
  type: 'search';
  placeholder?: string;
}

export interface SliderSlide {
  title?: string;
  subtitle?: string;
  image_url?: string;
  link_url?: string;
}

export interface SliderHomeBlock extends HomeBlockBase {
  type: 'slider';
  autoplay?: boolean;
  slides?: SliderSlide[];
}

export interface CategoriesHomeBlock extends HomeBlockBase {
  type: 'categories';
  title?: string;
  columns?: number;
  limit?: number;
}

export interface FeaturedHomeBlock extends HomeBlockBase {
  type: 'featured';
  title?: string;
  limit?: number;
  layout?: 'scroll' | 'grid';
}

export interface ProductsHomeBlock extends HomeBlockBase {
  type: 'products';
  title?: string;
  layout?: 'grid' | 'list';
  limit?: number;
}

export interface SpacerHomeBlock extends HomeBlockBase {
  type: 'spacer';
  size?: 'sm' | 'md' | 'lg';
}

export type HomeBlock =
  | HeroHomeBlock
  | SearchHomeBlock
  | SliderHomeBlock
  | CategoriesHomeBlock
  | FeaturedHomeBlock
  | ProductsHomeBlock
  | SpacerHomeBlock;

export interface CatalogConfig {
  is_enabled?: boolean;
  can_purchase?: boolean;
  platform: string;
  hero_title: string;
  hero_subtitle: string;
  theme: Record<string, string>;
  home_blocks?: HomeBlock[];
  labels: Record<string, string>;
  logo_url: string;
  hero_background_url: string;
  public_base_url: string;
  payment_methods?: PaymentMethodOption[];
  payment_default?: string;
  checkout_form?: CheckoutFormConfig;
  shipping?: {
    mode: string;
    flat_cost: number;
    free_threshold: number | null;
    provinces: string[];
  };
}

export interface CartSummary {
  items: CartLine[];
  subtotal: number;
  shipping_cost: number;
  discount_amount: number;
  total: number;
  free_shipping: boolean;
}

export interface AuthValidateResult {
  subscriber_id: number;
  user: {
    id: number;
    first_name: string;
    username: string;
  };
  channel_required: boolean;
  is_channel_member: boolean;
  channel_message: string;
  channel_invite_link: string;
}

export interface CheckoutResult {
  order_id: number;
  payment_method: string;
  status?: string;
  message?: string;
  method?: string;
  amount?: number;
  card?: CardToCardDetails;
}

export interface CardToCardDetails {
  number: string;
  number_display: string;
  sheba: string;
  sheba_display: string;
  holder: string;
}

export interface OrderPaymentInfo {
  order_id: number;
  amount: number;
  status: string;
  receipt_uploaded: boolean;
  receipt_url: string;
  card: CardToCardDetails;
}

export type MediaType = 'image' | 'video' | 'file';

export interface ItemMedia {
  id: number;
  type: MediaType;
  url: string;
  title: string;
}

export interface Category {
  id: number;
  slug: string;
  name: string;
  icon: string;
  image_url: string;
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
  is_downloadable: boolean;
  is_featured: boolean;
  metadata: Record<string, unknown>;
  media: ItemMedia[];
  images: string[];
  cover_url: string;
  download_url: string;
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
