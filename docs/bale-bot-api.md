# مستند مرجع API بازوی بله (Bale Bot API)

این فایل برای استفاده در توسعهٔ پروژه تهیه شده است. API بازوی بله بر پایهٔ API بات تلگرام است؛ کتابخانه‌های توسعهٔ بات تلگرام را می‌توان با آدرس پایهٔ متفاوت استفاده کرد.

---

## فهرست

1. [خلاصهٔ سریع](#خلاصهٔ-سریع)
2. [ایجاد بازو و توکن](#ایجاد-بازو-و-توکن)
3. [درخواست‌های HTTP](#درخواست‌های-http)
4. [قالب پاسخ JSON](#قالب-پاسخ-json)
5. [دریافت آپدیت‌ها](#دریافت-آپدیت‌ها)
6. [شیء Update](#شیء-update)
7. [انواع داده (Types)](#انواع-داده-types)
8. [ارسال فایل](#ارسال-فایل)
9. [متدهای API](#متدهای-api)
10. [پرداخت و کیف پول](#پرداخت-و-کیف-پول)
11. [استیکرها](#استیکرها)
12. [نکات پیاده‌سازی](#نکات-پیاده‌سازی)

---

## خلاصهٔ سریع

| مورد | مقدار |
|------|--------|
| پایهٔ API | `https://tapi.bale.ai/bot<token>/METHOD_NAME` |
| فایل (دانلود) | `https://tapi.bale.ai/file/bot<token>/<file_path>` |
| پروتکل | HTTPS |
| کدگذاری | UTF-8 |
| حساسیت حروف | ندارد (case-insensitive) |

**مثال:** `https://tapi.bale.ai/bot123456789:abcd.../getMe`

---

## ایجاد بازو و توکن

- با **@botfather** در بله گفتگو کنید و بازو بسازید.
- پس از ساخت، **توکن احراز هویت** منحصربه‌فرد دریافت می‌کنید.
- فرمت نمونهٔ توکن: `123456789:abcdIuZmK5qNEm2A1BhUaAg7MPJv1O9KCcBQB2ro`

---

## درخواست‌های HTTP

**متدها:** `GET` و `POST` (هر دو پشتیبانی می‌شوند).

**ارسال پارامتر (چهار روش):**

1. Query string در URL
2. `application/x-www-form-urlencoded`
3. `application/json` (برای آپلود فایل مناسب نیست)
4. `multipart/form-data` (برای آپلود فایل)

---

## قالب پاسخ JSON

همهٔ پاسخ‌ها شیء JSON با فیلد **`ok`** (boolean) هستند.

| وضعیت | فیلدها |
|--------|---------|
| موفق | `ok: true`، نتیجه معمولاً در **`result`** |
| ناموفق | `ok: false`، **`error_code`** (integer)، ممکن است **`description`** و **`parameters`** (`ResponseParameters`) |

---

## دریافت آپدیت‌ها

دو روش:

1. **`getUpdates`** — long polling  
2. **`setWebhook`** — ارسال آپدیت با HTTPS POST به URL شما

**نگهداری آپدیت:** تا وقتی بازو آن‌ها را با یکی از دو روش بالا مصرف نکند در سرور ذخیره می‌شوند؛ در حال حاضر **۲۰۰۰ آپدیت آخر تا ۲۴ ساعت**.

### getUpdates

آرایه‌ای از `Update` برمی‌گرداند.

| پارامتر | نوع | الزام | توضیح |
|---------|-----|--------|--------|
| offset | Integer | خیر | اولین `update_id` که باید برگردد؛ برای تأیید آپدیت‌های قبلی معمولاً `max(update_id)+1`. offset منفی برای گرفتن از انتهای صف؛ آپدیت‌های قبلی فراموش می‌شوند. |
| limit | Integer | خیر | ۱…۱۰۰، پیش‌فرض ۱۰۰ |
| timeout | Integer | خیر | ثانیهٔ انتظار long polling |

**نکته:** بعد از هر پاسخ، `offset` را به‌روز کنید تا آپدیت تکراری نگیرید.

### setWebhook

| پارامتر | نوع | الزام | توضیح |
|---------|-----|--------|--------|
| url | String | بله | URL کامل HTTPS؛ رشتهٔ خالی = حذف وب‌هوک |

**پورت‌های مجاز وب‌هوک:** `443`، `88`

### deleteWebhook

غیرفعال‌سازی وب‌هوک (مثلاً برای برگشت به `getUpdates`). خروجی موفق: `true`.

### getWebhookInfo

وضعیت وب‌هوک؛ اگر فقط `getUpdates` استفاده شود، `url` خالی است.

---

## شیء Update

برای هر رویداد (پیام، ویرایش، کلیک دکمه، …) یک آپدیت. **حداکثر یکی** از فیلدهای اختیاری زیر در هر آپدیت:

| فیلد | نوع | توضیح |
|------|-----|--------|
| update_id | Integer | شناسه یکتا و صعودی؛ مهم برای وب‌هوک و دئودیپلیکیت |
| message | Message | پیام جدید |
| edited_message | Message | نسخهٔ ویرایش‌شده پیام |
| callback_query | CallbackQuery | کلیک دکمهٔ inline |
| pre_checkout_query | PreCheckoutQuery | قبل از نهایی شدن پرداخت کیف‌پولی |

---

## انواع داده (Types)

### User

| فیلد | نوع | توضیح |
|------|-----|--------|
| id | Integer | ممکن است بزرگ‌تر از 2³¹ باشد → در صورت لزوم int64 / string |
| is_bot | Boolean | |
| first_name | String | |
| last_name | String | اختیاری |
| username | String | اختیاری |
| language_code | String | اختیاری |

### Chat

| فیلد | نوع | توضیح |
|------|-----|--------|
| id | Integer | مثل `user.id`، ممکن است بسیار بزرگ باشد |
| type | String | `private`، `group`، `channel` |
| title / username / first_name / last_name | | بسته به نوع گفتگو |

`ChatFullInfo` اطلاعات بیشتر (مثلاً `photo`، `bio`، `description`، `invite_link`، `linked_chat_id`).

### Message (خلاصه)

فیلدهای مهم: `message_id`، `from`، `date`، `chat`، `text`، `entities`، انواع رسانه (`photo`، `document`، `voice`، …)، `reply_to_message`، `caption`، `reply_markup`، `invoice`، `successful_payment`، `web_app_data`، …

**MessageEntity:** `type` (مثلاً `mention`، `bot_command`)، `offset` و `length` بر حسب **واحد UTF-16**.

### File

دریافت مسیر فایل با `getFile`، سپس:

`https://tapi.bale.ai/file/bot<token>/<file_path>`

لینک حدود **یک ساعت** معتبر است.

### سایر

`PhotoSize`، `Animation`، `Audio`، `Document`، `Video`، `Voice`، `Contact`، `Location`، `Invoice`، `ReplyKeyboardMarkup`، `InlineKeyboardMarkup`، `CallbackQuery`، `WebAppData`، `WebAppInfo`، `ChatMember*`، `InputMedia*`، `ResponseParameters` (`retry_after` برای rate limit)، … مطابق جداول رسمی بله.

---

## ارسال فایل

**سه روش:**

1. **`file_id`** — بدون آپلود مجدد؛ برای هر بازو جداگانه است و بین بازوها قابل انتقال نیست.
2. **HTTP URL** — بله دانلود می‌کند (محدودیت اندازه برای تصویر ۵MB، سایر انواع ۲۰MB در مستند).
3. **`multipart/form-data`** — آپلود مستقیم (تصویر تا ۱۰MB، سایر تا ۵۰MB در بخش «ارسال فایل‌ها» مستند).

محدودیت‌های نوع فایل هنگام ارسال مجدد با `file_id` و موارد خاص URL/voice مانند مستند اصلی اعمال می‌شود.

---

## متدهای API

نام متدها case-insensitive است. پارامترها مانند تلگرام؛ برای جزئیات هر متد به جداول بالای پیام مراجعه کنید.

### عمومی و آپدیت

| متد | کار |
|-----|-----|
| getMe | تست توکن؛ برمی‌گرداند User بازو |
| getUpdates | دریافت آپدیت (long polling) |
| setWebhook / deleteWebhook / getWebhookInfo | مدیریت وب‌هوک |

### پیام و رسانه

| متد | کار |
|-----|-----|
| sendMessage | متن؛ در بله قالب‌بندی **Markdown** (bold با ستاره، italic با زیرخط، لینک `[متن](url)`؛ پیش‌نمایش آنی: متن داخل کروشه + توضیح، قبل و بعد با سه کاراکتر بک‌تیک طبق مستند بله) |
| forwardMessage | بازارسال |
| copyMessage | کپی بدون لینک به اصل؛ پیام‌های سرویس/رسید پرداخت قابل کپی نیستند |
| sendPhoto | chat_id، photo (file_id / URL / آپلود)، caption، reply_to_message_id، reply_markup |
| sendAudio | MP3/M4A؛ تا ۵۰MB |
| sendDocument | عمومی؛ تا ۵۰MB |
| sendVideo | MPEG4؛ تا ۵۰MB |
| sendAnimation | GIF / ویدیوی بدون صدا |
| sendVoice | پیام صوتی |
| sendMediaGroup | آلبوم |
| sendLocation | |
| sendContact | |
| sendChatAction | typing، upload_photo، … (حداکثر ~۶ ثانیه نمایش) |

### فایل و تعامل

| متد | کار |
|-----|-----|
| getFile | گرفتن `file_path` برای دانلود |
| answerCallbackQuery | **الزامی** پس از کلیک inline؛ در غیر این صورت دکمه در حالت انتظار می‌ماند. پارامترها: callback_query_id، text، show_alert. نکتهٔ نسخهٔ کلاینت: اگر `callback_query_id` با `1` شروع شود، ممکن است ویژگی‌های جدید را پشتیبانی نکند. |
| askReview | رضایت‌سنجی؛ معمولاً با HTTP خام (در همهٔ کتابخانه‌های تلگرام نیست). پارامترها: user_id، delay_seconds |

### مدیریت چت و مدیران

banChatMember، unbanChatMember، promoteChatMember، setChatPhoto، leaveChat، getChat، getChatAdministrators، getChatMembersCount، getChatMember، pinChatMessage، unPinChatMessage، unpinAllChatMessages، setChatTitle، setChatDescription، deleteChatPhoto، createChatInviteLink، revokeChatInviteLink، exportChatInviteLink، …

### ویرایش و حذف پیام

editMessageText، editMessageCaption، editMessageReplyMarkup، deleteMessage — با محدودیت‌های زمانی و نقش بازو مطابق مستند.

---

## پرداخت و کیف پول

- روش رسمی: **کیف پول**؛ پرداخت کارت‌به‌کارت از API بازو حذف شده است.
- **`sendInvoice`** نیاز به **`provider_token`** از @botfather دارد.
- تست: `WALLET-TEST-1111111111111111` (بدون انتقال واقعی پول).
- **`answerPreCheckoutQuery`** حداکثر ظرف **۱۰ ثانیه** پس از `pre_checkout_query`.
- موفقیت نهایی را از پیام حاوی **`successful_payment`** تشخیص دهید، نه تنها از `pre_checkout_query`.
- **`createInvoiceLink`** برای مینی‌اپ‌ها.
- **`inquireTransaction`** برای استعلام تراکنش — معمولاً با HTTP خام.

**LabeledPrice:** `amount` به **ریال** (integer).

**SuccessfulPayment / PreCheckoutQuery:** فیلدها مطابق مستند؛ `currency` برای IRR.

**Transaction** (خروجی inquireTransaction): `status` ∈ `pending`، `paid`، `failed`، `rejected`؛ فیلدهای `id`، `userID`، `amount`، `createdAt`.

---

## استیکرها

متدهای مدیریت استیکر: uploadStickerFile، createNewStickerSet، addStickerToSet، … با محدودیت تعداد استیکر در هر نوع مجموعه مطابق مستند.

---

## نکات پیاده‌سازی

1. **شناسه‌های بزرگ:** `User.id`، `Chat.id`، برخی `file_size` ممکن است از int32 بزرگ‌تر باشند → از int64 یا رشته استفاده کنید.
2. **offset در موجودیت‌های متن:** UTF-16 code units.
3. **کتابخانهٔ تلگرام:** معمولاً فقط **آدرس پایه API** را به `https://tapi.bale.ai` تغییر دهید؛ متدهای اختصاصی بله (`askReview`، `inquireTransaction`) را با `requests` یا مشابه صدا بزنید.
4. **وب‌هوک:** فقط پورت‌های ۴۴۳ و ۸۸.
5. **پرداخت:** همیشه جریان `pre_checkout_query` → `answerPreCheckoutQuery` → تأیید با `successful_payment` را رعایت کنید.

---

## مرجع

متن بر اساس مستند رسمی «API بازوی بله» تهیه شده؛ در صورت اختلاف با مستند به‌روز بله، نسخهٔ رسمی مرجع است.
