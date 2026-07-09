(function () {
  'use strict';

  var MAX_DEPTH = 20;
  var MEDIA_TYPES = ['image', 'video', 'voice', 'document'];
  var MEDIA_LABELS = {
    image: 'عکس',
    video: 'ویدیو',
    voice: 'صدا',
    document: 'فایل',
  };
  var MEDIA_ICONS = {
    image: 'image',
    video: 'camera-video',
    voice: 'mic',
    document: 'paperclip',
  };
  var MEDIA_ACCEPT = {
    image: 'image/*',
    video: 'video/*,.mp4,.mov,.mkv,.webm',
    voice: 'audio/*,.ogg,.mp3,.m4a,.wav,.opus',
    document: '*/*,.pdf,.zip,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt',
  };
  var ACTION_OPTIONS = [
    ['', 'بدون اکشن'],
    ['text', 'ارسال متن'],
    ['sequence', 'چند پیام / رسانه'],
    ['buttons', 'زیرمنو'],
    ['image', 'ارسال عکس'],
    ['url', 'باز کردن لینک'],
    ['webapp', 'مینی‌اپ فروشگاه'],
    ['order_status', 'رهگیری سفارش'],
    ['my_orders', 'سفارش‌های من'],
    ['input', 'سوال و پاسخ'],
    ['form', 'فرم چندمرحله‌ای'],
    ['handoff', 'پشتیبانی انسانی'],
    ['location_card', 'موقعیت و آدرس'],
    ['contact_card', 'کارت تماس'],
    ['faq', 'سوالات متداول'],
    ['coupon', 'کد تخفیف'],
    ['join_gate', 'عضویت کانال'],
    ['invoice', 'پرداخت بله'],
    ['request_contact', 'درخواست ارسال شماره'],
    ['request_location', 'درخواست موقعیت'],
  ];

  var INTERACTIVE_TYPES = [
    'webapp', 'order_status', 'my_orders', 'invoice', 'location_card', 'contact_card',
    'input', 'form', 'request_contact', 'request_location',
    'condition', 'goto', 'join_gate', 'tag', 'faq', 'coupon', 'handoff',
  ];

  function isInteractiveType(t) {
    return INTERACTIVE_TYPES.indexOf(String(t || '').toLowerCase()) >= 0;
  }

  function defaultInteractiveAction(type) {
    var t = String(type || '').toLowerCase();
    if (t === 'webapp') return { type: 'webapp', label: 'ورود به فروشگاه', target: { kind: 'home', value: '' } };
    if (t === 'order_status') return { type: 'order_status', prompt: 'شماره سفارشت رو بفرست:' };
    if (t === 'my_orders') return { type: 'my_orders', limit: 5 };
    if (t === 'invoice') return { type: 'invoice', title: 'پرداخت', amount: 0, description: '', item_slug: '' };
    if (t === 'location_card') return { type: 'location_card', lat: 35.7, lng: 51.4, address: '', hours: '' };
    if (t === 'contact_card') return { type: 'contact_card', phone: '', name: 'پشتیبانی' };
    if (t === 'input') return { type: 'input', prompt: '', save_key: 'answer', validate: 'text', next: { type: 'text', body: 'ممنون!' } };
    if (t === 'form') {
      return {
        type: 'form',
        title: 'فرم',
        steps: [{ prompt: 'نام؟', save_key: 'name', validate: 'text' }],
        on_complete: { notify_admin: true, thank_you: 'ثبت شد.', assign_tag: '' },
      };
    }
    if (t === 'request_contact') return { type: 'request_contact', prompt: 'شماره‌ت رو بفرست', assign_tag: '' };
    if (t === 'request_location') return { type: 'request_location', prompt: 'موقعیتت رو بفرست', save_key: 'loc' };
    if (t === 'condition') {
      return {
        type: 'condition',
        if: { kind: 'has_tag', value: '' },
        then: { type: 'text', body: '' },
        else: { type: 'text', body: '' },
      };
    }
    if (t === 'goto') return { type: 'goto', target_id: '' };
    if (t === 'join_gate') return { type: 'join_gate', channel: '', prompt: 'اول عضو کانال شو', then: { type: 'text', body: 'خوش اومدی!' } };
    if (t === 'tag') return { type: 'tag', add: [], remove: [] };
    if (t === 'faq') return { type: 'faq', title: 'سوالات متداول', items: [{ q: 'سوال؟', a: 'پاسخ' }] };
    if (t === 'coupon') return { type: 'coupon', discount_id: null, code: '', message: '' };
    if (t === 'handoff') return { type: 'handoff', message: 'پیامت رو بفرست' };
    return null;
  }

  function normalizeInteractiveAction(action) {
    if (!action || !isInteractiveType(action.type)) return null;
    try {
      return JSON.parse(JSON.stringify(action));
    } catch (e) {
      return null;
    }
  }

  var PALETTE_ICONS = {
    text: 'chat-text',
    image: 'image',
    video: 'camera-video',
    voice: 'mic',
    document: 'paperclip',
    buttons: 'ui-checks-grid',
    webapp: 'shop',
    order_status: 'truck',
    my_orders: 'bag-check',
    invoice: 'credit-card',
    coupon: 'ticket-perforated',
    input: 'chat-dots',
    form: 'ui-radios',
    faq: 'question-circle',
    handoff: 'headset',
    join_gate: 'people',
    request_contact: 'telephone',
    request_location: 'geo-alt',
    location_card: 'pin-map',
    contact_card: 'person-vcard',
    tag: 'tags',
    condition: 'signpost-split',
    goto: 'arrow-return-right',
  };

  var PALETTE_DESCRIPTIONS = {
    text: 'پیام متنی در چت',
    image: 'ارسال عکس',
    video: 'ارسال ویدیو',
    voice: 'ارسال پیام صوتی',
    document: 'ارسال فایل یا PDF',
    buttons: 'ردیف دکمه برای منو',
    webapp: 'باز کردن فروشگاه مینی‌اپ',
    order_status: 'پیگیری وضعیت سفارش',
    my_orders: 'لیست سفارش‌های کاربر',
    invoice: 'درخواست پرداخت بله',
    coupon: 'نمایش کد تخفیف',
    input: 'سوال از کاربر و ذخیره پاسخ',
    form: 'فرم چندمرحله‌ای',
    faq: 'سوالات متداول',
    handoff: 'انتقال به پشتیبانی انسانی',
    join_gate: 'اجبار عضویت در کانال',
    request_contact: 'درخواست ارسال شماره',
    request_location: 'درخواست ارسال موقعیت',
    location_card: 'نمایش آدرس روی نقشه',
    contact_card: 'کارت تماس با شماره',
    tag: 'افزودن یا حذف برچسب',
    condition: 'شرط بر اساس برچسب یا پاسخ',
    goto: 'پرش به بخش دیگر منو',
  };

  var state = null;
  var hiddenId = 'id_start_flow';
  var uploadUrl = '';
  var miniAppUrl = '';
  var hasMiniApp = false;
  var threadEl = null;
  var paletteEl = null;
  var outlineEl = null;
  var itemCountEl = null;
  var paletteHintEl = null;
  var toolbarTargetEl = null;
  var editorRootEl = null;
  var mobileApi = null;
  var inspectorBody = null;
  var inspectorTitle = null;
  var inspectorHint = null;
  var paletteFilter = 'all';
  var paletteSearch = '';
  var paletteFiltersEl = null;
  var quickAddEl = null;
  var paletteSearchEl = null;
  var dockTabsEl = null;
  var selection = null;
  var discountCodes = [];

  var PALETTE_FILTER_OPTIONS = [
    ['all', 'همه'],
    ['content', 'محتوا'],
    ['menu', 'منو'],
    ['shop', 'فروشگاه'],
    ['engage', 'تعامل'],
    ['advanced', 'پیشرفته'],
  ];

  var QUICK_ADD_TYPES = ['text', 'button', 'image'];

  function $(id) {
    return document.getElementById(id);
  }

  function newNodeId() {
    return 'n_' + Math.random().toString(16).slice(2, 10);
  }

  function defaultButton() {
    return { id: newNodeId(), text: '', category_slug: '', action: null };
  }

  function slugifyLabel(raw, fallbackId) {
    var s = String(raw || '').trim();
    var ascii = s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    if (ascii && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(ascii)) {
      return ascii.slice(0, 140);
    }
    if (fallbackId) {
      var fid = String(fallbackId).replace(/^n_/, 'btn-').toLowerCase().replace(/[^a-z0-9-]+/g, '');
      if (fid) return fid.slice(0, 140);
    }
    return '';
  }

  function buttonHasCategory(btn) {
    return Boolean(String(btn.category_slug || '').trim());
  }

  function ensureButtonCategorySlug(btn) {
    if (!btn.id) btn.id = newNodeId();
    var slug = slugifyLabel(btn.text, btn.id);
    if (slug) btn.category_slug = slug;
  }

  function appendButtonChipMeta(chip, btn) {
    if (buttonHasCategory(btn)) {
      var cat = document.createElement('small');
      cat.className = 'flow-canvas-category-badge';
      cat.textContent = 'دسته‌بندی';
      chip.appendChild(cat);
      chip.classList.add('has-category');
    } else if (btn.action) {
      var hint = document.createElement('small');
      hint.textContent = actionHint(btn.action);
      chip.appendChild(hint);
    }
  }

  function defaultSequence() {
    return { type: 'sequence', items: [] };
  }

  function defaultMediaItem(mediaType) {
    return { type: mediaType, media_id: '', caption: '' };
  }

  function emptyFlow() {
    return { version: 2, root: defaultSequence() };
  }

  function isMediaType(t) {
    return MEDIA_TYPES.indexOf(String(t || '').toLowerCase()) >= 0;
  }

  function actionHint(action) {
    if (!action || !action.type) return '';
    var t = action.type;
    if (t === 'url') return 'لینک';
    if (t === 'text') return 'متن';
    if (t === 'buttons') return 'زیرمنو';
    if (t === 'sequence') return 'چند آیتم';
    if (isMediaType(t)) return MEDIA_LABELS[t] || t;
    if (isInteractiveType(t)) {
      var hint = t;
      ACTION_OPTIONS.forEach(function (o) {
        if (o[0] === t) hint = o[1];
      });
      if (t === 'coupon') {
        if (action.code) return 'تخفیف · ' + action.code;
        if (action.discount_id != null) {
          var dc = findDiscountCode(action.discount_id);
          if (dc) return 'تخفیف · ' + dc.code;
        }
      }
      return hint;
    }
    return t;
  }

  function normalizeMediaItem(item, mediaType) {
    var mid = String(item.media_id || '').trim();
    if (!mid) return null;
    return {
      type: mediaType,
      media_id: mid,
      caption: String(item.caption || '').slice(0, 1024),
    };
  }

  function normalizeMiniSequence(seq) {
    if (!seq || String(seq.type).toLowerCase() !== 'sequence') return null;
    var items = [];
    (seq.items || []).forEach(function (item) {
      if (!item) return;
      var t = String(item.type || '').toLowerCase();
      if (t === 'text') {
        var body = String(item.body || item.text || '').trim();
        if (body) items.push({ type: 'text', body: body.slice(0, 4096) });
      } else if (isMediaType(t)) {
        var media = normalizeMediaItem(item, t);
        if (media) items.push(media);
      }
    });
    return items.length ? { type: 'sequence', items: items } : null;
  }

  function normalizeAction(action, depth) {
    if (!action || depth > MAX_DEPTH) return null;
    var t = String(action.type || '').toLowerCase();
    if (t === 'text') {
      var body = String(action.body || action.text || '').trim().slice(0, 4096);
      return body ? { type: 'text', body: body } : null;
    }
    if (isMediaType(t)) return normalizeMediaItem(action, t);
    if (t === 'sequence') return normalizeMiniSequence(action);
    if (t === 'url') {
      var url = String(action.url || '').trim().slice(0, 512);
      return url ? { type: 'url', url: url } : null;
    }
    if (t === 'buttons') return normalizeButtons({ type: 'buttons', rows: action.rows }, depth);
    if (isInteractiveType(t)) return normalizeInteractiveAction(action);
    return null;
  }

  function normalizeButton(btn, depth) {
    if (!btn || depth > MAX_DEPTH) return null;
    var text = String(btn.text || btn.label || '').trim().slice(0, 64);
    var action = btn.action ? normalizeAction(btn.action, depth + 1) : null;
    if (!text && !action) return null;
    var idRaw = String(btn.id || '').trim();
    var idOk = /^n_[a-zA-Z0-9_]{1,48}$/.test(idRaw);
    var out = {
      id: idOk ? idRaw.slice(0, 56) : newNodeId(),
      text: text || '…',
    };
    var slug = String(btn.category_slug || '').trim().slice(0, 140);
    if (slug) out.category_slug = slug;
    if (action) out.action = action;
    return out;
  }

  function normalizeButtons(node, depth) {
    if (!node || depth > MAX_DEPTH) return null;
    var rowsOut = [];
    (node.rows || []).forEach(function (row) {
      if (!Array.isArray(row)) return;
      var r = [];
      row.forEach(function (b) {
        var nb = normalizeButton(b, depth);
        if (nb) r.push(nb);
      });
      if (r.length) rowsOut.push(r);
    });
    return rowsOut.length ? { type: 'buttons', rows: rowsOut } : null;
  }

  function buttonItemFromNode(btn, depth, row) {
    var nb = normalizeButton(btn, depth);
    if (!nb) return null;
    var out = { type: 'button', id: nb.id, text: nb.text, action: nb.action || null };
    if (nb.category_slug) out.category_slug = nb.category_slug;
    if (row !== undefined && row !== null) out.row = row;
    else if (btn.row !== undefined && btn.row !== null) out.row = btn.row;
    return out;
  }

  function flattenToIndependentItems(items) {
    var out = [];
    (items || []).forEach(function (item) {
      if (!item) return;
      var t = String(item.type || '').toLowerCase();
      if (t === 'buttons') {
        (item.rows || []).forEach(function (row, rowIdx) {
          (row || []).forEach(function (btn) {
            var bi = buttonItemFromNode(btn, 0, rowIdx);
            if (bi) out.push(bi);
          });
        });
      } else if (t === 'button') {
        var flat = buttonItemFromNode(item, 0);
        if (flat) out.push(flat);
      } else {
        out.push(item);
      }
    });
    return out;
  }

  function normalizeSequence(seq, depth) {
    if (!seq || String(seq.type).toLowerCase() !== 'sequence') return defaultSequence();
    var items = [];
    (seq.items || []).forEach(function (item) {
      if (!item) return;
      var t = String(item.type || '').toLowerCase();
      if (t === 'text') {
        var body = String(item.body || item.text || '').trim();
        if (body) items.push({ type: 'text', body: body.slice(0, 4096) });
      } else if (isMediaType(t)) {
        var media = normalizeMediaItem(item, t);
        if (media) items.push(media);
      } else if (t === 'buttons') {
        var b = normalizeButtons(item, depth);
        if (b) items.push(b);
      } else if (t === 'button') {
        var bi = buttonItemFromNode(item, depth);
        if (bi) items.push(bi);
      } else if (isInteractiveType(t)) {
        var ia = normalizeInteractiveAction(item);
        if (ia) items.push(ia);
      }
    });
    return { type: 'sequence', items: flattenToIndependentItems(items) };
  }

  function parseHidden() {
    var el = $(hiddenId);
    if (!el || !String(el.value).trim()) return emptyFlow();
    try {
      var data = JSON.parse(el.value);
      if (data && data.version === 2 && data.root) {
        return { version: 2, root: normalizeSequence(data.root, 0) };
      }
    } catch (e) {
      /* ignore */
    }
    return emptyFlow();
  }

  function syncHidden() {
    var el = $(hiddenId);
    if (el) el.value = JSON.stringify(state);
  }

  function uploadMedia(file, onOk, onErr) {
    if (!uploadUrl) {
      onErr('آدرس آپلود تنظیم نشده.');
      return;
    }
    var fd = new FormData();
    fd.append('file', file);
    var csrf =
      document.querySelector('[name=csrfmiddlewaretoken]') &&
      document.querySelector('[name=csrfmiddlewaretoken]').value;
    fetch(uploadUrl, {
      method: 'POST',
      body: fd,
      headers: csrf ? { 'X-CSRFToken': csrf } : {},
      credentials: 'same-origin',
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && j.ok && j.media_id) onOk(j);
        else onErr((j && j.error) || 'خطا در آپلود');
      })
      .catch(function () {
        onErr('خطا در ارتباط با سرور');
      });
  }

  function pathSegmentKey(seg) {
    if (!seg || !seg.kind) return '';
    if (seg.kind === 'item') return 'i' + seg.index;
    if (seg.kind === 'btn') return 'r' + seg.row + 'b' + seg.btn;
    return String(seg.kind);
  }

  function selKey(sel) {
    if (!sel) return '';
    var parts = (sel.path || []).map(pathSegmentKey);
    return sel.kind + ':' + parts.join('/');
  }

  function pathsEqual(a, b) {
    if (!a || !b) return false;
    if (a.kind !== b.kind) return false;
    var pa = a.path || [];
    var pb = b.path || [];
    if (pa.length !== pb.length) return false;
    for (var i = 0; i < pa.length; i += 1) {
      if (pathSegmentKey(pa[i]) !== pathSegmentKey(pb[i])) return false;
    }
    return true;
  }

  function resolveAtPath(path) {
    var ref = { node: state.root, item: null, itemIndex: -1, buttons: null, button: null, rowIndex: -1, btnIndex: -1 };
    if (!path.length) return ref;

    var seg = path[0];
    if (seg.kind !== 'item') return null;
    var item = state.root.items[seg.index];
    if (!item) return null;
    ref.item = item;
    ref.itemIndex = seg.index;

    if (path.length === 1) return ref;

    var buttons = item.type === 'buttons' ? item : null;
    if (!buttons) return null;

    for (var i = 1; i < path.length; i += 1) {
      var s = path[i];
      if (s.kind !== 'btn') return null;
      var row = buttons.rows[s.row];
      if (!row) return null;
      var btn = row[s.btn];
      if (!btn) return null;
      ref.buttons = buttons;
      ref.button = btn;
      ref.rowIndex = s.row;
      ref.btnIndex = s.btn;
      if (i < path.length - 1) {
        if (!btn.action || btn.action.type !== 'buttons') return null;
        buttons = btn.action;
      }
    }
    return ref;
  }

  function cloneJson(obj) {
    try {
      return JSON.parse(JSON.stringify(obj));
    } catch (e) {
      return null;
    }
  }

  function pruneEmptyButtonRows(buttons) {
    if (!buttons || !buttons.rows) return;
    buttons.rows = (buttons.rows || []).filter(function (row) {
      return row && row.length;
    });
    if (!buttons.rows.length) buttons.rows = [[defaultButton()]];
  }

  function removeButtonAt(ref) {
    if (!ref || !ref.buttons || ref.rowIndex < 0 || ref.btnIndex < 0) return null;
    var row = ref.buttons.rows[ref.rowIndex];
    if (!row || !row[ref.btnIndex]) return null;
    var btn = cloneJson(row[ref.btnIndex]);
    row.splice(ref.btnIndex, 1);
    if (!row.length) {
      ref.buttons.rows.splice(ref.rowIndex, 1);
    }
    pruneEmptyButtonRows(ref.buttons);
    return btn;
  }

  function isTopLevelButtonSelection(path) {
    return path && path.length === 2 && path[0].kind === 'item' && path[1].kind === 'btn';
  }

  function listTopLevelButtonsBlocks(excludeIndex) {
    var out = [];
    var n = 0;
    state.root.items.forEach(function (item, idx) {
      if (!item || item.type !== 'buttons') return;
      if (idx === excludeIndex) return;
      n += 1;
      var count = 0;
      (item.rows || []).forEach(function (row) {
        count += (row || []).length;
      });
      out.push({ index: idx, label: 'منو #' + n + ' (' + count + ' دکمه)' });
    });
    return out;
  }

  function extractButtonToNewBlock(ref, path) {
    if (!isTopLevelButtonSelection(path)) return false;
    var btn = removeButtonAt(ref);
    if (!btn) return false;
    var insertAt = ref.itemIndex + 1;
    state.root.items.splice(insertAt, 0, { type: 'buttons', rows: [[btn]] });
    selectPath([{ kind: 'item', index: insertAt }], 'item');
    return true;
  }

  function convertButtonToStandaloneBlock(ref, path) {
    if (!isTopLevelButtonSelection(path)) return false;
    var action = ref.button && ref.button.action;
    if (!action) return false;
    var atype = String(action.type || '').toLowerCase();
    if (!isInteractiveType(atype) || atype === 'buttons') return false;
    var node = cloneJson(action);
    if (!node) return false;
    if (!removeButtonAt(ref)) return false;
    var insertAt = ref.itemIndex + 1;
    state.root.items.splice(insertAt, 0, node);
    selectPath([{ kind: 'item', index: insertAt }], 'item');
    return true;
  }

  function moveButtonToBlock(ref, path, targetIndex) {
    if (!isTopLevelButtonSelection(path)) return false;
    var target = state.root.items[targetIndex];
    if (!target || target.type !== 'buttons' || targetIndex === ref.itemIndex) return false;
    var btn = removeButtonAt(ref);
    if (!btn) return false;
    target.rows.push([btn]);
    selectPath([{ kind: 'item', index: targetIndex }], 'item');
    return true;
  }

  function newContentNode(type) {
    if (type === 'text') return { type: 'text', body: '' };
    if (type === 'button') {
      return { type: 'button', id: newNodeId(), text: '', category_slug: '', action: null };
    }
    if (type === 'buttons') return { type: 'buttons', rows: [[defaultButton()]] };
    if (isMediaType(type)) return defaultMediaItem(type);
    if (isInteractiveType(type)) return defaultInteractiveAction(type);
    return null;
  }

  function buildPaletteGroups() {
    var groups = [
      {
        id: 'content',
        group: 'پیام و رسانه',
        blocks: ['text', 'image', 'video', 'voice', 'document'],
      },
      {
        id: 'menu',
        group: 'منو',
        blocks: ['button'],
      },
    ];
    if (hasMiniApp) {
      groups.push({
        id: 'shop',
        group: 'فروشگاه',
        blocks: ['webapp', 'order_status', 'my_orders', 'invoice', 'coupon'],
      });
    }
    groups.push({
      id: 'engage',
      group: 'تعامل',
      blocks: ['input', 'form', 'faq', 'handoff', 'join_gate', 'request_contact', 'request_location'],
    });
    groups.push({
      id: 'info',
      group: 'اطلاعات',
      blocks: ['location_card', 'contact_card'],
    });
    groups.push({
      id: 'advanced',
      group: 'پیشرفته',
      blocks: ['tag', 'condition', 'goto'],
    });
    return groups;
  }

  function paletteCategoryForType(type) {
    var found = '';
    buildPaletteGroups().forEach(function (g) {
      if (g.blocks.indexOf(type) >= 0) found = g.id;
    });
    if (found === 'info') return 'engage';
    return found;
  }

  function paletteMatchesFilter(type) {
    if (paletteFilter !== 'all' && paletteCategoryForType(type) !== paletteFilter) return false;
    if (!paletteSearch) return true;
    var q = paletteSearch.trim().toLowerCase();
    var label = paletteLabel(type).toLowerCase();
    var desc = (paletteDescription(type) || '').toLowerCase();
    return label.indexOf(q) >= 0 || desc.indexOf(q) >= 0 || type.indexOf(q) >= 0;
  }

  function switchDockTab(tabId) {
    if (!dockTabsEl || !editorRootEl) return;
    dockTabsEl.querySelectorAll('.bot-studio-tab').forEach(function (btn) {
      var active = btn.getAttribute('data-dock-tab') === tabId;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    editorRootEl.querySelectorAll('.bot-studio-panel').forEach(function (panel) {
      var active = panel.getAttribute('data-dock-panel') === tabId;
      panel.classList.toggle('is-active', active);
      panel.hidden = !active;
    });
  }

  function renderPaletteFilters() {
    if (!paletteFiltersEl) return;
    paletteFiltersEl.innerHTML = '';
    PALETTE_FILTER_OPTIONS.forEach(function (pair) {
      if (pair[0] === 'shop' && !hasMiniApp) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bot-studio-filter' + (paletteFilter === pair[0] ? ' is-active' : '');
      btn.textContent = pair[1];
      btn.setAttribute('data-filter', pair[0]);
      btn.addEventListener('click', function () {
        paletteFilter = pair[0];
        renderPaletteFilters();
        renderBlockPalette();
      });
      paletteFiltersEl.appendChild(btn);
    });
  }

  function renderQuickAdd() {
    if (!quickAddEl) return;
    quickAddEl.innerHTML = '';
    QUICK_ADD_TYPES.forEach(function (type) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bot-studio-quick-btn';
      btn.title = paletteDescription(type) || paletteLabel(type);
      btn.innerHTML =
        '<i class="bi bi-' +
        (PALETTE_ICONS[type] || 'plus') +
        '"></i><span>' +
        escapeHtml(paletteLabel(type)) +
        '</span>';
      btn.addEventListener('click', function () {
        addItem(type);
      });
      quickAddEl.appendChild(btn);
    });
  }

  function mkPaletteTile(type) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bot-studio-tile bot-studio-tile--' + paletteCategoryForType(type);
    btn.setAttribute('data-add-type', type);
    btn.title = paletteDescription(type) || paletteLabel(type);
    btn.innerHTML =
      '<span class="bot-studio-tile-icon"><i class="bi bi-' +
      (PALETTE_ICONS[type] || 'plus') +
      '"></i></span>' +
      '<span class="bot-studio-tile-label">' +
      escapeHtml(paletteLabel(type)) +
      '</span>';
    btn.addEventListener('click', function () {
      addItem(type);
    });
    return btn;
  }

  function paletteLabel(type) {
    var label = type;
    ACTION_OPTIONS.forEach(function (o) {
      if (o[0] === type) label = o[1];
    });
    if (isMediaType(type)) label = MEDIA_LABELS[type] || type;
    if (type === 'text') label = 'متن';
    if (type === 'button') label = 'دکمه منو';
    if (type === 'buttons') label = 'زیرمنو';
    if (type === 'request_contact') label = 'درخواست شماره';
    if (type === 'request_location') label = 'درخواست موقعیت';
    return label;
  }

  function itemSummary(item) {
    if (!item) return 'آیتم';
    var t = String(item.type || '');
    if (t === 'text') {
      var body = String(item.body || '').trim();
      return body ? body.slice(0, 36) + (body.length > 36 ? '…' : '') : 'متن خالی';
    }
    if (isMediaType(t)) {
      return (MEDIA_LABELS[t] || t) + (item.media_id ? '' : ' · بدون فایل');
    }
    if (t === 'buttons') {
      var count = 0;
      (item.rows || []).forEach(function (row) {
        count += (row || []).length;
      });
      return 'زیرمنو · ' + count + ' دکمه';
    }
    if (t === 'button') {
      return buttonSummary(item);
    }
    if (isInteractiveType(t)) {
      var label = paletteLabel(t);
      var preview = item.prompt || item.title || item.message || item.label || item.code || '';
      preview = String(preview || '').trim();
      return preview ? label + ' · ' + preview.slice(0, 28) : label;
    }
    return t;
  }

  function buttonSummary(btn) {
    var text = String((btn && btn.text) || '').trim() || 'دکمه جدید';
    if (btn && btn.action) return text + ' → ' + actionHint(btn.action);
    return text;
  }

  function updateItemCountLabel() {
    if (!itemCountEl) return;
    var n = (state && state.root && state.root.items) ? state.root.items.length : 0;
    itemCountEl.textContent = n + ' آیتم';
  }

  function scrollSelectionIntoView() {
    if (!threadEl || !selection) return;
    var key = selKey(selection);
    var node = threadEl.querySelector('[data-flow-sel="' + key + '"]');
    if (node && node.scrollIntoView) {
      node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function paletteDescription(type) {
    return PALETTE_DESCRIPTIONS[type] || '';
  }

  function renderBlockPalette() {
    if (!paletteEl) return;
    paletteEl.innerHTML = '';

    var any = false;
    buildPaletteGroups().forEach(function (group) {
      if (paletteFilter !== 'all' && paletteFilter !== group.id && !(paletteFilter === 'engage' && group.id === 'info')) {
        return;
      }

      var visible = group.blocks.filter(paletteMatchesFilter);
      if (!visible.length) return;

      any = true;
      var section = document.createElement('div');
      section.className = 'bot-studio-palette-group';

      if (paletteFilter === 'all') {
        var title = document.createElement('div');
        title.className = 'bot-studio-palette-group-title';
        title.textContent = group.group;
        section.appendChild(title);
      }

      var grid = document.createElement('div');
      grid.className = 'bot-studio-tile-grid';
      visible.forEach(function (type) {
        grid.appendChild(mkPaletteTile(type));
      });
      section.appendChild(grid);
      paletteEl.appendChild(section);
    });

    if (!any) {
      paletteEl.innerHTML =
        '<div class="bot-studio-palette-empty"><i class="bi bi-search"></i><p>ویژگی‌ای پیدا نشد</p></div>';
    }
  }

  function renderFlowOutline() {
    if (!outlineEl) return;
    outlineEl.innerHTML = '';
    if (!state.root.items.length) {
      outlineEl.innerHTML =
        '<div class="bot-flow-outline-empty">هنوز آیتمی اضافه نشده — از کتابخانه شروع کنید</div>';
      return;
    }

    function appendButtonRows(rows, basePath, depth) {
      (rows || []).forEach(function (row, ri) {
        (row || []).forEach(function (btn, bi) {
          var btnPath = basePath.concat([{ kind: 'btn', row: ri, btn: bi }]);
          var rowBtn = document.createElement('button');
          rowBtn.type = 'button';
          rowBtn.className =
            'bot-outline-item bot-outline-item--button' +
            (isSelected(btnPath, 'button') ? ' is-selected' : '');
          rowBtn.style.paddingInlineStart = 0.65 + depth * 0.55 + 'rem';
          rowBtn.setAttribute('data-flow-sel', selKey({ kind: 'button', path: btnPath }));
          rowBtn.innerHTML =
            '<i class="bi bi-ui-radios bot-outline-icon"></i>' +
            '<span class="bot-outline-label">' +
            escapeHtml(buttonSummary(btn)) +
            '</span>';
          rowBtn.addEventListener('click', function () {
            selectPath(btnPath, 'button');
          });
          outlineEl.appendChild(rowBtn);
          if (btn.action && btn.action.type === 'buttons') {
            appendButtonRows(btn.action.rows, btnPath, depth + 1);
          }
        });
      });
    }

    state.root.items.forEach(function (item, index) {
      var path = [{ kind: 'item', index: index }];
      var row = document.createElement('button');
      row.type = 'button';
      row.className =
        'bot-outline-item' + (isSelected(path, 'item') ? ' is-selected' : '');
      row.setAttribute('data-flow-sel', selKey({ kind: 'item', path: path }));
      var icon = 'chat-text';
      var t = String(item.type || '');
      if (isMediaType(t)) icon = MEDIA_ICONS[t] || 'paperclip';
      else if (t === 'button') icon = 'ui-radios';
      else if (t === 'buttons') icon = 'ui-checks-grid';
      else if (isInteractiveType(t)) icon = PALETTE_ICONS[t] || 'lightning';
      row.innerHTML =
        '<span class="bot-outline-index">' +
        (index + 1) +
        '</span>' +
        '<i class="bi bi-' +
        icon +
        ' bot-outline-icon"></i>' +
        '<span class="bot-outline-label">' +
        escapeHtml(itemSummary(item)) +
        '</span>';
      row.addEventListener('click', function () {
        selectPath(path, 'item');
      });
      outlineEl.appendChild(row);
      if (t === 'buttons') {
        appendButtonRows(item.rows, path, 1);
      }
    });
  }

  function canMergeIntoSequence(action) {
    if (!action || !action.type) return false;
    var t = action.type;
    return t === 'text' || isMediaType(t);
  }

  function actionAsSequenceItems(action) {
    if (!action) return [];
    if (action.type === 'sequence') return (action.items || []).slice();
    if (canMergeIntoSequence(action)) return [JSON.parse(JSON.stringify(action))];
    return [];
  }

  function ensureButtonSubmenu(btn) {
    if (!btn.action || btn.action.type !== 'buttons') {
      btn.action = { type: 'buttons', rows: [] };
    }
    return btn.action;
  }

  function addButtonToSubmenu(btn, sameRow) {
    var sub = ensureButtonSubmenu(btn);
    var rowIdx;
    var btnIdx;
    if (sameRow && sub.rows.length) {
      rowIdx = sub.rows.length - 1;
      sub.rows[rowIdx].push(defaultButton());
      btnIdx = sub.rows[rowIdx].length - 1;
    } else {
      sub.rows.push([defaultButton()]);
      rowIdx = sub.rows.length - 1;
      btnIdx = 0;
    }
    return { row: rowIdx, btn: btnIdx };
  }

  function appendToButtonAction(btn, type) {
    var node = newContentNode(type);
    if (!node || !btn) return false;

    if (type === 'buttons') {
      addButtonToSubmenu(btn, false);
      return true;
    }

    if (!btn.action) {
      btn.action = node;
      return true;
    }

    if (btn.action.type === 'sequence') {
      if (!btn.action.items) btn.action.items = [];
      btn.action.items.push(node);
      return true;
    }

    if (canMergeIntoSequence(btn.action)) {
      btn.action = {
        type: 'sequence',
        items: actionAsSequenceItems(btn.action).concat([node]),
      };
      return true;
    }

    btn.action = node;
    return true;
  }

  function updateToolbarContext() {
    if (paletteHintEl) {
      if (selection && selection.kind === 'button') {
        var ref = resolveAtPath(selection.path);
        var name = ref && ref.button ? (ref.button.text || '').trim() || 'دکمه' : 'دکمه';
        paletteHintEl.textContent = 'افزودن به اکشن دکمه «' + name + '»';
      } else {
        paletteHintEl.textContent = 'آیتم را از پنل چپ اضافه کنید · روی canvas ویرایش کنید';
      }
    }

    if (toolbarTargetEl) {
      if (selection && selection.kind === 'button') {
        var refBtn = resolveAtPath(selection.path);
        var btnName = refBtn && refBtn.button ? (refBtn.button.text || '').trim() || 'دکمه' : 'دکمه';
        toolbarTargetEl.innerHTML = '<i class="bi bi-cursor"></i> ' + escapeHtml(btnName);
        toolbarTargetEl.hidden = false;
      } else {
        toolbarTargetEl.hidden = true;
        toolbarTargetEl.textContent = '';
      }
    }

    if (editorRootEl) {
      editorRootEl.classList.toggle('is-button-target', !!(selection && selection.kind === 'button'));
      if (selection && selection.kind === 'button') switchDockTab('add');
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function selectPath(path, kind) {
    selection = { kind: kind, path: path.slice() };
    renderCanvas();
    renderInspector();
    renderFlowOutline();
    updateToolbarContext();
    scrollSelectionIntoView();
    if (mobileApi) mobileApi.onSelection();
  }

  function toggleSelect(path, kind) {
    if (isSelected(path, kind)) clearSelection();
    else selectPath(path, kind);
  }

  function clearSelection() {
    selection = null;
    renderCanvas();
    renderInspector();
    renderFlowOutline();
    updateToolbarContext();
    if (mobileApi) mobileApi.onClearSelection();
  }

  function stopProp(e) {
    e.stopPropagation();
  }

  var dragPayload = null;
  var pointerDrag = null;
  var pointerDragListenersBound = false;

  function isPageRtl() {
    var dir = document.documentElement.getAttribute('dir') || '';
    if (dir) return dir.toLowerCase() === 'rtl';
    return window.getComputedStyle(document.documentElement).direction === 'rtl';
  }

  function getButtonRowKey(item, index) {
    if (item && item.row !== undefined && item.row !== null) return item.row;
    return index;
  }

  function compactButtonRows() {
    var items = state.root.items;
    var i = 0;
    var nextRow = 0;
    while (i < items.length) {
      if (String(items[i].type || '').toLowerCase() !== 'button') {
        i += 1;
        continue;
      }
      var rowKey = getButtonRowKey(items[i], i);
      var j = i + 1;
      while (j < items.length) {
        var next = items[j];
        if (String(next.type || '').toLowerCase() !== 'button') break;
        if (getButtonRowKey(next, j) !== rowKey) break;
        j += 1;
      }
      for (var k = i; k < j; k += 1) {
        items[k].row = nextRow;
      }
      nextRow += 1;
      i = j;
    }
  }

  function findFlatButtonIndexById(id) {
    if (!id) return -1;
    for (var i = 0; i < state.root.items.length; i += 1) {
      var item = state.root.items[i];
      if (String(item.type || '').toLowerCase() === 'button' && item.id === id) return i;
    }
    return -1;
  }

  function moveIndicesRange(indices, toIndex) {
    if (!indices || !indices.length) return;
    var sorted = indices.slice().sort(function (a, b) {
      return a - b;
    });
    var fromStart = sorted[0];
    var count = sorted.length;
    if (toIndex >= fromStart && toIndex <= fromStart + count) return;

    var items = state.root.items;
    var moving = [];
    var i;
    for (i = sorted.length - 1; i >= 0; i -= 1) {
      moving.unshift(items.splice(sorted[i], 1)[0]);
    }
    var adjusted = toIndex;
    if (toIndex > fromStart) adjusted = toIndex - count;
    for (i = 0; i < moving.length; i += 1) {
      items.splice(adjusted + i, 0, moving[i]);
    }
  }

  function moveFlatButtonToRow(dragIndex, targetIndex, before) {
    var items = state.root.items;
    var dragItem = items[dragIndex];
    if (!dragItem || String(dragItem.type || '').toLowerCase() !== 'button') return -1;

    var dragId = dragItem.id;
    items.splice(dragIndex, 1);
    var adjTarget = dragIndex < targetIndex ? targetIndex - 1 : targetIndex;
    var target = items[adjTarget];
    if (!target || String(target.type || '').toLowerCase() !== 'button') {
      items.splice(dragIndex, 0, dragItem);
      return dragIndex;
    }

    dragItem.row = getButtonRowKey(target, adjTarget);
    var insertAt = before ? adjTarget : adjTarget + 1;
    items.splice(insertAt, 0, dragItem);
    compactButtonRows();
    return findFlatButtonIndexById(dragId);
  }

  function moveFlatButtonToNewLine(dragIndex, insertIndex) {
    var items = state.root.items;
    var dragItem = items[dragIndex];
    if (!dragItem || String(dragItem.type || '').toLowerCase() !== 'button') return -1;

    var dragId = dragItem.id;
    items.splice(dragIndex, 1);
    var adjustedInsert = insertIndex > dragIndex ? insertIndex - 1 : insertIndex;
    dragItem.row = 9999;
    items.splice(adjustedInsert, 0, dragItem);
    compactButtonRows();
    return findFlatButtonIndexById(dragId);
  }

  function clearDropHighlights() {
    if (!threadEl) return;
    threadEl.querySelectorAll('.is-drop-active').forEach(function (el) {
      el.classList.remove('is-drop-active');
    });
    threadEl.querySelectorAll('.is-drop-target-left, .is-drop-target-right').forEach(function (el) {
      el.classList.remove('is-drop-target-left', 'is-drop-target-right');
    });
  }

  function removeDragGhost() {
    if (!pointerDrag || !pointerDrag.ghost) return;
    if (pointerDrag.ghost.parentNode) pointerDrag.ghost.parentNode.removeChild(pointerDrag.ghost);
    pointerDrag.ghost = null;
  }

  function createDragGhost(host) {
    if (!host) return null;
    var ghost = host.cloneNode(true);
    ghost.className = ghost.className + ' flow-canvas-drag-ghost';
    ghost.setAttribute('aria-hidden', 'true');
    ghost.style.width = host.offsetWidth + 'px';
    document.body.appendChild(ghost);
    return ghost;
  }

  function positionDragGhost(clientX, clientY) {
    if (!pointerDrag || !pointerDrag.ghost) return;
    pointerDrag.ghost.style.left = clientX + 14 + 'px';
    pointerDrag.ghost.style.top = clientY + 14 + 'px';
  }

  function elementAtPoint(clientX, clientY) {
    var hidden = [];
    if (pointerDrag && pointerDrag.host) {
      pointerDrag.host.style.visibility = 'hidden';
      hidden.push(pointerDrag.host);
    }
    if (pointerDrag && pointerDrag.ghost) {
      pointerDrag.ghost.style.visibility = 'hidden';
      hidden.push(pointerDrag.ghost);
    }
    var el = document.elementFromPoint(clientX, clientY);
    hidden.forEach(function (node) {
      node.style.visibility = '';
    });
    return el;
  }

  function moveFlatButtonToGap(dragIndex, insertIndex, rowKey) {
    var items = state.root.items;
    var dragItem = items[dragIndex];
    if (!dragItem || String(dragItem.type || '').toLowerCase() !== 'button') return -1;

    var dragId = dragItem.id;
    items.splice(dragIndex, 1);
    var adjustedInsert = insertIndex > dragIndex ? insertIndex - 1 : insertIndex;
    dragItem.row = rowKey;
    items.splice(adjustedInsert, 0, dragItem);
    compactButtonRows();
    return findFlatButtonIndexById(dragId);
  }

  function bumpCanvas() {
    syncHidden();
    renderCanvas();
    renderInspector();
    updateToolbarContext();
  }

  function dropBeforeInRow(clientX, rect) {
    var leftHalf = clientX < rect.left + rect.width / 2;
    return isPageRtl() ? !leftHalf : leftHalf;
  }

  function hitDropTarget(clientX, clientY) {
    if (!pointerDrag || !threadEl) return null;

    var el = elementAtPoint(clientX, clientY);
    if (!el || !threadEl.contains(el)) return null;

    var gap = el.closest('.flow-canvas-chip-gap');
    if (gap && pointerDrag.payload && pointerDrag.payload.kind === 'button') {
      var gapInsert = parseInt(gap.getAttribute('data-insert-index'), 10);
      var gapRow = parseInt(gap.getAttribute('data-row-key'), 10);
      if (!isNaN(gapInsert) && !isNaN(gapRow)) {
        return { type: 'chip-gap', insertIndex: gapInsert, rowKey: gapRow, gap: gap };
      }
    }

    var zone = el.closest('.flow-canvas-drop-zone');
    if (zone) {
      var insertIndex = parseInt(zone.getAttribute('data-insert-index'), 10);
      if (!isNaN(insertIndex)) {
        return { type: 'line', insertIndex: insertIndex, zone: zone };
      }
    }

    var chip = el.closest('.flow-canvas-keyboard-btn[data-flat-button-index]');
    if (chip && pointerDrag.payload && pointerDrag.payload.kind === 'button') {
      var targetIndex = parseInt(chip.getAttribute('data-flat-button-index'), 10);
      if (!isNaN(targetIndex)) {
        var rect = chip.getBoundingClientRect();
        return {
          type: 'chip',
          targetIndex: targetIndex,
          before: dropBeforeInRow(clientX, rect),
          chip: chip,
        };
      }
    }

    return null;
  }

  function updateDropHighlights(target) {
    clearDropHighlights();
    if (!target) return;
    if (target.type === 'line' && target.zone) {
      target.zone.classList.add('is-drop-active');
      return;
    }
    if (target.type === 'chip-gap' && target.gap) {
      target.gap.classList.add('is-drop-active');
      return;
    }
    if (target.type === 'chip' && target.chip) {
      target.chip.classList.toggle('is-drop-target-left', target.before);
      target.chip.classList.toggle('is-drop-target-right', !target.before);
    }
  }

  function applyPointerDrop(target) {
    if (!pointerDrag || !pointerDrag.active || !target) return;

    var payload = pointerDrag.payload;
    if (target.type === 'chip-gap' && payload.kind === 'button') {
      if (target.insertIndex === payload.index || target.insertIndex === payload.index + 1) return;
      var gapIdx = moveFlatButtonToGap(payload.index, target.insertIndex, target.rowKey);
      if (gapIdx >= 0) selectPath([{ kind: 'item', index: gapIdx }], 'item');
      bumpCanvas();
      return;
    }

    if (target.type === 'line') {
      if (payload.kind === 'block') {
        moveIndicesRange(payload.indices, target.insertIndex);
        bumpCanvas();
      } else if (payload.kind === 'button') {
        var newIdx = moveFlatButtonToNewLine(payload.index, target.insertIndex);
        if (newIdx >= 0) selectPath([{ kind: 'item', index: newIdx }], 'item');
        bumpCanvas();
      }
      return;
    }

    if (target.type === 'chip' && payload.kind === 'button') {
      if (target.targetIndex === payload.index) return;
      var movedIdx = moveFlatButtonToRow(payload.index, target.targetIndex, target.before);
      if (movedIdx >= 0) selectPath([{ kind: 'item', index: movedIdx }], 'item');
      bumpCanvas();
    }
  }

  function finishPointerDrag(clientX, clientY) {
    if (!pointerDrag) return;

    var wasActive = pointerDrag.active;
    var target = wasActive ? hitDropTarget(clientX, clientY) : null;

    if (pointerDrag.host) {
      pointerDrag.host.classList.remove('is-dragging', 'is-long-press-drag', 'is-long-press-pending');
      pointerDrag.host.style.pointerEvents = '';
      pointerDrag.host.style.visibility = '';
      pointerDrag.host.style.userSelect = '';
    }
    document.body.style.userSelect = '';
    removeDragGhost();
    if (threadEl) threadEl.classList.remove('is-canvas-dragging');

    if (wasActive) applyPointerDrop(target);

    dragPayload = null;
    pointerDrag = null;
    clearDropHighlights();
  }

  function onDocumentPointerMove(e) {
    if (!pointerDrag) return;

    var dx = Math.abs(e.clientX - pointerDrag.startX);
    var dy = Math.abs(e.clientY - pointerDrag.startY);

    if (!pointerDrag.active) {
      if (dx < 8 && dy < 8) return;
      pointerDrag.active = true;
      dragPayload = pointerDrag.payload;
      if (pointerDrag.host) {
        pointerDrag.host.classList.add('is-dragging');
        pointerDrag.host.style.pointerEvents = 'none';
        pointerDrag.host.style.userSelect = 'none';
        pointerDrag.ghost = createDragGhost(pointerDrag.host);
      }
      document.body.style.userSelect = 'none';
      if (threadEl) threadEl.classList.add('is-canvas-dragging');
    }

    e.preventDefault();
    positionDragGhost(e.clientX, e.clientY);
    var target = hitDropTarget(e.clientX, e.clientY);
    pointerDrag.dropTarget = target;
    updateDropHighlights(target);
  }

  function onDocumentPointerUp(e) {
    if (!pointerDrag) return;
    finishPointerDrag(e.clientX, e.clientY);
  }

  function bindPointerDragListeners() {
    if (pointerDragListenersBound) return;
    pointerDragListenersBound = true;
    document.addEventListener('mousemove', onDocumentPointerMove);
    document.addEventListener('mouseup', onDocumentPointerUp);
    document.addEventListener('touchmove', function (e) {
      if (!pointerDrag || !e.touches.length) return;
      onDocumentPointerMove(e.touches[0]);
    }, { passive: false });
    document.addEventListener('touchend', function (e) {
      if (!pointerDrag) return;
      var t = e.changedTouches && e.changedTouches[0];
      finishPointerDrag(t ? t.clientX : pointerDrag.startX, t ? t.clientY : pointerDrag.startY);
    });
    document.addEventListener('touchcancel', function () {
      if (!pointerDrag) return;
      finishPointerDrag(pointerDrag.startX, pointerDrag.startY);
    });
  }

  function ensureDragHandle(wrap) {
    var existing = wrap.querySelector('.flow-canvas-drag-handle');
    if (existing) return existing;
    var handle = document.createElement('button');
    handle.type = 'button';
    handle.className = 'flow-canvas-drag-handle flow-canvas-block-badge';
    handle.setAttribute('aria-label', 'جابجایی');
    handle.innerHTML = '<i class="bi bi-grip-vertical"></i>';
    wrap.appendChild(handle);
    return handle;
  }

  function beginPointerDrag(sourceEl, clientX, clientY, payload, hostSelector, e) {
    if (e && e.type !== 'touchstart') {
      e.preventDefault();
      e.stopPropagation();
    }
    bindPointerDragListeners();
    pointerDrag = {
      payload: payload,
      handle: sourceEl,
      host: hostSelector ? sourceEl.closest(hostSelector) : sourceEl,
      startX: clientX,
      startY: clientY,
      active: false,
      dropTarget: null,
      ghost: null,
    };
    document.body.style.userSelect = 'none';
  }

  function attachDragSource(sourceEl, payload, hostSelector, ignoreSelector) {
    if (!sourceEl) return;

    sourceEl.addEventListener('dragstart', function (e) {
      e.preventDefault();
    });

    sourceEl.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      if (ignoreSelector && e.target && e.target.closest(ignoreSelector)) return;
      if (window.getSelection) {
        var sel = window.getSelection();
        if (sel && sel.removeAllRanges) sel.removeAllRanges();
      }
      beginPointerDrag(sourceEl, e.clientX, e.clientY, payload, hostSelector, e);
    });

    var useTouchOnHandle =
      !window.FlowCanvasMobile || !window.FlowCanvasMobile.isMobile();
    if (useTouchOnHandle) {
      sourceEl.addEventListener('touchstart', function (e) {
        if (!e.touches.length) return;
        var t = e.touches[0];
        var under = document.elementFromPoint(t.clientX, t.clientY);
        if (ignoreSelector && under && under.closest(ignoreSelector)) return;
        beginPointerDrag(sourceEl, t.clientX, t.clientY, payload, hostSelector, e);
      }, { passive: true });
    }
  }

  function attachBlockTouchInteraction(wrap, payload, ignoreSelector, onTap) {
    if (!wrap || !onTap || !window.FlowCanvasMobile || !FlowCanvasMobile.attachTouchSelectOrDrag) return;
    FlowCanvasMobile.attachTouchSelectOrDrag(wrap, {
      ignoreSelector: ignoreSelector,
      onTap: onTap,
      onStartDrag: function (clientX, clientY) {
        beginPointerDrag(wrap, clientX, clientY, payload, '.flow-canvas-block', null);
      },
    });
  }

  function bindBlockTap(wrap, onTap) {
    wrap.addEventListener('click', function (e) {
      if (window.FlowCanvasMobile && FlowCanvasMobile.shouldSkipClick(wrap)) return;
      if (window.FlowCanvasMobile && FlowCanvasMobile.isMobile()) return;
      onTap(e);
    });
  }

  function decorateBlockDrag(wrap, indices, onTap) {
    if (!wrap || !indices || !indices.length) return;
    wrap.classList.add('flow-canvas-block--draggable');
    var handle = ensureDragHandle(wrap);
    var payload = { kind: 'block', indices: indices.slice() };
    var ignore =
      '.flow-canvas-keyboard-btn, .flow-canvas-button-cell, .flow-canvas-drop-zone, .flow-canvas-chip-gap, .flow-canvas-submenu, .flow-canvas-block--nested, input, textarea, select, a, button';
    wrap.style.userSelect = 'none';

    attachDragSource(wrap, payload, '.flow-canvas-block', ignore);
    if (handle && handle !== wrap) {
      attachDragSource(handle, payload, '.flow-canvas-block', ignore);
    }

    if (onTap) {
      attachBlockTouchInteraction(wrap, payload, ignore, function () {
        onTap();
      });
      bindBlockTap(wrap, onTap);
    }
  }

  function appendChipGap(rowEl, insertIndex, rowKey) {
    var gap = document.createElement('div');
    gap.className = 'flow-canvas-chip-gap';
    gap.setAttribute('data-insert-index', String(insertIndex));
    gap.setAttribute('data-row-key', String(rowKey));
    gap.innerHTML = '<span class="flow-canvas-chip-gap-line" aria-hidden="true"></span>';
    rowEl.appendChild(gap);
    return gap;
  }

  function appendDropZone(insertIndex) {
    if (!threadEl) return;
    var zone = document.createElement('div');
    zone.className = 'flow-canvas-drop-zone';
    zone.setAttribute('data-insert-index', String(insertIndex));
    zone.innerHTML =
      '<span class="flow-canvas-drop-zone-line" aria-hidden="true"></span>' +
      '<span class="flow-canvas-drop-zone-label">ردیف جدید</span>';
    threadEl.appendChild(zone);
  }

  function setupCanvasDragDrop() {
    bindPointerDragListeners();
  }

  function appendInspectorItemActions(container, itemIndex) {
    var tools = document.createElement('div');
    tools.className = 'flow-inspector-item-actions d-flex flex-wrap gap-2 mt-3 pt-3 border-top';

    if (itemIndex > 0) {
      var moveUp = document.createElement('button');
      moveUp.type = 'button';
      moveUp.className = 'btn btn-panel-ghost btn-sm';
      moveUp.innerHTML = '<i class="bi bi-arrow-up"></i> بالا';
      moveUp.addEventListener('click', function () {
        var items = state.root.items;
        var tmp = items[itemIndex - 1];
        items[itemIndex - 1] = items[itemIndex];
        items[itemIndex] = tmp;
        compactButtonRows();
        selectPath([{ kind: 'item', index: itemIndex - 1 }], 'item');
      });
      tools.appendChild(moveUp);
    }

    if (itemIndex < state.root.items.length - 1) {
      var moveDown = document.createElement('button');
      moveDown.type = 'button';
      moveDown.className = 'btn btn-panel-ghost btn-sm';
      moveDown.innerHTML = '<i class="bi bi-arrow-down"></i> پایین';
      moveDown.addEventListener('click', function () {
        var items = state.root.items;
        var tmp = items[itemIndex + 1];
        items[itemIndex + 1] = items[itemIndex];
        items[itemIndex] = tmp;
        compactButtonRows();
        selectPath([{ kind: 'item', index: itemIndex + 1 }], 'item');
      });
      tools.appendChild(moveDown);
    }

    var del = document.createElement('button');
    del.type = 'button';
    del.className = 'btn btn-panel-ghost btn-sm text-danger';
    del.innerHTML = '<i class="bi bi-trash"></i> حذف';
    del.addEventListener('click', function () {
      state.root.items.splice(itemIndex, 1);
      clearSelection();
    });
    tools.appendChild(del);

    container.appendChild(tools);
  }

  function mkBtn(type, icon, title, handler) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'flow-canvas-block-action';
    b.title = title;
    b.innerHTML = '<i class="bi bi-' + icon + '"></i>';
    b.addEventListener('click', function (e) {
      stopProp(e);
      handler();
    });
    return b;
  }

  function isSelected(path, kind) {
    return selection && selection.kind === kind && pathsEqual(selection, { kind: kind, path: path });
  }

  function renderTextBlock(item, itemIndex) {
    var path = [{ kind: 'item', index: itemIndex }];
    var wrap = document.createElement('div');
    wrap.className =
      'flow-canvas-block flow-chat-row flow-chat-row--bot' +
      (isSelected(path, 'item') ? ' is-selected' : '');
    wrap.setAttribute('data-flow-sel', selKey({ kind: 'item', path: path }));

    var bubble = document.createElement('div');
    bubble.className = 'flow-chat-bubble flow-chat-bubble--text flow-canvas-editable-bubble';
    bubble.textContent = (item.body || '').trim() || 'متن خالی — برای ویرایش کلیک کنید';
    if (!(item.body || '').trim()) bubble.classList.add('is-placeholder');

    wrap.appendChild(bubble);
    decorateBlockDrag(wrap, [itemIndex], function () {
      toggleSelect(path, 'item');
    });
    return wrap;
  }

  function renderMediaBlock(item, itemIndex) {
    var path = [{ kind: 'item', index: itemIndex }];
    var t = String(item.type || '');
    var wrap = document.createElement('div');
    wrap.className =
      'flow-canvas-block flow-chat-row flow-chat-row--bot' +
      (isSelected(path, 'item') ? ' is-selected' : '');
    wrap.setAttribute('data-flow-sel', selKey({ kind: 'item', path: path }));

    var bubble = document.createElement('div');
    bubble.className = 'flow-chat-bubble flow-chat-bubble--media';

    var ph = document.createElement('div');
    ph.className = 'flow-chat-media-placeholder flow-chat-media-placeholder--' + t;
    ph.innerHTML =
      '<i class="bi bi-' +
      (MEDIA_ICONS[t] || 'paperclip') +
      '"></i><span>' +
      (MEDIA_LABELS[t] || t) +
      (item.media_id ? ' · آپلود شده' : ' · بدون فایل') +
      '</span>';
    bubble.appendChild(ph);

    if (item.caption) {
      var cap = document.createElement('p');
      cap.className = 'flow-chat-media-caption';
      cap.textContent = item.caption;
      bubble.appendChild(cap);
    }

    wrap.appendChild(bubble);
    decorateBlockDrag(wrap, [itemIndex], function () {
      toggleSelect(path, 'item');
    });
    return wrap;
  }

  function renderButtonChip(btn, path, nestedHost) {
    var btnPath = path.concat([{ kind: 'btn', row: path[path.length - 1].row, btn: path[path.length - 1].btn }]);
    // path for button already includes row/btn in caller

    var chip = document.createElement('button');
    chip.type = 'button';
    chip.className =
      'flow-chat-keyboard-btn flow-canvas-keyboard-btn' +
      (isSelected(btnPath, 'button') ? ' is-selected' : '');

    var label = document.createElement('span');
    label.textContent = (btn.text || '').trim() || 'دکمه جدید';
    chip.appendChild(label);
    appendButtonChipMeta(chip, btn);

    chip.addEventListener('click', function (e) {
      stopProp(e);
      toggleSelect(btnPath, 'button');
    });

    if (btn.action && btn.action.type === 'buttons' && nestedHost) {
      var sub = document.createElement('div');
      sub.className = 'flow-canvas-submenu';
      renderButtonsBlock(btn.action, btnPath, sub, true);
      nestedHost.appendChild(sub);
    }

    return chip;
  }

  function renderButtonsBlock(node, basePath, parentEl, isNested) {
    if (!node.rows || !node.rows.length) node.rows = [[defaultButton()]];

    var wrap = document.createElement('div');
    wrap.className = 'flow-canvas-block flow-chat-row flow-chat-row--bot' + (isNested ? ' flow-canvas-block--nested' : '');

    if (!isNested && basePath.length === 1) {
      var itemIndex = basePath[0].index;
      if (isSelected(basePath, 'item')) wrap.classList.add('is-selected');
      wrap.setAttribute('data-flow-sel', selKey({ kind: 'item', path: basePath }));
      decorateBlockDrag(wrap, [itemIndex], function () {
        toggleSelect(basePath, 'item');
      });
    }

    var kb = document.createElement('div');
    kb.className = 'flow-chat-keyboard flow-canvas-keyboard';

    node.rows.forEach(function (row, ri) {
      var rowEl = document.createElement('div');
      rowEl.className = 'flow-chat-keyboard-row';

      row.forEach(function (btn, bi) {
        var btnPath = basePath.concat([{ kind: 'btn', row: ri, btn: bi }]);
        var cell = document.createElement('div');
        cell.className = 'flow-canvas-keyboard-cell';

        var chip = document.createElement('button');
        chip.type = 'button';
        chip.className =
          'flow-chat-keyboard-btn flow-canvas-keyboard-btn' +
          (isSelected(btnPath, 'button') ? ' is-selected' : '');
        chip.setAttribute('data-flow-sel', selKey({ kind: 'button', path: btnPath }));

        var label = document.createElement('span');
        label.textContent = (btn.text || '').trim() || 'دکمه جدید';
        chip.appendChild(label);
        appendButtonChipMeta(chip, btn);

        chip.addEventListener('click', function (e) {
          stopProp(e);
          toggleSelect(btnPath, 'button');
        });
        cell.appendChild(chip);

        if (btn.action && btn.action.type === 'buttons') {
          var sub = document.createElement('div');
          sub.className = 'flow-canvas-submenu';
          renderButtonsBlock(btn.action, btnPath, sub, true);
          cell.appendChild(sub);
        }

        rowEl.appendChild(cell);
      });

      kb.appendChild(rowEl);
    });

    wrap.appendChild(kb);
    parentEl.appendChild(wrap);
  }

  function renderInteractiveBlock(item, itemIndex) {
    var path = [{ kind: 'item', index: itemIndex }];
    var wrap = document.createElement('div');
    wrap.className =
      'flow-canvas-block flow-chat-row flow-chat-row--bot' +
      (isSelected(path, 'item') ? ' is-selected' : '');
    wrap.setAttribute('data-flow-sel', selKey({ kind: 'item', path: path }));

    var label = String(item.type || '');
    ACTION_OPTIONS.forEach(function (o) {
      if (o[0] === label) label = o[1];
    });
    var preview =
      item.prompt || item.title || item.message || item.label || item.code || item.channel || '';
    var bubble = document.createElement('div');
    bubble.className = 'flow-chat-bubble flow-chat-bubble--text flow-canvas-editable-bubble';
    bubble.textContent = '[' + label + ']' + (preview ? ' ' + preview : '');
    if (!preview) bubble.classList.add('is-placeholder');

    wrap.appendChild(bubble);
    decorateBlockDrag(wrap, [itemIndex], function () {
      toggleSelect(path, 'item');
    });
    return wrap;
  }

  function renderButtonItemBlock(item, itemIndex) {
    return renderButtonItemGroup([{ item: item, index: itemIndex }]);
  }

  function renderButtonItemGroup(entries) {
    if (!entries || !entries.length) return document.createElement('div');
    var firstIndex = entries[0].index;
    var rowKey = getButtonRowKey(entries[0].item, firstIndex);
    var path = [{ kind: 'item', index: firstIndex }];
    var wrap = document.createElement('div');
    wrap.className =
      'flow-canvas-block flow-canvas-button-row-block flow-chat-row flow-chat-row--bot' +
      (entries.some(function (e) {
        return isSelected([{ kind: 'item', index: e.index }], 'item');
      })
        ? ' is-selected'
        : '');
    wrap.setAttribute('data-flow-sel', selKey({ kind: 'item', path: path }));

    var kb = document.createElement('div');
    kb.className = 'flow-chat-keyboard flow-canvas-keyboard';
    var rowEl = document.createElement('div');
    rowEl.className = 'flow-canvas-button-row flow-chat-keyboard-row';

    appendChipGap(rowEl, firstIndex, rowKey);

    entries.forEach(function (entry) {
      var item = entry.item;
      var itemIndex = entry.index;
      var itemPath = [{ kind: 'item', index: itemIndex }];

      var cell = document.createElement('div');
      cell.className = 'flow-canvas-button-cell';

      var chip = document.createElement('div');
      chip.className =
        'flow-chat-keyboard-btn flow-canvas-keyboard-btn' +
        (isSelected(itemPath, 'item') ? ' is-selected' : '');
      chip.setAttribute('role', 'button');
      chip.setAttribute('tabindex', '0');
      chip.setAttribute('data-flat-button-index', String(itemIndex));
      attachDragSource(chip, { kind: 'button', index: itemIndex }, '.flow-canvas-button-cell');

      var label = document.createElement('span');
      label.className = 'flow-canvas-keyboard-btn-label';
      label.textContent = (item.text || '').trim() || 'دکمه جدید';
      chip.appendChild(label);
      appendButtonChipMeta(chip, item);

      chip.addEventListener('click', function (e) {
        stopProp(e);
        toggleSelect(itemPath, 'item');
      });
      chip.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleSelect(itemPath, 'item');
        }
      });

      cell.appendChild(chip);

      if (item.action && item.action.type === 'buttons') {
        var sub = document.createElement('div');
        sub.className = 'flow-canvas-submenu';
        renderButtonsBlock(item.action, itemPath, sub, true);
        cell.appendChild(sub);
      }

      rowEl.appendChild(cell);
      appendChipGap(rowEl, itemIndex + 1, rowKey);
    });

    kb.appendChild(rowEl);
    wrap.appendChild(kb);
    wrap.addEventListener('click', function (e) {
      if (e.target.closest('.flow-canvas-button-cell')) return;
      toggleSelect(path, 'item');
    });
    return wrap;
  }

  function renderCanvas() {
    if (!threadEl) return;
    threadEl.innerHTML = '';

    var sys = document.createElement('div');
    sys.className = 'flow-chat-system';
    sys.innerHTML = '<span>کاربر /start را ارسال کرد</span>';
    threadEl.appendChild(sys);

    if (!state.root.items.length) {
      var empty = document.createElement('div');
      empty.className = 'flow-chat-empty flow-canvas-empty';
      empty.innerHTML =
        '<i class="bi bi-chat-square-dots"></i>' +
        '<p><strong>منوی /start</strong></p>' +
        '<p class="flow-canvas-empty-hint">از تب «افزودن» آیتم بسازید · خود دکمه یا کارت را بکشید و جابه‌جا کنید</p>';
      threadEl.appendChild(empty);
    }

    appendDropZone(0);

    var i = 0;
    while (i < state.root.items.length) {
      var item = state.root.items[i];
      var t = String(item.type || '');
      if (t === 'button') {
        var rowKey = item.row !== undefined && item.row !== null ? item.row : i;
        var group = [{ item: item, index: i }];
        var j = i + 1;
        while (j < state.root.items.length) {
          var next = state.root.items[j];
          if (String(next.type || '').toLowerCase() !== 'button') break;
          var nextRow = next.row !== undefined && next.row !== null ? next.row : j;
          if (nextRow !== rowKey) break;
          group.push({ item: next, index: j });
          j += 1;
        }
        threadEl.appendChild(renderButtonItemGroup(group));
        i = j;
        appendDropZone(i);
        continue;
      }
      if (t === 'text') threadEl.appendChild(renderTextBlock(item, i));
      else if (isMediaType(t)) threadEl.appendChild(renderMediaBlock(item, i));
      else if (t === 'buttons') {
        var host = document.createElement('div');
        renderButtonsBlock(item, [{ kind: 'item', index: i }], host, false);
        threadEl.appendChild(host.firstChild);
      } else if (isInteractiveType(t)) {
        threadEl.appendChild(renderInteractiveBlock(item, i));
      }
      i += 1;
      appendDropZone(i);
    }

    syncHidden();
    updateItemCountLabel();
    renderFlowOutline();
  }

  function addFieldLabel(text) {
    var lbl = document.createElement('label');
    lbl.className = 'form-label small mb-1';
    lbl.textContent = text;
    return lbl;
  }

  function addTextarea(value, placeholder, maxLen, onInput) {
    var ta = document.createElement('textarea');
    ta.className = 'form-control panel-input';
    ta.rows = 3;
    ta.placeholder = placeholder || '';
    ta.maxLength = maxLen || 4096;
    ta.value = value || '';
    ta.addEventListener('input', function () {
      onInput(ta.value);
    });
    return ta;
  }

  function addInput(value, placeholder, maxLen, onInput, type) {
    var inp = document.createElement('input');
    inp.type = type || 'text';
    inp.className = 'form-control panel-input';
    inp.placeholder = placeholder || '';
    if (maxLen) inp.maxLength = maxLen;
    inp.value = value || '';
    inp.addEventListener('input', function () {
      onInput(inp.value);
    });
    return inp;
  }

  function addSelect(value, options, onChange) {
    var sel = document.createElement('select');
    sel.className = 'form-select panel-input';
    options.forEach(function (o) {
      var opt = document.createElement('option');
      opt.value = o[0];
      opt.textContent = o[1];
      sel.appendChild(opt);
    });
    sel.value = value || '';
    sel.addEventListener('change', function () {
      onChange(sel.value);
    });
    return sel;
  }

  function appendMediaInspector(container, mediaType, getItem, setItem) {
    var fileInp = document.createElement('input');
    fileInp.type = 'file';
    fileInp.accept = MEDIA_ACCEPT[mediaType] || '*/*';
    fileInp.className = 'form-control panel-input';

    var status = document.createElement('div');
    status.className = 'small text-muted mt-1 mb-2';

    function refreshStatus() {
      var item = getItem();
      status.textContent =
        item && item.media_id
          ? 'آپلود شده · ' + item.media_id.slice(0, 8) + '…'
          : 'فایلی انتخاب نشده';
    }
    refreshStatus();

    fileInp.addEventListener('change', function () {
      var f = fileInp.files && fileInp.files[0];
      if (!f) return;
      status.textContent = 'در حال آپلود…';
      uploadMedia(
        f,
        function (j) {
          var item = getItem() || defaultMediaItem(mediaType);
          item.type = mediaType;
          item.media_id = j.media_id;
          if (item.caption === undefined) item.caption = '';
          setItem(item);
          refreshStatus();
          renderCanvas();
        },
        function (err) {
          status.textContent = err;
        }
      );
    });

    container.appendChild(fileInp);
    container.appendChild(status);
    container.appendChild(addFieldLabel('کپشن (اختیاری)'));
    container.appendChild(
      addTextarea((getItem() && getItem().caption) || '', 'توضیح زیر رسانه', 1024, function (v) {
        var item = getItem() || defaultMediaItem(mediaType);
        item.caption = v;
        setItem(item);
        renderCanvas();
      })
    );
  }

  function renderMiniSequenceInspector(seq, onChange) {
    var box = document.createElement('div');
    box.className = 'flow-inspector-mini-seq';

    if (!seq.items) seq.items = [];

    var list = document.createElement('div');
    list.className = 'flow-inspector-mini-seq-list';

    function renderList() {
      list.innerHTML = '';
      seq.items.forEach(function (item, idx) {
        var card = document.createElement('div');
        card.className = 'flow-inspector-mini-seq-item';

        var head = document.createElement('div');
        head.className = 'd-flex justify-content-between align-items-center mb-2';
        var t = String(item.type || '');
        head.innerHTML = '<span class="small fw-semibold">' + (t === 'text' ? 'متن' : MEDIA_LABELS[t] || t) + '</span>';
        var rm = document.createElement('button');
        rm.type = 'button';
        rm.className = 'btn btn-panel-ghost btn-sm text-danger';
        rm.innerHTML = '<i class="bi bi-trash"></i>';
        rm.addEventListener('click', function () {
          seq.items.splice(idx, 1);
          renderList();
          onChange();
        });
        head.appendChild(rm);
        card.appendChild(head);

        if (t === 'text') {
          card.appendChild(
            addTextarea(item.body || '', 'متن پیام', 4096, function (v) {
              item.body = v;
              onChange();
            })
          );
        } else if (isMediaType(t)) {
          appendMediaInspector(
            card,
            t,
            function () {
              return item;
            },
            function (next) {
              seq.items[idx] = next;
            }
          );
        }
        list.appendChild(card);
      });
    }

    var toolbar = document.createElement('div');
    toolbar.className = 'd-flex flex-wrap gap-2 mb-2';
    [
      ['text', 'متن'],
      ['image', 'عکس'],
      ['video', 'ویدیو'],
    ].forEach(function (pair) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn btn-panel-ghost btn-sm';
      b.textContent = '+ ' + pair[1];
      b.addEventListener('click', function () {
        if (pair[0] === 'text') seq.items.push({ type: 'text', body: '' });
        else seq.items.push(defaultMediaItem(pair[0]));
        renderList();
        onChange();
      });
      toolbar.appendChild(b);
    });

    box.appendChild(toolbar);
    box.appendChild(list);
    renderList();
    return box;
  }

  function findDiscountCode(id) {
    var pk = parseInt(id, 10);
    if (isNaN(pk)) return null;
    for (var i = 0; i < discountCodes.length; i += 1) {
      if (discountCodes[i].id === pk) return discountCodes[i];
    }
    return null;
  }

  function applyCouponSelection(action, discountId) {
    var dc = findDiscountCode(discountId);
    if (!dc) {
      action.discount_id = null;
      action.code = '';
      return;
    }
    action.discount_id = dc.id;
    action.code = dc.code;
  }

  function appendCouponPicker(container, action, onChange) {
    container.appendChild(addFieldLabel('کد تخفیف مینی‌اپ'));
    if (!discountCodes.length) {
      var empty = document.createElement('p');
      empty.className = 'small text-muted';
      empty.textContent = 'ابتدا از بخش مینی‌اپ یک کد تخفیف بسازید.';
      container.appendChild(empty);
      return;
    }
    var options = [['', '— انتخاب کنید —']];
    discountCodes.forEach(function (dc) {
      options.push([String(dc.id), dc.label || dc.code]);
    });
    var selVal = action.discount_id != null ? String(action.discount_id) : '';
    if (!selVal && action.code) {
      discountCodes.forEach(function (dc) {
        if (String(dc.code || '').toUpperCase() === String(action.code || '').toUpperCase()) {
          selVal = String(dc.id);
          action.discount_id = dc.id;
        }
      });
    }
    container.appendChild(
      addSelect(selVal, options, function (v) {
        if (v) applyCouponSelection(action, v);
        else {
          action.discount_id = null;
          action.code = '';
        }
        onChange();
      })
    );
    if (action.code) {
      var preview = document.createElement('div');
      preview.className = 'small text-muted mt-1 mb-2';
      preview.textContent = 'کد انتخاب‌شده: ' + action.code;
      container.appendChild(preview);
    }
    container.appendChild(addFieldLabel('پیام (اختیاری)'));
    container.appendChild(
      addTextarea(action.message || '', 'اگر خالی باشد، متن پیش‌فرض ارسال می‌شود', 500, function (v) {
        action.message = v;
        onChange();
      })
    );
  }

  function renderInteractiveFields(action, container, onChange) {
    if (!action || !isInteractiveType(action.type)) return;
    var t = action.type;

    function field(label, value, placeholder, maxLen, cb, inputType) {
      container.appendChild(addFieldLabel(label));
      container.appendChild(addInput(value, placeholder, maxLen, cb, inputType));
    }

    if (t === 'webapp') {
      if (!action.target) action.target = { kind: 'home', value: '' };
      field('متن دکمه', action.label, 'ورود به فروشگاه', 64, function (v) {
        action.label = v;
        onChange();
      });
      container.appendChild(addFieldLabel('مقصد'));
      container.appendChild(
        addSelect(action.target.kind || 'home', [
          ['home', 'صفحه اصلی'],
          ['category', 'دسته'],
          ['item', 'محصول'],
        ], function (v) {
          action.target.kind = v;
          onChange();
        })
      );
      if (action.target.kind !== 'home') {
        field('شناسه (slug)', action.target.value, '', 120, function (v) {
          action.target.value = v;
          onChange();
        });
      }
      return;
    }

    if (t === 'order_status' || t === 'handoff' || t === 'request_contact' || t === 'request_location') {
      field('پیام', action.prompt || action.message, '', 500, function (v) {
        if (t === 'handoff') action.message = v;
        else action.prompt = v;
        onChange();
      });
      if (t === 'request_contact') {
        field('برچسب پس از ثبت (slug)', action.assign_tag || '', '', 140, function (v) {
          action.assign_tag = v;
          onChange();
        });
      }
      if (t === 'request_location') {
        field('کلید ذخیره', action.save_key || 'loc', 'loc', 64, function (v) {
          action.save_key = v;
          onChange();
        });
      }
      return;
    }

    if (t === 'my_orders') {
      field('تعداد نمایش', String(action.limit || 5), '5', 2, function (v) {
        action.limit = parseInt(v, 10) || 5;
        onChange();
      });
      return;
    }

    if (t === 'invoice') {
      field('عنوان', action.title, 'پرداخت', 32, function (v) {
        action.title = v;
        onChange();
      });
      field('مبلغ (ریال)', String(action.amount || 0), '0', 12, function (v) {
        action.amount = parseInt(v, 10) || 0;
        onChange();
      }, 'number');
      field('توضیح', action.description, '', 255, function (v) {
        action.description = v;
        onChange();
      });
      field('slug محصول (اختیاری)', action.item_slug, '', 120, function (v) {
        action.item_slug = v;
        onChange();
      });
      return;
    }

    if (t === 'location_card') {
      field('عرض جغرافیایی', String(action.lat || ''), '', 20, function (v) {
        action.lat = parseFloat(v) || 0;
        onChange();
      });
      field('طول جغرافیایی', String(action.lng || ''), '', 20, function (v) {
        action.lng = parseFloat(v) || 0;
        onChange();
      });
      field('آدرس', action.address, '', 500, function (v) {
        action.address = v;
        onChange();
      });
      field('ساعت کاری', action.hours, '', 200, function (v) {
        action.hours = v;
        onChange();
      });
      return;
    }

    if (t === 'contact_card') {
      field('شماره', action.phone, '021…', 20, function (v) {
        action.phone = v;
        onChange();
      });
      field('نام', action.name, 'پشتیبانی', 64, function (v) {
        action.name = v;
        onChange();
      });
      return;
    }

    if (t === 'input') {
      field('سوال', action.prompt, '', 500, function (v) {
        action.prompt = v;
        onChange();
      });
      field('کلید ذخیره', action.save_key, 'size', 64, function (v) {
        action.save_key = v;
        onChange();
      });
      container.appendChild(addFieldLabel('اعتبارسنجی'));
      container.appendChild(
        addSelect(action.validate || 'text', [
          ['text', 'متن'],
          ['number', 'عدد'],
          ['phone', 'شماره'],
        ], function (v) {
          action.validate = v;
          onChange();
        })
      );
      if (!action.next) action.next = { type: 'text', body: '' };
      container.appendChild(addFieldLabel('پیام بعد از ثبت'));
      container.appendChild(
        addTextarea((action.next && action.next.body) || '', 'ممنون!', 500, function (v) {
          action.next = { type: 'text', body: v };
          onChange();
        })
      );
      return;
    }

    if (t === 'form') {
      if (!action.steps) action.steps = [];
      if (!action.on_complete) action.on_complete = { notify_admin: true, thank_you: 'ثبت شد.', assign_tag: '' };
      field('عنوان فرم', action.title, '', 120, function (v) {
        action.title = v;
        onChange();
      });
      var stepsBox = document.createElement('div');
      stepsBox.className = 'flow-inspector-form-steps';
      function renderSteps() {
        stepsBox.innerHTML = '';
        action.steps.forEach(function (step, si) {
          var card = document.createElement('div');
          card.className = 'border rounded p-2 mb-2';
          card.appendChild(addFieldLabel('مرحله ' + (si + 1)));
          card.appendChild(
            addInput(step.prompt || '', 'سوال', 500, function (v) {
              step.prompt = v;
              onChange();
            })
          );
          card.appendChild(
            addInput(step.save_key || '', 'کلید (name, phone…)', 64, function (v) {
              step.save_key = v;
              onChange();
            })
          );
          card.appendChild(
            addSelect(step.validate || 'text', [
              ['text', 'متن'],
              ['number', 'عدد'],
              ['phone', 'شماره'],
            ], function (v) {
              step.validate = v;
              onChange();
            })
          );
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف مرحله';
          rm.addEventListener('click', function () {
            action.steps.splice(si, 1);
            renderSteps();
            onChange();
          });
          card.appendChild(rm);
          stepsBox.appendChild(card);
        });
      }
      renderSteps();
      container.appendChild(addFieldLabel('مراحل فرم'));
      container.appendChild(stepsBox);
      var addStep = document.createElement('button');
      addStep.type = 'button';
      addStep.className = 'btn btn-panel-ghost btn-sm mb-2';
      addStep.textContent = '+ مرحله';
      addStep.addEventListener('click', function () {
        action.steps.push({ prompt: '', save_key: 'field_' + (action.steps.length + 1), validate: 'text' });
        renderSteps();
        onChange();
      });
      container.appendChild(addStep);
      var notifyWrap = document.createElement('label');
      notifyWrap.className = 'd-flex align-items-center gap-2 mb-2';
      var notifyChk = document.createElement('input');
      notifyChk.type = 'checkbox';
      notifyChk.checked = !!action.on_complete.notify_admin;
      notifyChk.addEventListener('change', function () {
        action.on_complete.notify_admin = notifyChk.checked;
        onChange();
      });
      notifyWrap.appendChild(notifyChk);
      notifyWrap.appendChild(document.createTextNode(' اعلان به ادمین'));
      container.appendChild(notifyWrap);
      field('پیام تشکر', action.on_complete.thank_you, '', 500, function (v) {
        action.on_complete.thank_you = v;
        onChange();
      });
      field('برچسب پس از ثبت', action.on_complete.assign_tag, '', 140, function (v) {
        action.on_complete.assign_tag = v;
        onChange();
      });
      return;
    }

    if (t === 'join_gate') {
      field('کانال (@username)', action.channel, '@channel', 120, function (v) {
        action.channel = v;
        onChange();
      });
      field('پیام', action.prompt, '', 500, function (v) {
        action.prompt = v;
        onChange();
      });
      return;
    }

    if (t === 'goto') {
      field('شناسه نود هدف', action.target_id, 'n_xxxxxxxx', 16, function (v) {
        action.target_id = v;
        onChange();
      });
      return;
    }

    if (t === 'tag') {
      field('افزودن برچسب (با کاما)', (action.add || []).join(', '), 'vip, lead', 300, function (v) {
        action.add = v.split(/[,،]/).map(function (s) {
          return s.trim();
        }).filter(Boolean);
        onChange();
      });
      field('حذف برچسب', (action.remove || []).join(', '), '', 300, function (v) {
        action.remove = v.split(/[,،]/).map(function (s) {
          return s.trim();
        }).filter(Boolean);
        onChange();
      });
      return;
    }

    if (t === 'coupon') {
      appendCouponPicker(container, action, onChange);
      return;
    }

    if (t === 'faq') {
      if (!action.items) action.items = [];
      field('عنوان', action.title, 'سوالات متداول', 120, function (v) {
        action.title = v;
        onChange();
      });
      var faqList = document.createElement('div');
      function renderFaq() {
        faqList.innerHTML = '';
        action.items.forEach(function (item, fi) {
          var card = document.createElement('div');
          card.className = 'border rounded p-2 mb-2';
          card.appendChild(addFieldLabel('سوال ' + (fi + 1)));
          card.appendChild(
            addInput(item.q || '', 'سوال', 200, function (v) {
              item.q = v;
              onChange();
            })
          );
          card.appendChild(
            addTextarea(item.a || '', 'پاسخ', 2000, function (v) {
              item.a = v;
              onChange();
            })
          );
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف';
          rm.addEventListener('click', function () {
            action.items.splice(fi, 1);
            renderFaq();
            onChange();
          });
          card.appendChild(rm);
          faqList.appendChild(card);
        });
      }
      renderFaq();
      container.appendChild(faqList);
      var addFaq = document.createElement('button');
      addFaq.type = 'button';
      addFaq.className = 'btn btn-panel-ghost btn-sm';
      addFaq.textContent = '+ سوال';
      addFaq.addEventListener('click', function () {
        action.items.push({ q: '', a: '' });
        renderFaq();
        onChange();
      });
      container.appendChild(addFaq);
      return;
    }

    if (t === 'condition') {
      if (!action.if) action.if = { kind: 'has_tag', value: '' };
      container.appendChild(addFieldLabel('شرط'));
      container.appendChild(
        addSelect(action.if.kind || 'has_tag', [
          ['has_tag', 'دارای برچسب'],
          ['is_registered', 'ثبت‌نام‌شده'],
          ['answer_equals', 'پاسخ برابر'],
        ], function (v) {
          action.if.kind = v;
          onChange();
        })
      );
      if (action.if.kind === 'has_tag') {
        field('برچسب', action.if.value, 'vip', 140, function (v) {
          action.if.value = v;
          onChange();
        });
      } else if (action.if.kind === 'answer_equals') {
        field('کلید', action.if.key, '', 64, function (v) {
          action.if.key = v;
          onChange();
        });
        field('مقدار', action.if.value, '', 500, function (v) {
          action.if.value = v;
          onChange();
        });
      }
      if (!action.then) action.then = { type: 'text', body: '' };
      if (!action.else) action.else = { type: 'text', body: '' };
      container.appendChild(addFieldLabel('اگر درست بود'));
      container.appendChild(
        addTextarea((action.then.body) || '', 'متن', 500, function (v) {
          action.then = { type: 'text', body: v };
          onChange();
        })
      );
      container.appendChild(addFieldLabel('وگرنه'));
      container.appendChild(
        addTextarea((action.else.body) || '', 'متن', 500, function (v) {
          action.else = { type: 'text', body: v };
          onChange();
        })
      );
    }
  }

  function renderActionInspector(btn, onChange) {
    var box = document.createElement('div');
    box.className = 'flow-inspector-action';

    box.appendChild(addFieldLabel('نوع اکشن'));
    var actionType = (btn.action && btn.action.type) || '';
    box.appendChild(
      addSelect(actionType, ACTION_OPTIONS, function (t) {
        if (!t) btn.action = null;
        else if (t === 'text') btn.action = { type: 'text', body: '' };
        else if (t === 'url') btn.action = { type: 'url', url: miniAppUrl || '' };
        else if (t === 'image') btn.action = { type: 'image', media_id: '', caption: '' };
        else if (t === 'sequence') btn.action = { type: 'sequence', items: [] };
        else if (t === 'buttons') btn.action = { type: 'buttons', rows: [[defaultButton()]] };
        else if (isInteractiveType(t)) btn.action = defaultInteractiveAction(t);
        onChange();
        renderInspector();
      })
    );

    var extras = document.createElement('div');
    extras.className = 'mt-2';

    if (btn.action && btn.action.type === 'text') {
      extras.appendChild(addFieldLabel('متن پس از کلیک'));
      extras.appendChild(
        addTextarea(btn.action.body || '', 'متن پیام', 4096, function (v) {
          btn.action.body = v;
          onChange();
        })
      );
    } else if (btn.action && btn.action.type === 'url') {
      extras.appendChild(addFieldLabel('آدرس URL'));
      if (miniAppUrl) {
        var quick = document.createElement('button');
        quick.type = 'button';
        quick.className = 'btn btn-panel-ghost btn-sm mb-2';
        quick.textContent = 'استفاده از لینک مینی‌اپ';
        quick.addEventListener('click', function () {
          btn.action.url = miniAppUrl;
          onChange();
          renderInspector();
        });
        extras.appendChild(quick);
      }
      extras.appendChild(
        addInput(btn.action.url || '', 'https://...', 512, function (v) {
          btn.action.url = v;
          onChange();
        }, 'url')
      );
    } else if (btn.action && btn.action.type === 'image') {
      appendMediaInspector(
        extras,
        'image',
        function () {
          return btn.action;
        },
        function (act) {
          btn.action = act;
        }
      );
    } else if (btn.action && btn.action.type === 'sequence') {
      extras.appendChild(
        renderMiniSequenceInspector(btn.action, function () {
          onChange();
          renderCanvas();
        })
      );
    } else if (btn.action && btn.action.type === 'buttons') {
      extras.appendChild(
        addFieldLabel('زیرمنو روی canvas نمایش داده می‌شود. «+ دکمه زیرمنو» یا افزودن از نوار ابزار.')
      );
    } else if (btn.action && isInteractiveType(btn.action.type)) {
      renderInteractiveFields(btn.action, extras, onChange);
    }

    box.appendChild(extras);
    return box;
  }

  function mkDeselectBtn() {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn btn-panel-ghost btn-sm flow-inspector-deselect mb-3';
    b.innerHTML = '<i class="bi bi-x-lg"></i> لغو انتخاب';
    b.addEventListener('click', clearSelection);
    return b;
  }

  function renderInspector() {
    if (!inspectorBody) return;
    inspectorBody.innerHTML = '';

    if (!selection) {
      if (inspectorTitle) inspectorTitle.textContent = 'ویژگی‌ها';
      if (inspectorHint) inspectorHint.textContent = 'یک آیتم را انتخاب کنید';
      inspectorBody.innerHTML =
        '<div class="bot-inspector-idle">' +
        '<div class="bot-inspector-idle-icon"><i class="bi bi-cursor"></i></div>' +
        '<p class="bot-inspector-idle-title">چیزی انتخاب نشده</p>' +
        '<p class="bot-inspector-idle-text">روی پیام یا دکمه کلیک کنید · برای جابجایی، نوار کنار آیتم را بکشید · حذف و بالا/پایین از همین پنل</p>' +
        '</div>';
      return;
    }

    var ref = resolveAtPath(selection.path);
    if (!ref) {
      clearSelection();
      return;
    }

    function bump() {
      syncHidden();
      renderCanvas();
    }

    inspectorBody.appendChild(mkDeselectBtn());
    if (inspectorHint) {
      inspectorHint.textContent = 'برای لغو: دوباره کلیک · فضای خالی · Escape';
    }

    if (selection.kind === 'item') {
      var item = ref.item;
      var t = String(item.type || '');
      if (inspectorTitle) {
        inspectorTitle.textContent =
          t === 'text' ? 'پیام متنی' : t === 'button' ? 'دکمه منو' : t === 'buttons' ? 'زیرمنو' : MEDIA_LABELS[t] || 'آیتم';
      }
      if (inspectorHint) inspectorHint.textContent = 'آیتم ' + (ref.itemIndex + 1);

      if (t === 'text') {
        inspectorBody.appendChild(addFieldLabel('متن پیام'));
        inspectorBody.appendChild(
          addTextarea(item.body || '', 'متن ارسالی به کاربر', 4096, function (v) {
            item.body = v;
            bump();
          })
        );
      } else if (isMediaType(t)) {
        appendMediaInspector(
          inspectorBody,
          t,
          function () {
            return item;
          },
          function (next) {
            state.root.items[ref.itemIndex] = next;
            bump();
          }
        );
      } else if (t === 'button') {
        var btnItem = item;
        inspectorBody.appendChild(addFieldLabel('متن روی دکمه'));
        inspectorBody.appendChild(
          addInput(btnItem.text || '', 'مثلاً مشاهده ویترین', 64, function (v) {
            btnItem.text = v;
            if (buttonHasCategory(btnItem)) {
              ensureButtonCategorySlug(btnItem);
            }
            bump();
          })
        );

        var catWrap = document.createElement('div');
        catWrap.className = 'flow-inspector-category mt-3';
        var catToggle = document.createElement('label');
        catToggle.className = 'flow-inspector-category-toggle';
        var catCheck = document.createElement('input');
        catCheck.type = 'checkbox';
        catCheck.className = 'form-check-input';
        catCheck.checked = buttonHasCategory(btnItem);
        var catText = document.createElement('span');
        catText.innerHTML =
          '<strong>استفاده به‌عنوان دسته‌بندی</strong><small class="d-block text-muted mt-1">با کلیک کاربر روی این دکمه، در این دسته‌بندی قرار می‌گیرد.</small>';
        catToggle.appendChild(catCheck);
        catToggle.appendChild(catText);
        catWrap.appendChild(catToggle);

        var slugWrap = document.createElement('div');
        slugWrap.className = 'mt-2';
        slugWrap.style.display = catCheck.checked ? '' : 'none';
        slugWrap.appendChild(addFieldLabel('شناسه دسته‌بندی (اختیاری)'));
        slugWrap.appendChild(
          addInput(btnItem.category_slug || '', 'خودکار از متن دکمه', 140, function (v) {
            btnItem.category_slug = String(v || '').trim();
            bump();
          })
        );
        catCheck.addEventListener('change', function () {
          if (catCheck.checked) {
            ensureButtonCategorySlug(btnItem);
          } else {
            btnItem.category_slug = '';
          }
          slugWrap.style.display = catCheck.checked ? '' : 'none';
          bump();
        });
        catWrap.appendChild(slugWrap);
        inspectorBody.appendChild(catWrap);
        inspectorBody.appendChild(renderActionInspector(btnItem, bump));

        var subTools = document.createElement('div');
        subTools.className = 'flow-inspector-btn-tools mt-3 pt-3 border-top';
        var addSub = document.createElement('button');
        addSub.type = 'button';
        addSub.className = 'btn btn-panel-primary btn-sm';
        addSub.textContent = '+ زیرمنو';
        addSub.addEventListener('click', function () {
          btnItem.action = { type: 'buttons', rows: [[defaultButton()]] };
          bump();
        });
        subTools.appendChild(addSub);
        inspectorBody.appendChild(subTools);

        var rowTools = document.createElement('div');
        rowTools.className = 'd-flex flex-wrap gap-2 mt-2';
        var addSiblingBtn = document.createElement('button');
        addSiblingBtn.type = 'button';
        addSiblingBtn.className = 'btn btn-panel-ghost btn-sm';
        addSiblingBtn.textContent = '+ کنار این دکمه';
        addSiblingBtn.addEventListener('click', function () {
          var rowVal =
            btnItem.row !== undefined && btnItem.row !== null ? btnItem.row : ref.itemIndex;
          var newBtn = newContentNode('button');
          newBtn.row = rowVal;
          var insertAt = ref.itemIndex + 1;
          state.root.items.splice(insertAt, 0, newBtn);
          selectPath([{ kind: 'item', index: insertAt }], 'item');
          bump();
        });
        var addRowBtn = document.createElement('button');
        addRowBtn.type = 'button';
        addRowBtn.className = 'btn btn-panel-ghost btn-sm';
        addRowBtn.textContent = '+ ردیف جدید';
        addRowBtn.addEventListener('click', function () {
          var rowKey = getButtonRowKey(btnItem, ref.itemIndex);
          var insertAt = ref.itemIndex + 1;
          while (insertAt < state.root.items.length) {
            var next = state.root.items[insertAt];
            if (String(next.type || '').toLowerCase() !== 'button') break;
            if (getButtonRowKey(next, insertAt) !== rowKey) break;
            insertAt += 1;
          }
          var newBtn = newContentNode('button');
          newBtn.row = 9999;
          state.root.items.splice(insertAt, 0, newBtn);
          compactButtonRows();
          selectPath([{ kind: 'item', index: insertAt }], 'item');
          bump();
        });
        rowTools.appendChild(addSiblingBtn);
        rowTools.appendChild(addRowBtn);
        inspectorBody.appendChild(rowTools);
      } else if (t === 'buttons') {
        inspectorBody.appendChild(addFieldLabel('مدیریت ردیف‌ها'));
        var hint = document.createElement('p');
        hint.className = 'small text-muted';
        hint.textContent = 'دکمه‌ها را روی canvas انتخاب کنید یا ردیف جدید اضافه کنید.';
        inspectorBody.appendChild(hint);

        var rowTools = document.createElement('div');
        rowTools.className = 'd-flex flex-wrap gap-2 mb-3';
        var addRow = document.createElement('button');
        addRow.type = 'button';
        addRow.className = 'btn btn-panel-primary btn-sm';
        addRow.textContent = '+ ردیف دکمه';
        addRow.addEventListener('click', function () {
          item.rows.push([defaultButton()]);
          bump();
        });
        rowTools.appendChild(addRow);
        inspectorBody.appendChild(rowTools);
      } else if (isInteractiveType(t)) {
        var interactiveLabel = t;
        ACTION_OPTIONS.forEach(function (o) {
          if (o[0] === t) interactiveLabel = o[1];
        });
        if (inspectorTitle) inspectorTitle.textContent = interactiveLabel;
        renderInteractiveFields(item, inspectorBody, bump);
      }
      appendInspectorItemActions(inspectorBody, ref.itemIndex);
      return;
    }

    if (selection.kind === 'button') {
      var btn = ref.button;
      if (inspectorTitle) inspectorTitle.textContent = 'دکمه';
      if (inspectorHint) inspectorHint.textContent = (btn.text || '').trim() || 'بدون عنوان';

      inspectorBody.appendChild(addFieldLabel('متن روی دکمه'));
      inspectorBody.appendChild(
        addInput(btn.text || '', 'مثلاً مشاهده ویترین', 64, function (v) {
          btn.text = v;
          if (buttonHasCategory(btn)) {
            ensureButtonCategorySlug(btn);
          }
          bump();
        })
      );

      var categoryWrap = document.createElement('div');
      categoryWrap.className = 'flow-inspector-category mt-3';

      var categoryToggle = document.createElement('label');
      categoryToggle.className = 'flow-inspector-category-toggle';

      var categoryCheck = document.createElement('input');
      categoryCheck.type = 'checkbox';
      categoryCheck.className = 'form-check-input';
      categoryCheck.checked = buttonHasCategory(btn);

      var categoryText = document.createElement('span');
      categoryText.innerHTML =
        '<strong>استفاده به‌عنوان دسته‌بندی</strong><small class="d-block text-muted mt-1">با کلیک کاربر روی این دکمه، در این دسته‌بندی قرار می‌گیرد.</small>';

      categoryToggle.appendChild(categoryCheck);
      categoryToggle.appendChild(categoryText);
      categoryWrap.appendChild(categoryToggle);

      var slugFieldWrap = document.createElement('div');
      slugFieldWrap.className = 'mt-2';
      slugFieldWrap.style.display = categoryCheck.checked ? '' : 'none';

      slugFieldWrap.appendChild(addFieldLabel('شناسه دسته‌بندی (اختیاری)'));
      slugFieldWrap.appendChild(
        addInput(btn.category_slug || '', 'خودکار از متن دکمه', 140, function (v) {
          btn.category_slug = String(v || '').trim();
          bump();
        })
      );

      categoryCheck.addEventListener('change', function () {
        if (categoryCheck.checked) {
          ensureButtonCategorySlug(btn);
        } else {
          btn.category_slug = '';
        }
        slugFieldWrap.style.display = categoryCheck.checked ? '' : 'none';
        if (categoryCheck.checked) {
          var slugInput = slugFieldWrap.querySelector('input');
          if (slugInput) slugInput.value = btn.category_slug || '';
        }
        bump();
      });

      categoryWrap.appendChild(slugFieldWrap);
      inspectorBody.appendChild(categoryWrap);

      inspectorBody.appendChild(renderActionInspector(btn, bump));

      var btnTools = document.createElement('div');
      btnTools.className = 'flow-inspector-btn-tools mt-3 pt-3 border-top';

      var addSubBtn = document.createElement('button');
      addSubBtn.type = 'button';
      addSubBtn.className = 'btn btn-panel-primary btn-sm';
      addSubBtn.textContent = '+ دکمه زیرمنو';
      addSubBtn.addEventListener('click', function () {
        var loc = addButtonToSubmenu(btn, false);
        var newPath = selection.path.concat([
          { kind: 'btn', row: loc.row, btn: loc.btn },
        ]);
        selectPath(newPath, 'button');
      });

      var addSiblingBtn = document.createElement('button');
      addSiblingBtn.type = 'button';
      addSiblingBtn.className = 'btn btn-panel-ghost btn-sm ms-1';
      addSiblingBtn.textContent = '+ هم‌ردیف';
      addSiblingBtn.title = 'دکمه کنار «' + ((btn.text || '').trim() || 'این دکمه') + '» در همان ردیف';
      addSiblingBtn.addEventListener('click', function () {
        ref.buttons.rows[ref.rowIndex].push(defaultButton());
        bump();
      });

      var rmBtn = document.createElement('button');
      rmBtn.type = 'button';
      rmBtn.className = 'btn btn-panel-ghost btn-sm text-danger ms-1';
      rmBtn.textContent = 'حذف دکمه';
      rmBtn.addEventListener('click', function () {
        ref.buttons.rows[ref.rowIndex].splice(ref.btnIndex, 1);
        if (!ref.buttons.rows[ref.rowIndex].length) {
          ref.buttons.rows.splice(ref.rowIndex, 1);
        }
        if (!ref.buttons.rows.length) ref.buttons.rows = [[defaultButton()]];
        clearSelection();
      });

      btnTools.appendChild(addSubBtn);
      btnTools.appendChild(addSiblingBtn);
      btnTools.appendChild(rmBtn);

      if (isTopLevelButtonSelection(selection.path)) {
        var moveWrap = document.createElement('div');
        moveWrap.className = 'd-flex flex-wrap gap-2 mt-2';

        var extractBtn = document.createElement('button');
        extractBtn.type = 'button';
        extractBtn.className = 'btn btn-panel-ghost btn-sm';
        extractBtn.textContent = 'استخراج به بلوک منوی جدید';
        extractBtn.addEventListener('click', function () {
          if (extractButtonToNewBlock(ref, selection.path)) bump();
        });
        moveWrap.appendChild(extractBtn);

        var actionType = (btn.action && btn.action.type) || '';
        if (isInteractiveType(actionType) && actionType !== 'buttons') {
          var standaloneBtn = document.createElement('button');
          standaloneBtn.type = 'button';
          standaloneBtn.className = 'btn btn-panel-ghost btn-sm';
          standaloneBtn.textContent = 'تبدیل به بلوک مستقل';
          standaloneBtn.addEventListener('click', function () {
            if (convertButtonToStandaloneBlock(ref, selection.path)) bump();
          });
          moveWrap.appendChild(standaloneBtn);
        }

        var otherBlocks = listTopLevelButtonsBlocks(ref.itemIndex);
        if (otherBlocks.length) {
          var moveSelect = document.createElement('select');
          moveSelect.className = 'form-select form-select-sm panel-input';
          moveSelect.style.maxWidth = '220px';
          var opt0 = document.createElement('option');
          opt0.value = '';
          opt0.textContent = 'انتقال به بلوک منو…';
          moveSelect.appendChild(opt0);
          otherBlocks.forEach(function (b) {
            var opt = document.createElement('option');
            opt.value = String(b.index);
            opt.textContent = b.label;
            moveSelect.appendChild(opt);
          });
          moveSelect.addEventListener('change', function () {
            var idx = parseInt(moveSelect.value, 10);
            if (!idx && idx !== 0) return;
            if (moveButtonToBlock(ref, selection.path, idx)) bump();
            moveSelect.value = '';
          });
          moveWrap.appendChild(moveSelect);
        }

        btnTools.appendChild(moveWrap);
      }

      inspectorBody.appendChild(btnTools);
    }
  }

  function addItem(type) {
    if (selection && selection.kind === 'button') {
      var ref = resolveAtPath(selection.path);
      if (ref && ref.button) {
        if (type === 'buttons') {
          var loc = addButtonToSubmenu(ref.button, false);
          var newPath = selection.path.concat([
            { kind: 'btn', row: loc.row, btn: loc.btn },
          ]);
          renderCanvas();
          selectPath(newPath, 'button');
          syncHidden();
          return;
        }
        if (appendToButtonAction(ref.button, type)) {
          renderCanvas();
          renderInspector();
          syncHidden();
          return;
        }
      }
    }

    var node = newContentNode(type);
    if (!node) return;

    var insertAt = state.root.items.length;
    if (selection && selection.kind === 'item' && selection.path.length) {
      insertAt = selection.path[0].index + 1;
    }

    state.root.items.splice(insertAt, 0, node);
    selectPath([{ kind: 'item', index: insertAt }], 'item');
    if (mobileApi) mobileApi.onItemAdded();
  }

  function mount(root) {
    hiddenId = root.getAttribute('data-hidden-id') || 'id_start_flow';
    uploadUrl = root.getAttribute('data-upload-url') || '';
    miniAppUrl = root.getAttribute('data-mini-app-url') || '';
    hasMiniApp = root.getAttribute('data-has-miniapp') === '1';
    editorRootEl = root;
    mobileApi = window.FlowCanvasMobile ? FlowCanvasMobile.mount(root) : null;
    threadEl = $('flow-canvas-thread');
    paletteEl = $('flow-block-palette');
    outlineEl = $('flow-blocks-outline');
    itemCountEl = $('flow-editor-item-count');
    paletteHintEl = $('flow-palette-hint');
    toolbarTargetEl = $('flow-canvas-toolbar-target');
    paletteFiltersEl = $('flow-palette-filters');
    quickAddEl = $('flow-quick-add');
    paletteSearchEl = $('flow-palette-search');
    dockTabsEl = document.querySelector('.bot-studio-tabs');
    inspectorBody = $('flow-inspector-body');
    inspectorTitle = $('flow-inspector-title');
    inspectorHint = $('flow-inspector-hint');

    try {
      discountCodes = JSON.parse(root.getAttribute('data-discount-codes') || '[]');
    } catch (discountErr) {
      discountCodes = [];
    }

    state = parseHidden();

    renderQuickAdd();
    renderPaletteFilters();
    renderBlockPalette();

    if (dockTabsEl) {
      dockTabsEl.querySelectorAll('.bot-studio-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
          switchDockTab(tab.getAttribute('data-dock-tab'));
        });
      });
    }

    if (paletteSearchEl) {
      paletteSearchEl.addEventListener('input', function () {
        paletteSearch = paletteSearchEl.value || '';
        renderBlockPalette();
      });
    }

    if (threadEl) {
      threadEl.addEventListener('click', function (e) {
        if (e.target.closest('.flow-canvas-block')) return;
        if (e.target.closest('.flow-canvas-block-actions')) return;
        clearSelection();
      });
      setupCanvasDragDrop();
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && selection) clearSelection();
    });

    renderCanvas();
    renderInspector();
    updateToolbarContext();
    if (mobileApi) mobileApi.suggestAddIfEmpty(state.root.items.length);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('flow-canvas-editor');
    if (root) mount(root);
  });
})();
