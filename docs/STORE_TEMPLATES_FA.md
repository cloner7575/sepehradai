# راهنمای کامل قالب‌های فروشگاه (Store Template)

این سند ساختار **الگوهای آماده فروشگاه** را توضیح می‌دهد تا بتوانید قالب جدید برای **ربات** و **مینی‌اپ** بسازید، وارد سیستم کنید و اعمال کنید.

---

## فهرست

1. [مفاهیم پایه](#مفاهیم-پایه)
2. [ساختار کلی JSON](#ساختار-کلی-json)
3. [بخش مینی‌اپ (`scope=miniapp`)](#بخش-مینی‌اپ-scopeminiapp)
4. [بخش ربات (`scope=bot`)](#بخش-ربات-scopebot)
5. [بلوک‌های صفحهٔ اصلی مینی‌اپ (`home_blocks`)](#بلوک‌های-صفحهٔ-اصلی-مینی‌اپ-home_blocks)
6. [فلوی ربات (`start_flow`)](#فلوی-ربات-start_flow)
7. [اعمال قالب](#اعمال-قالب)
8. [ایمپورت و اکسپورت](#ایمپورت-و-اکسپورت)
9. [نمونهٔ کامل — فروشگاه فیزیکی](#نمونهٔ-کامل--فروشگاه-فیزیکی)
10. [نمونهٔ کامل — کسب‌وکار خدماتی](#نمونهٔ-کامل--کسب‌وکار-خدماتی)
11. [نمونهٔ کامل — محصولات دیجیتال](#نمونهٔ-کامل--محصولات-دیجیتال)
12. [قالب حداقلی (اسکلت خالی)](#قالب-حداقلی-اسکلت-خالی)
13. [چک‌لیست ساخت قالب جدید](#چک‌لیست-ساخت-قالب-جدید)
14. [نکات مهم و محدودیت‌ها](#نکات-مهم-و-محدودیت‌ها)

---

## مفاهیم پایه

### یک قالب، دو حوزهٔ اعمال

هر قالب در دیتابیس با مدل `StoreTemplate` ذخیره می‌شود. **یک فایل JSON** شامل همهٔ داده‌هاست، اما هنگام اعمال، کاربر یکی از دو حوزه را انتخاب می‌کند:

| حوزه | آدرس پنل | چه چیزی اعمال می‌شود |
|------|----------|----------------------|
| **مینی‌اپ** | `/catalog/templates/` | تنظیمات ویترین، دسته‌ها، محصولات، بلوک‌های صفحهٔ اصلی |
| **ربات** | `/bot/templates/` | فلوی `/start`، تنظیمات ربات، کد تخفیف خوش‌آمد، کمپین‌های نمونه |

**مهم:** اعمال قالب ربات، ویترین را دست نمی‌زند و بالعکس.

### فایل‌های مرجع در پروژه

| فایل | نقش |
|------|-----|
| `balebot/data/store_templates.json` | منبع اصلی ۲۴ قالب آماده |
| `balebot/services/store_template.py` | منطق اعمال قالب |
| `balebot/services/catalog_page_layout.py` | اعتبارسنجی `home_blocks` |
| `balebot/services/flow_sanitize.py` | اعتبارسنجی `start_flow` |
| `balebot/services/store_template_io.py` | ایمپورت/اکسپورت JSON |
| `balebot/data/home_blocks_presets.py` | تولید خودکار `home_blocks` اگر در قالب نباشد |
| `miniapp/src/types.ts` | تایپ‌های TypeScript بلوک‌ها |

### جریان کلی

```
store_templates.json
       ↓
  migration / import
       ↓
  StoreTemplate (دیتابیس)
       ↓
  پنل: انتخاب قالب + append/replace
       ↓
  ┌─────────────────┬──────────────────┐
  │ scope=miniapp   │ scope=bot        │
  │ CatalogSettings │ BotSettings      │
  │ Categories      │ DiscountCode     │
  │ Items           │ Campaign (draft) │
  └─────────────────┴──────────────────┘
       ↓                    ↓
  React مینی‌اپ        webhook /start
```

---

## ساختار کلی JSON

### متادیتای قالب (سطح بالا)

```json
{
  "slug": "my-shop",
  "name": "نام نمایشی در پنل",
  "industry": "clothing",
  "description": "توضیح کوتاه برای لیست قالب‌ها",
  "preview_image": "",
  "sort_order": 0,
  "is_active": true,
  "data": { }
}
```

| فیلد | نوع | الزامی | محدودیت |
|------|-----|--------|---------|
| `slug` | string | بله | یکتا، `[-a-z0-9]+`، حداکثر ۸۰ کاراکتر |
| `name` | string | بله | حداکثر ۱۲۰ کاراکتر |
| `industry` | string | خیر | حداکثر ۶۰ کاراکتر، پیش‌فرض `general` |
| `description` | string | خیر | حداکثر ۲۵۵ کاراکتر |
| `sort_order` | number | خیر | ترتیب نمایش در لیست |
| `is_active` | boolean | خیر | پیش‌فرض `true` |
| `data` | object | بله | محتوای اصلی قالب |

### فیلدهای داخل `data`

| فیلد | حوزه | توضیح |
|------|------|-------|
| `settings` | مینی‌اپ | عنوان، تم، برچسب‌ها، `home_blocks` |
| `categories` | مینی‌اپ | دسته‌بندی‌های نمونه |
| `items` | مینی‌اپ | محصولات/خدمات نمونه |
| `start_flow` | ربات | منوی `/start` نسخه ۲ |
| `bot_settings` | ربات | جمع‌آوری شماره تماس |
| `marketing` | ربات | تخفیف، کمپین‌ها، نکات (بخشی فقط مستندات) |
| `sample_campaign` | ربات | کمپین تکی (جایگزین قدیمی `marketing.campaigns`) |

---

## بخش مینی‌اپ (`scope=miniapp`)

### `settings` — تنظیمات ویترین

```json
{
  "settings": {
    "hero_title": "عنوان اصلی صفحهٔ خانه",
    "hero_subtitle": "زیرعنوان کوتاه",
    "theme": {
      "primary": "#b3456b",
      "accent": "#7c3aed",
      "background": "#fdf6f8",
      "font": "Vazirmatn",
      "layout": "grid"
    },
    "labels": {
      "buy": "افزودن به سبد",
      "cart": "سبد خرید",
      "checkout": "تسویه حساب",
      "categories": "دسته‌بندی‌ها"
    },
    "home_blocks": []
  }
}
```

**نگاشت هنگام اعمال:**

| در قالب | در دیتابیس (`CatalogSettings`) |
|---------|--------------------------------|
| `hero_title` | `hero_title` (حداکثر ۲۰۰ کاراکتر) |
| `hero_subtitle` | `hero_subtitle` (حداکثر ۳۰۰ کاراکتر) |
| `theme.primary` | `theme_config.primary_color` |
| `theme.accent` | `theme_config.accent_color` |
| `theme.layout` | `theme_config.layout` → `grid` یا `list` |
| `theme.font` | `theme_config.font_family` |
| `home_blocks` | `theme_config.home_blocks` |
| `labels.buy` | `labels.buy_now` و `labels.add_to_cart` |

اگر `home_blocks` خالی باشد یا نباشد، سیستم از `home_blocks_presets.py` بر اساس `industry` چیدمان پیش‌فرض می‌سازد.

### `categories` — دسته‌بندی‌ها

```json
{
  "slug": "manto",
  "name": "مانتو و پالتو",
  "icon": "🧥",
  "sort_order": 1,
  "parent": null
}
```

| فیلد | توضیح |
|------|-------|
| `slug` | شناسه یکتا؛ اگر نباشد از `name` ساخته می‌شود |
| `name` | نام نمایشی |
| `icon` | ایموجی یا متن کوتاه (حداکثر ۶۴ کاراکتر) |
| `sort_order` | ترتیب نمایش |
| `parent` | `slug` دستهٔ والد برای زیردسته (یا `null`) |

**نکته:** دسته‌های والد باید **قبل از** زیردسته‌ها در آرایه بیایند.

### `items` — محصولات و خدمات

```json
{
  "slug": "manto-krep",
  "name": "مانتو جلوباز کرپ",
  "category": "manto",
  "item_type": "product",
  "sale_mode": "buy",
  "price": 3850000,
  "compare_at_price": 4312000,
  "sales_count": 24,
  "stock": 12,
  "is_featured": true,
  "description": "توضیحات محصول",
  "image_url": ""
}
```

#### `item_type` — نوع آیتم

| مقدار در قالب | نوع در سیستم | کاربرد |
|---------------|--------------|--------|
| `product` | PRODUCT | کالای فیزیکی |
| `download` | DOWNLOAD | فایل دیجیتال |
| `showcase` | SHOWCASE | ویترین / نمایشی |
| `service` | SHOWCASE | خدمات (مثل سالن زیبایی) |
| `portfolio` | SHOWCASE | نمونه‌کار |

#### `sale_mode` — حالت فروش

| مقدار در قالب | حالت در سیستم | معنی |
|---------------|---------------|------|
| `buy`, `buyable` | BUYABLE | خرید مستقیم |
| `quote`, `request`, `request_only` | REQUEST_ONLY | استعلام / تماس |
| `download` | DOWNLOAD | دانلود پس از پرداخت |
| `both` | BOTH | خرید یا استعلام |

#### قیمت و موجودی

- **قیمت** به **ریال** است.
- `price: 0` یا نبودن قیمت برای خدمات استعلامی → قیمت `null` ذخیره می‌شود.
- `stock: null` → موجودی نامحدود.
- `compare_at_price` → قیمت قبل از تخفیف (اختیاری).
- `sales_count` → تعداد فروش نمایشی (اختیاری).
- **`image_url` هنگام اعمال کپی نمی‌شود** — تصویر را بعداً در پنل اضافه کنید.

---

## بخش ربات (`scope=bot`)

### `bot_settings`

```json
{
  "bot_settings": {
    "collect_contact_on_start": false,
    "start_message_contact": "برای اطلاع از تخفیف‌ها، شماره‌ت رو به اشتراک بذار 🌸"
  }
}
```

| فیلد | توضیح |
|------|-------|
| `collect_contact_on_start` | آیا بلافاصله پس از `/start` شماره بخواهد |
| `start_message_contact` | متن همراه دکمهٔ اشتراک شماره (حداکثر ۴۰۹۶ کاراکتر) |

### `marketing`

```json
{
  "marketing": {
    "target": "مخاطب هدف — فقط مستندات",
    "strategy": "استراتژی — فقط مستندات",
    "welcome_discount": {
      "code": "WELCOME15",
      "kind": "percent",
      "value": 15,
      "max_uses": null,
      "min_order_amount": null,
      "max_discount_amount": null,
      "first_purchase_only": false
    },
    "tips": ["نکته ۱", "نکته ۲"],
    "campaigns": [
      {
        "title": "تخفیف اولین خرید",
        "trigger": "welcome",
        "content_type": "text",
        "body": "متن کمپین..."
      }
    ]
  }
}
```

| فیلد | اعمال در DB |
|------|-------------|
| `welcome_discount` | ایجاد/به‌روزرسانی `DiscountCode` |
| `campaigns` | ایجاد `Campaign` با وضعیت **DRAFT** |
| `target`, `strategy`, `tips` | **اعمال نمی‌شوند** — فقط راهنما برای نویسندهٔ قالب |

#### `welcome_discount.kind`

- `percent` → درصد تخفیف
- `amount` → مبلغ ثابت (ریال)

#### `campaigns[].trigger` (متادیتا)

مقادیر رایج: `welcome`, `abandoned_cart`, `restock`, `seasonal`, `loyalty`

این مقدار فقط برای مستندسازی است؛ اتوماسیون تریگر هنگام اعمال وصل نمی‌شود.

---

## بلوک‌های صفحهٔ اصلی مینی‌اپ (`home_blocks`)

آرایه‌ای از بلوک‌ها که ترتیب نمایش در صفحهٔ اصلی مینی‌اپ را تعیین می‌کند.

### قوانین عمومی

- هر بلوک باید `id` و `type` داشته باشد.
- `id` باید با الگوی `b_` + ۸ کاراکتر hex باشد: `b_a1b2c3d4`
- رنگ‌ها باید hex باشند: `#2563eb`
- `visible: false` → بلوک حذف می‌شود

### انواع بلوک (۲۱ نوع)

| type | کاربرد | فیلدهای مهم |
|------|--------|-------------|
| `hero` | بنر اصلی | `variant`: `banner` \| `compact` |
| `search` | جستجو | `placeholder` |
| `slider` | اسلایدر تصویر | `slides[]`, `autoplay` |
| `categories` | شبکهٔ دسته‌ها | `title`, `columns`, `limit` |
| `featured` | محصولات ویژه | `title`, `limit`, `layout` |
| `products` | لیست محصولات | `title`, `layout`, `limit` |
| `spacer` | فاصله | `size`: `sm` \| `md` \| `lg` |
| `announcement_bar` | نوار اعلان | `text`, `bg`, `color`, `dismissible` |
| `story_bar` | استوری | `items[]` با `slides` |
| `countdown` | شمارش معکوس | `ends_at`, `cta_label`, `cta_target` |
| `coupon` | نمایش کد تخفیف | `code` یا `discount_id` |
| `product_carousel` | کاروسل محصول | `source`, `category`, `limit` |
| `banner_grid` | گرید بنر | `columns`, `items[]` |
| `video` | ویدیو | `url`, `poster`, `title` |
| `testimonials` | نظرات | `items[]` با `name`, `text`, `rating` |
| `trust_badges` | نشان‌های اعتماد | `items[]` با `icon`, `label` |
| `faq` | سوالات متداول | `items[]` با `q`, `a` |
| `info` | درباره ما | `about`, `phones`, `address`, `hours`, `socials` |
| `bundle` | بسته محصول | `item_slugs[]`, `bundle_price` |
| `rich_text` | متن HTML | `html`, `align` |

### `target` — مقصد کلیک

```json
{
  "kind": "category",
  "value": "manto"
}
```

| kind | value |
|------|-------|
| `category` | slug دسته |
| `item` | slug محصول |
| `tag` | برچسب |
| `url` | آدرس خارجی |
| `home` | صفحهٔ اصلی (value خالی) |
| `flash_sale` | حراج (value خالی) |

### `product_carousel.source`

`featured`, `newest`, `bestselling`, `discounted`, `flash_sale`, `category`, `tag`

### نمونهٔ چیدمان صفحهٔ اصلی

```json
"home_blocks": [
  {
    "id": "b_announce1",
    "type": "announcement_bar",
    "text": "🚚 ارسال رایگان برای سفارش‌های بالای ۵ میلیون تومان",
    "bg": "#111111",
    "color": "#ffffff",
    "dismissible": true
  },
  {
    "id": "b_hero0001",
    "type": "hero",
    "variant": "banner"
  },
  {
    "id": "b_search01",
    "type": "search",
    "placeholder": "جستجوی محصول…"
  },
  {
    "id": "b_categ001",
    "type": "categories",
    "title": "دسته‌بندی‌ها",
    "columns": 2,
    "limit": 8
  },
  {
    "id": "b_carous01",
    "type": "product_carousel",
    "title": "پرفروش‌ترین‌ها",
    "source": "bestselling",
    "limit": 10
  },
  {
    "id": "b_coupon01",
    "type": "coupon",
    "title": "تخفیف اولین خرید",
    "code": "WELCOME15",
    "subtitle": "۱۵٪ تخفیف",
    "copy_label": "کپی کد"
  },
  {
    "id": "b_trust001",
    "type": "trust_badges",
    "items": [
      { "icon": "✅", "label": "اصالت کالا" },
      { "icon": "🚚", "label": "ارسال سریع" }
    ]
  },
  {
    "id": "b_faq0001",
    "type": "faq",
    "title": "سوالات متداول",
    "items": [
      { "q": "هزینه ارسال چقدره؟", "a": "برای سفارش‌های بالای ۵ میلیون رایگان است." }
    ]
  }
]
```

---

## فلوی ربات (`start_flow`)

فلوی `/start` نسخه ۲. ریشه همیشه یک `sequence` است.

### ساختار پایه

```json
{
  "start_flow": {
    "version": 2,
    "root": {
      "type": "sequence",
      "items": [
        {
          "type": "text",
          "text": "سلام! به فروشگاه ما خوش اومدی."
        },
        {
          "type": "buttons",
          "rows": [
            [
              {
                "id": "n_shop",
                "label": "🛍 ورود به فروشگاه",
                "action": { "type": "url", "url": "{shop_url}" }
              }
            ]
          ]
        }
      ]
    }
  }
}
```

### نکات نوشتن فلو در قالب

| نکته | توضیح |
|------|-------|
| `{shop_url}` | هنگام اعمال با لینک واقعی مینی‌اپ جایگزین می‌شود |
| `text` یا `body` | هر دو قابل قبول‌اند؛ سیستم به `body` نرمال می‌کند |
| `label` یا `text` در دکمه | هر دو قابل قبول‌اند |
| `label_slug` | فقط برای پردازش الگو — ذخیره نمی‌شود |
| `id` دکمه | الگو: `n_` + حروف/عدد، مثل `n_shop` |

### انواع `action` در دکمه‌ها

| type | کاربرد | فیلدهای کلیدی |
|------|--------|---------------|
| `text` | نمایش پیام | `text` یا `body` |
| `url` | باز کردن لینک | `url` |
| `webapp` | باز کردن مینی‌اپ | `label`, `target` |
| `coupon` | نمایش کد تخفیف | `code` یا `discount_id` |
| `handoff` | انتقال به پشتیبانی | `message` |
| `faq` | سوالات متداول | `title`, `items[]` |
| `order_status` | پیگیری سفارش | `prompt` |
| `my_orders` | لیست سفارش‌ها | `limit` |
| `input` | دریافت ورودی | `prompt`, `save_key`, `validate` |
| `form` | فرم چندمرحله‌ای | `steps[]`, `on_complete` |
| `request_contact` | درخواست شماره | `prompt`, `assign_tag` |
| `condition` | شرط | `if`, `then`, `else` |
| `tag` | افزودن/حذف برچسب | `add[]`, `remove[]` |

### نمونهٔ دکمه‌های پیشرفته

```json
{
  "type": "buttons",
  "rows": [
    [
      {
        "id": "n_webapp",
        "label": "🛍 فروشگاه",
        "action": {
          "type": "webapp",
          "label": "ورود به فروشگاه",
          "target": { "kind": "home", "value": "" }
        }
      }
    ],
    [
      {
        "id": "n_coupon",
        "label": "🎁 کد تخفیف",
        "action": {
          "type": "coupon",
          "code": "WELCOME15",
          "message": "کد تخفیف اولین خریدت:"
        }
      },
      {
        "id": "n_support",
        "label": "💬 پشتیبانی",
        "action": {
          "type": "handoff",
          "message": "پیامت رو بفرست، همکاران پاسخ می‌دن."
        }
      }
    ],
    [
      {
        "id": "n_faq",
        "label": "❓ سوالات متداول",
        "action": {
          "type": "faq",
          "title": "سوالات پرتکرار",
          "items": [
            { "q": "زمان ارسال؟", "a": "۲ تا ۵ روز کاری." }
          ]
        }
      }
    ]
  ]
}
```

---

## اعمال قالب

### از پنل

1. **مینی‌اپ:** کاتالوگ → قالب‌ها → `/catalog/templates/`
2. **ربات:** ربات → قالب‌ها → `/bot/templates/`
3. روی «استفاده از قالب» کلیک کنید.
4. حالت را انتخاب کنید:

| mode | رفتار |
|------|-------|
| `append` (پیش‌فرض) | فقط موارد جدید اضافه می‌شود؛ موارد موجود با همان slug رد می‌شوند |
| `replace` | مینی‌اپ: همهٔ دسته‌ها و محصولات پاک و از نو ساخته می‌شوند. ربات: کمپین‌های draft با همان عنوان جایگزین می‌شوند |

### برنامه‌نویسی

```python
from balebot.services.store_template import apply_template

stats = apply_template(
    template,
    workspace,
    platform,
    mode='append',      # یا 'replace'
    scope='miniapp',    # یا 'bot'
)
```

---

## ایمپورت و اکسپورت

فقط **سوپرادمین** می‌تواند قالب‌ها را ایمپورت/اکسپورت کند.

### فرمت تک‌قالب

```json
{
  "version": 1,
  "kind": "store_template",
  "template": {
    "slug": "my-shop",
    "name": "فروشگاه من",
    "industry": "general",
    "description": "",
    "sort_order": 0,
    "is_active": true,
    "data": { }
  }
}
```

### فرمت چندقالبی (bundle)

```json
{
  "version": 1,
  "kind": "store_templates",
  "templates": [
    { "slug": "shop-a", "name": "...", "data": {} },
    { "slug": "shop-b", "name": "...", "data": {} }
  ]
}
```

### روش‌های جایگزین قابل قبول

- آرایهٔ مستقیم از قالب‌ها: `[{ "slug": "...", ... }]`
- یک شیء تکی با فیلد `slug` در ریشه

---

## نمونهٔ کامل — فروشگاه فیزیکی

قالب `women-clothing` — پوشاک با خرید مستقیم.

```json
{
  "slug": "women-clothing",
  "name": "بوتیک پوشاک زنانه",
  "industry": "clothing",
  "description": "فروشگاه لباس زنانه با تمرکز بر کالکشن فصلی",
  "data": {
    "settings": {
      "hero_title": "بوتیک [نام شما]",
      "hero_subtitle": "جدیدترین کالکشن • ارسال به سراسر کشور",
      "theme": {
        "primary": "#b3456b",
        "background": "#fdf6f8",
        "font": "Vazirmatn",
        "layout": "grid"
      },
      "labels": {
        "buy": "افزودن به سبد",
        "cart": "سبد خرید",
        "categories": "دسته‌بندی‌ها"
      }
    },
    "bot_settings": {
      "collect_contact_on_start": false,
      "start_message_contact": "برای اطلاع از تخفیف‌ها شماره‌ت رو به اشتراک بذار 🌸"
    },
    "categories": [
      { "slug": "manto", "name": "مانتو و پالتو", "icon": "🧥", "sort_order": 1, "parent": null },
      { "slug": "shomiz", "name": "شومیز و بلوز", "icon": "👚", "sort_order": 2, "parent": null }
    ],
    "items": [
      {
        "slug": "manto-krep",
        "name": "مانتو جلوباز کرپ",
        "category": "manto",
        "item_type": "product",
        "sale_mode": "buy",
        "price": 3850000,
        "stock": 12,
        "is_featured": true,
        "description": "کرپ مازراتی، سایز ۳۶ تا ۴۸",
        "image_url": ""
      }
    ],
    "start_flow": {
      "version": 2,
      "root": {
        "type": "sequence",
        "items": [
          {
            "type": "text",
            "text": "سلام 🌸 به بوتیک ما خوش اومدی!"
          },
          {
            "type": "buttons",
            "rows": [
              [
                {
                  "id": "n_shop",
                  "label": "🛍 ورود به فروشگاه",
                  "action": { "type": "url", "url": "{shop_url}" }
                }
              ],
              [
                {
                  "id": "n_offer",
                  "label": "🎁 تخفیف اولین خرید",
                  "action": {
                    "type": "text",
                    "text": "کد WELCOME15 رو موقع پرداخت بزن."
                  }
                }
              ]
            ]
          }
        ]
      }
    },
    "marketing": {
      "welcome_discount": {
        "code": "WELCOME15",
        "kind": "percent",
        "value": 15
      },
      "campaigns": [
        {
          "title": "تخفیف اولین خرید",
          "trigger": "welcome",
          "content_type": "text",
          "body": "🎀 با کد WELCOME15، ۱۵٪ تخفیف اولین خرید."
        },
        {
          "title": "یادآوری سبد",
          "trigger": "abandoned_cart",
          "content_type": "text",
          "body": "🛍 سبدت هنوز منتظرته!"
        }
      ]
    }
  }
}
```

---

## نمونهٔ کامل — کسب‌وکار خدماتی

قالب `salon` — خدمات با قیمت استعلامی.

```json
{
  "slug": "salon",
  "name": "سالن زیبایی",
  "industry": "service",
  "description": "رزرو نوبت سالن زیبایی",
  "data": {
    "settings": {
      "hero_title": "سالن [نام شما]",
      "hero_subtitle": "زیبایی، با یه نوبت ساده ✨",
      "theme": {
        "primary": "#b04f7a",
        "background": "#fbf3f7",
        "layout": "list"
      },
      "labels": {
        "buy": "رزرو نوبت",
        "cart": "نوبت‌های من",
        "categories": "خدمات"
      }
    },
    "categories": [
      { "slug": "hair", "name": "مو", "icon": "💇", "sort_order": 1, "parent": null },
      { "slug": "nail", "name": "ناخن", "icon": "💅", "sort_order": 2, "parent": null }
    ],
    "items": [
      {
        "slug": "haircut",
        "name": "کوتاهی و براشینگ",
        "category": "hair",
        "item_type": "service",
        "sale_mode": "quote",
        "price": 0,
        "stock": null,
        "is_featured": true,
        "description": "برای رزرو نوبت پیام بده"
      }
    ],
    "start_flow": {
      "version": 2,
      "root": {
        "type": "sequence",
        "items": [
          {
            "type": "text",
            "text": "سلام ✨ برای کدوم خدمت نوبت می‌خوای؟"
          },
          {
            "type": "buttons",
            "rows": [
              [
                {
                  "id": "n_book",
                  "label": "📅 رزرو نوبت",
                  "action": {
                    "type": "text",
                    "text": "خدمت و روز دلخواهت رو بفرست."
                  }
                }
              ],
              [
                {
                  "id": "n_gallery",
                  "label": "📸 نمونه‌کارها",
                  "action": { "type": "url", "url": "{shop_url}" }
                }
              ]
            ]
          }
        ]
      }
    },
    "marketing": {
      "campaigns": [
        {
          "title": "یادآوری نوبت",
          "trigger": "loyalty",
          "content_type": "text",
          "body": "یادآوری: نوبت شما فردا ساعت ..."
        }
      ]
    }
  }
}
```

**تفاوت کلیدی با فروشگاه فیزیکی:**
- `item_type: "service"` → ویترین + فقط درخواست/تماس
- `sale_mode: "quote"` و `price: 0`
- برچسب‌ها: «رزرو نوبت» به‌جای «افزودن به سبد»

---

## نمونهٔ کامل — محصولات دیجیتال

قالب `digital-products` — فایل قابل دانلود.

```json
{
  "slug": "digital-products",
  "name": "فروشگاه دیجیتال",
  "industry": "digital",
  "description": "فروش فایل و محصول دانلودی",
  "data": {
    "settings": {
      "hero_title": "فروشگاه دیجیتال [نام شما]",
      "hero_subtitle": "تحویل آنی، بدون معطلی ⚡",
      "theme": {
        "primary": "#5b4b8a",
        "background": "#f5f3fb",
        "layout": "list"
      },
      "labels": {
        "buy": "خرید و دانلود",
        "cart": "خریدهای من",
        "categories": "دسته‌ها"
      }
    },
    "categories": [
      { "slug": "template", "name": "قالب و فایل آماده", "icon": "🗂️", "sort_order": 1, "parent": null },
      { "slug": "ebook", "name": "کتاب الکترونیک", "icon": "📘", "sort_order": 2, "parent": null }
    ],
    "items": [
      {
        "slug": "notion-template",
        "name": "قالب نوشن مدیریت کار",
        "category": "template",
        "item_type": "download",
        "sale_mode": "download",
        "price": 350000,
        "stock": null,
        "is_featured": true,
        "description": "تحویل آنی پس از پرداخت"
      }
    ],
    "start_flow": {
      "version": 2,
      "root": {
        "type": "sequence",
        "items": [
          {
            "type": "text",
            "text": "سلام ⚡ فایل‌ها بلافاصله بعد از پرداخت آمادهٔ دانلودن."
          },
          {
            "type": "buttons",
            "rows": [
              [
                {
                  "id": "n_shop",
                  "label": "📥 مشاهده محصولات",
                  "action": { "type": "url", "url": "{shop_url}" }
                }
              ]
            ]
          }
        ]
      }
    },
    "marketing": {
      "welcome_discount": {
        "code": "FIRST10",
        "kind": "percent",
        "value": 10
      }
    }
  }
}
```

**تفاوت کلیدی:**
- `item_type: "download"` + `sale_mode: "download"`
- `layout: "list"` مناسب‌تر برای فایل‌ها
- `stock: null` معمولاً برای دیجیتال

---

## قالب حداقلی (اسکلت خالی)

کوچک‌ترین قالبی که هر دو حوزه را پوشش می‌دهد:

```json
{
  "slug": "minimal-shop",
  "name": "فروشگاه حداقلی",
  "industry": "general",
  "description": "اسکلت پایه برای شروع سریع",
  "sort_order": 99,
  "is_active": true,
  "data": {
    "settings": {
      "hero_title": "فروشگاه [نام شما]",
      "hero_subtitle": "به فروشگاه ما خوش آمدید",
      "theme": {
        "primary": "#2563eb",
        "background": "#ffffff",
        "font": "Vazirmatn",
        "layout": "grid"
      },
      "labels": {
        "buy": "خرید",
        "cart": "سبد خرید"
      }
    },
    "categories": [
      {
        "slug": "main",
        "name": "محصولات",
        "icon": "📦",
        "sort_order": 1,
        "parent": null
      }
    ],
    "items": [
      {
        "slug": "sample-product",
        "name": "محصول نمونه",
        "category": "main",
        "item_type": "product",
        "sale_mode": "buy",
        "price": 1000000,
        "stock": 10,
        "is_featured": true,
        "description": "توضیح محصول نمونه"
      }
    ],
    "bot_settings": {
      "collect_contact_on_start": false
    },
    "start_flow": {
      "version": 2,
      "root": {
        "type": "sequence",
        "items": [
          { "type": "text", "text": "سلام! به فروشگاه ما خوش اومدی." },
          {
            "type": "buttons",
            "rows": [
              [
                {
                  "id": "n_shop",
                  "label": "🛍 فروشگاه",
                  "action": { "type": "url", "url": "{shop_url}" }
                }
              ]
            ]
          }
        ]
      }
    },
    "marketing": {
      "welcome_discount": {
        "code": "WELCOME10",
        "kind": "percent",
        "value": 10
      }
    }
  }
}
```

---

## چک‌لیست ساخت قالب جدید

### ۱. طراحی

- [ ] `slug` یکتا و انگلیسی (مثل `my-bakery`)
- [ ] `industry` مناسب انتخاب شده
- [ ] نوع کسب‌وکار مشخص: فیزیکی / خدماتی / دیجیتال

### ۲. بخش مینی‌اپ

- [ ] `hero_title` و `hero_subtitle` نوشته شده
- [ ] رنگ‌های `theme` با هویت برند هماهنگ است
- [ ] حداقل ۱ دسته و ۲–۵ آیتم نمونه
- [ ] `item_type` و `sale_mode` درست انتخاب شده
- [ ] قیمت‌ها به **ریال**
- [ ] (اختیاری) `home_blocks` سفارشی یا اتکا به preset خودکار

### ۳. بخش ربات

- [ ] `start_flow.version` برابر ۲
- [ ] پیام خوش‌آمد + حداقل ۱ دکمهٔ فروشگاه با `{shop_url}`
- [ ] `bot_settings` در صورت نیاز
- [ ] `welcome_discount` در صورت نیاز
- [ ] ۱–۳ `campaign` نمونه با `trigger` مناسب

### ۴. اعتبارسنجی

- [ ] JSON معتبر (با `jsonlint` یا IDE)
- [ ] `slug` دسته‌ها در `items[].category` موجود است
- [ ] `id` بلوک‌ها: `b_xxxxxxxx`
- [ ] `id` دکمه‌های فلو: `n_...`

### ۵. استقرار

- [ ] اضافه به `store_templates.json` **یا** ایمپورت از پنل سوپرادمین
- [ ] تست `append` روی workspace آزمایشی
- [ ] تست `replace` در صورت نیاز
- [ ] تصاویر محصولات را دستی در پنل اضافه کنید

---

## نکات مهم و محدودیت‌ها

| موضوع | توضیح |
|-------|-------|
| **تصاویر** | `image_url` در قالب اعمال نمی‌شود |
| **کمپین‌ها** | فقط به‌صورت پیش‌نویس (DRAFT) ساخته می‌شوند |
| **`marketing.tips`** | فقط راهنما — در DB ذخیره نمی‌شود |
| **`{shop_url}`** | فقط در `start_flow` جایگزین می‌شود |
| **قالب‌های HTML پنل** | `balebot/templates/*.html` ربطی به این سیستم ندارند |
| **ویرایشگر بصری** | بعد از اعمال، از `/bot/flow/` و `/catalog/flow/` قابل ویرایش است |
| **seed خودکار** | اگر `home_blocks` نباشد، بر اساس `industry` ساخته می‌شود |
| **عمق فلو** | حداکثر ۲۰ سطح تو در تو |
| **rich_text HTML** | فقط تگ‌های `p`, `b`, `i`, `ul`, `li`, `a`, `br`, `strong`, `em` |

### صنف‌های (`industry`) رایج

`clothing`, `cosmetics`, `food`, `bakery`, `coffee`, `digital`, `service`, `restaurant`, `education`, `petshop`, `home-decor`, `jewelry`, `books`, `sports`, `toys`, `handicraft`, `organic`, `general`

لیست کامل در `STORE_TEMPLATE_INDUSTRY_LABELS` داخل `balebot/views_panel_catalog.py`.

---

## خلاصهٔ تصمیم‌گیری سریع

```
چه نوع کسب‌وکاری دارید؟
│
├─ کالای فیزیکی
│   ├─ مینی‌اپ: item_type=product, sale_mode=buy
│   └─ ربات: دکمه فروشگاه + تخفیف خوش‌آمد + یادآوری سبد
│
├─ خدمات / رزرو
│   ├─ مینی‌اپ: item_type=service, sale_mode=quote, price=0
│   └─ ربات: دکمه رزرو + لیست قیمت + پشتیبانی
│
└─ فایل دیجیتال
    ├─ مینی‌اپ: item_type=download, sale_mode=download, layout=list
    └─ ربات: تأکید بر تحویل آنی + دکمه مشاهده محصولات
```

---

*آخرین به‌روزرسانی: بر اساس کد پروژه در `balebot/data/store_templates.json` و سرویس‌های `store_template.py`, `catalog_page_layout.py`, `flow_sanitize.py`.*
