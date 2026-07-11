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
  | 'spacer'
  | 'announcement_bar'
  | 'story_bar'
  | 'countdown'
  | 'coupon'
  | 'product_carousel'
  | 'banner_grid'
  | 'video'
  | 'testimonials'
  | 'trust_badges'
  | 'faq'
  | 'info'
  | 'bundle'
  | 'rich_text';

export interface BlockTarget {
  kind: 'category' | 'item' | 'tag' | 'url' | 'home' | 'flash_sale';
  value: string;
}

export interface StorySlide {
  image?: string;
  text?: string;
  duration?: number;
  target?: BlockTarget;
}

export interface StoryItem {
  title?: string;
  image?: string;
  target?: BlockTarget;
  slides?: StorySlide[];
}

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

export interface AnnouncementBarBlock extends HomeBlockBase {
  type: 'announcement_bar';
  text?: string;
  link?: string;
  bg?: string;
  color?: string;
  dismissible?: boolean;
}

export interface StoryBarBlock extends HomeBlockBase {
  type: 'story_bar';
  items?: StoryItem[];
}

export interface CountdownBlock extends HomeBlockBase {
  type: 'countdown';
  title?: string;
  ends_at?: string;
  cta_label?: string;
  cta_target?: BlockTarget;
  accent?: string;
}

export interface CouponBlock extends HomeBlockBase {
  type: 'coupon';
  title?: string;
  code?: string;
  subtitle?: string;
  copy_label?: string;
}

export interface ProductCarouselBlock extends HomeBlockBase {
  type: 'product_carousel';
  title?: string;
  source?: 'featured' | 'newest' | 'bestselling' | 'discounted' | 'flash_sale' | 'category' | 'tag';
  category?: string;
  tag?: string;
  limit?: number;
}

export interface BannerGridBlock extends HomeBlockBase {
  type: 'banner_grid';
  columns?: number;
  items?: { image?: string; target?: BlockTarget }[];
}

export interface VideoBlock extends HomeBlockBase {
  type: 'video';
  title?: string;
  source?: string;
  url?: string;
  poster?: string;
}

export interface TestimonialsBlock extends HomeBlockBase {
  type: 'testimonials';
  title?: string;
  items?: { name?: string; text?: string; rating?: number; image?: string }[];
}

export interface TrustBadgesBlock extends HomeBlockBase {
  type: 'trust_badges';
  items?: { icon?: string; label?: string }[];
}

export interface FaqBlock extends HomeBlockBase {
  type: 'faq';
  title?: string;
  items?: { q?: string; a?: string }[];
}

export interface InfoBlock extends HomeBlockBase {
  type: 'info';
  about?: string;
  phones?: string[];
  address?: string;
  hours?: string;
  location?: { lat: number; lng: number };
  socials?: { instagram?: string; eitaa?: string; telegram?: string; website?: string };
}

export interface BundleBlock extends HomeBlockBase {
  type: 'bundle';
  title?: string;
  item_slugs?: string[];
  bundle_price?: number;
  badge?: string;
}

export interface RichTextBlock extends HomeBlockBase {
  type: 'rich_text';
  title?: string;
  html?: string;
  align?: 'right' | 'center' | 'left';
}

export type HomeBlock =
  | HeroHomeBlock
  | SearchHomeBlock
  | SliderHomeBlock
  | CategoriesHomeBlock
  | FeaturedHomeBlock
  | ProductsHomeBlock
  | SpacerHomeBlock
  | AnnouncementBarBlock
  | StoryBarBlock
  | CountdownBlock
  | CouponBlock
  | ProductCarouselBlock
  | BannerGridBlock
  | VideoBlock
  | TestimonialsBlock
  | TrustBadgesBlock
  | FaqBlock
  | InfoBlock
  | BundleBlock
  | RichTextBlock;

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
  embed_url?: string;
  external_url?: string;
  title: string;
  locked?: boolean;
}

export interface GroupMember {
  id: number;
  slug: string;
  title: string;
  short_description: string;
  item_type: string;
  price: number | null;
  is_buyable: boolean;
  is_downloadable?: boolean;
  is_preview: boolean;
  has_access: boolean;
  locked: boolean;
  image?: string;
  download_url?: string;
  media?: ItemMedia[];
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
  compare_at_price?: number | null;
  sales_count?: number;
  sale_mode: string;
  is_buyable: boolean;
  is_requestable: boolean;
  is_downloadable: boolean;
  is_featured: boolean;
  is_flash_sale?: boolean;
  is_flash_sale_active?: boolean;
  flash_sale_ends_at?: string | null;
  metadata: Record<string, unknown>;
  media: ItemMedia[];
  images: string[];
  cover_url: string;
  download_url: string;
  category_id: number | null;
  category_slug: string | null;
  has_access?: boolean;
  requires_access?: boolean;
  is_group_parent?: boolean;
  group_members?: GroupMember[];
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
