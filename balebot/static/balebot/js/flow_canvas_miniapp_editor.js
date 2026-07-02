(function () {
  'use strict';

  var RIAL_PER_TOMAN = 10;

  function tomanFromRial(rial) {
    return Math.floor(Number(rial || 0) / RIAL_PER_TOMAN);
  }

  function rialFromToman(toman) {
    return (parseInt(String(toman || '0'), 10) || 0) * RIAL_PER_TOMAN;
  }

  function formatTomanFromRial(rial) {
    return tomanFromRial(rial).toLocaleString('fa-IR') + ' تومان';
  }

  var BLOCK_LABELS = {
    hero: 'هیرو',
    slider: 'اسلایدر',
    search: 'جستجو',
    categories: 'دسته‌بندی‌ها',
    featured: 'محصولات ویژه',
    products: 'لیست محصولات',
    spacer: 'فاصله',
    announcement_bar: 'نوار اعلان',
    story_bar: 'استوری',
    countdown: 'شمارش معکوس',
    coupon: 'کد تخفیف',
    product_carousel: 'کاروسل محصول',
    banner_grid: 'گرید بنر',
    video: 'ویدیو',
    testimonials: 'نظرات',
    trust_badges: 'نشان اعتماد',
    faq: 'سوالات متداول',
    info: 'درباره ما',
    bundle: 'باندل',
    rich_text: 'متن آزاد',
  };

  var BLOCK_ICONS = {
    hero: 'image',
    slider: 'images',
    search: 'search',
    categories: 'folder',
    featured: 'star',
    products: 'grid',
    spacer: 'distribute-vertical',
    announcement_bar: 'megaphone',
    story_bar: 'record-circle',
    countdown: 'alarm',
    coupon: 'ticket-perforated',
    product_carousel: 'collection',
    banner_grid: 'grid-3x2-gap',
    video: 'play-circle',
    testimonials: 'chat-quote',
    trust_badges: 'shield-check',
    faq: 'question-circle',
    info: 'info-circle',
    bundle: 'box-seam',
    rich_text: 'file-text',
  };

  var BLOCK_PALETTE = [
    { group: 'ساختار', blocks: ['hero', 'slider', 'search', 'rich_text', 'spacer'] },
    { group: 'فروشگاه', blocks: ['categories', 'featured', 'products', 'product_carousel', 'banner_grid', 'bundle'] },
    { group: 'مارکتینگ', blocks: ['announcement_bar', 'story_bar', 'countdown', 'coupon', 'video'] },
    { group: 'اعتماد', blocks: ['testimonials', 'trust_badges', 'faq', 'info'] },
  ];

  var root = null;
  var form = null;
  var threadEl = null;
  var hiddenEl = null;
  var inspectorBody = null;
  var inspectorTitle = null;
  var inspectorHint = null;
  var storeTitleEl = null;
  var paletteEl = null;
  var outlineEl = null;
  var blockCountEl = null;
  var categories = [];
  var items = [];
  var pickerCategories = [];
  var pickerItems = [];
  var pickerTags = [];
  var discountCodes = [];
  var state = { blocks: [] };
  var selection = null;
  var globalPanel = null;
  var movedFieldNodes = [];
  var uploadUrl = '';
  var logoSavedUrl = '';
  var logoPreviewObjectUrl = '';
  var heroBgSavedUrl = '';
  var heroBgPreviewObjectUrl = '';

  function $(id) {
    return document.getElementById(id);
  }

  function newBlockId() {
    return 'b_' + Math.random().toString(16).slice(2, 10);
  }

  function defaultEndsAtIso() {
    var d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 19);
  }

  function defaultBlock(type) {
    var id = newBlockId();
    if (type === 'hero') return { id: id, type: 'hero', variant: 'banner' };
    if (type === 'search') return { id: id, type: 'search', placeholder: 'جستجو…' };
    if (type === 'slider') {
      return {
        id: id,
        type: 'slider',
        autoplay: true,
        slides: [{ title: 'اسلاید ۱', subtitle: '', image_url: '', link_url: '' }],
      };
    }
    if (type === 'categories') {
      return { id: id, type: 'categories', title: 'دسته‌بندی‌ها', columns: 2, limit: 8 };
    }
    if (type === 'featured') {
      return { id: id, type: 'featured', title: 'محصولات ویژه', limit: 6, layout: 'scroll' };
    }
    if (type === 'products') {
      return { id: id, type: 'products', title: 'همه محصولات', layout: 'grid', limit: 0 };
    }
    if (type === 'spacer') return { id: id, type: 'spacer', size: 'md' };
    if (type === 'announcement_bar') {
      return { id: id, type: 'announcement_bar', text: 'ارسال رایگان بالای ۵۰۰ هزار تومان', bg: '#111111', color: '#ffffff', dismissible: true };
    }
    if (type === 'story_bar') {
      return {
        id: id,
        type: 'story_bar',
        items: [{ title: 'جدید', image: '', slides: [{ image: '', duration: 5 }] }],
      };
    }
    if (type === 'countdown') {
      return {
        id: id,
        type: 'countdown',
        title: 'فروش ویژه',
        ends_at: defaultEndsAtIso(),
        cta_label: 'مشاهده حراج',
        cta_target: { kind: 'flash_sale', value: '' },
        accent: '#c2402f',
      };
    }
    if (type === 'coupon') {
      return { id: id, type: 'coupon', title: 'کد تخفیف', discount_id: null, code: '', subtitle: '', copy_label: 'کپی کد' };
    }
    if (type === 'product_carousel') {
      return { id: id, type: 'product_carousel', title: 'پرفروش‌ترین‌ها', source: 'bestselling', limit: 10 };
    }
    if (type === 'banner_grid') {
      return { id: id, type: 'banner_grid', columns: 2, items: [{ image: '', target: { kind: 'category', value: '' } }] };
    }
    if (type === 'video') {
      return { id: id, type: 'video', title: 'معرفی', url: '', poster: '' };
    }
    if (type === 'testimonials') {
      return { id: id, type: 'testimonials', title: 'نظر مشتری‌ها', items: [{ name: 'مریم', text: 'عالی بود', rating: 5 }] };
    }
    if (type === 'trust_badges') {
      return { id: id, type: 'trust_badges', items: [{ icon: '✅', label: 'اصالت کالا' }, { icon: '🚚', label: 'ارسال سریع' }] };
    }
    if (type === 'faq') {
      return { id: id, type: 'faq', title: 'سوالات متداول', items: [{ q: 'هزینه ارسال؟', a: 'بسته به شهر متفاوت است' }] };
    }
    if (type === 'info') {
      return { id: id, type: 'info', about: 'درباره فروشگاه', phones: [], address: '', hours: '۹ تا ۲۱' };
    }
    if (type === 'bundle') {
      return { id: id, type: 'bundle', title: 'ست ویژه', item_slugs: [], bundle_price: 0, badge: '' };
    }
    if (type === 'rich_text') {
      return { id: id, type: 'rich_text', title: '', html: '<p>متن دلخواه</p>', align: 'right' };
    }
    return null;
  }

  function parseInitialBlocks() {
    var tag = $('miniapp-home-blocks-data');
    if (tag && tag.textContent.trim()) {
      try {
        var data = JSON.parse(tag.textContent);
        if (Array.isArray(data) && data.length) return data;
      } catch (e) {
        /* ignore */
      }
    }
    if (hiddenEl && hiddenEl.value.trim()) {
      try {
        return JSON.parse(hiddenEl.value);
      } catch (e2) {
        /* ignore */
      }
    }
    return [
      defaultBlock('hero'),
      defaultBlock('search'),
      defaultBlock('categories'),
      defaultBlock('featured'),
      defaultBlock('products'),
    ].filter(Boolean);
  }

  function syncHidden() {
    if (hiddenEl) hiddenEl.value = JSON.stringify(state.blocks);
  }

  function formVal(name) {
    if (!form) return '';
    var el = form.querySelector('[name="' + name + '"]');
    return el ? String(el.value || '').trim() : '';
  }

  function featuredItems() {
    return items.filter(function (i) {
      return i.is_featured;
    });
  }

  function itemsForCarouselSource(block) {
    var limit = block.limit || 8;
    var source = block.source || 'featured';
    var list = items.slice();
    if (source === 'featured') {
      list = featuredItems();
      if (!list.length) list = items.slice();
    } else if (source === 'newest') {
      list = items.slice().reverse();
    } else if (source === 'bestselling') {
      list = items.slice().sort(function (a, b) {
        return (b.sales_count || 0) - (a.sales_count || 0);
      });
    } else if (source === 'discounted') {
      list = items.filter(function (i) {
        return i.compare_at_price && i.price && i.compare_at_price > i.price;
      });
      if (!list.length) list = items.slice();
    } else if (source === 'category' && block.category) {
      list = items.filter(function (i) {
        return i.category_slug === block.category;
      });
    } else if (source === 'tag' && block.tag) {
      list = items.filter(function (i) {
        return (i.tags || []).indexOf(block.tag) >= 0;
      });
    }
    return list.slice(0, limit);
  }

  function bundlePreviewItems(block) {
    var slugs = block.item_slugs || [];
    if (!slugs.length) return items.slice(0, 3);
    return items.filter(function (i) {
      return slugs.indexOf(i.slug) >= 0;
    }).slice(0, 4);
  }

  function updateBlockCountLabel() {
    if (blockCountEl) {
      blockCountEl.textContent = state.blocks.length + ' المان';
    }
  }

  function scrollBlockIntoView(index) {
    if (!threadEl) return;
    var node = threadEl.querySelector('[data-block-index="' + index + '"]');
    if (node && node.scrollIntoView) {
      node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function renderBlockPalette() {
    if (!paletteEl) return;
    paletteEl.innerHTML = '';
    BLOCK_PALETTE.forEach(function (group) {
      var section = document.createElement('div');
      section.className = 'miniapp-palette-group';

      var title = document.createElement('div');
      title.className = 'miniapp-palette-group-title';
      title.textContent = group.group;
      section.appendChild(title);

      var grid = document.createElement('div');
      grid.className = 'miniapp-palette-grid';
      group.blocks.forEach(function (type) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'miniapp-palette-btn';
        btn.setAttribute('data-add-block', type);
        btn.title = BLOCK_LABELS[type] || type;
        btn.innerHTML =
          '<i class="bi bi-' +
          (BLOCK_ICONS[type] || 'plus') +
          '"></i><span>' +
          escapeHtml(BLOCK_LABELS[type] || type) +
          '</span>';
        btn.addEventListener('click', function () {
          addBlock(type);
        });
        grid.appendChild(btn);
      });
      section.appendChild(grid);
      paletteEl.appendChild(section);
    });
  }

  function renderBlocksOutline() {
    if (!outlineEl) return;
    outlineEl.innerHTML = '';
    if (!state.blocks.length) {
      outlineEl.innerHTML = '<div class="miniapp-blocks-outline-empty">هنوز المانی اضافه نشده</div>';
      return;
    }
    state.blocks.forEach(function (block, index) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className =
        'miniapp-outline-item' + (selection === index ? ' is-selected' : '');
      row.setAttribute('data-outline-index', String(index));
      row.innerHTML =
        '<span class="miniapp-outline-index">' +
        (index + 1) +
        '</span>' +
        '<i class="bi bi-' +
        (BLOCK_ICONS[block.type] || 'square') +
        '"></i>' +
        '<span class="miniapp-outline-label">' +
        escapeHtml(BLOCK_LABELS[block.type] || block.type) +
        '</span>' +
        '<span class="miniapp-outline-actions">' +
        (index > 0 ? '<i class="bi bi-chevron-up" data-move="up"></i>' : '') +
        (index < state.blocks.length - 1 ? '<i class="bi bi-chevron-down" data-move="down"></i>' : '') +
        '</span>';
      row.addEventListener('click', function (e) {
        var move = e.target.closest('[data-move]');
        if (move) {
          e.stopPropagation();
          moveBlock(move.getAttribute('data-move') === 'up' ? -1 : 1, index);
          return;
        }
        selectBlock(index);
      });
      outlineEl.appendChild(row);
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function stopProp(e) {
    e.stopPropagation();
  }

  function logoUrl() {
    if (logoPreviewObjectUrl) return logoPreviewObjectUrl;
    return logoSavedUrl || '';
  }

  function heroBackgroundUrl() {
    if (heroBgPreviewObjectUrl) return heroBgPreviewObjectUrl;
    return heroBgSavedUrl || '';
  }

  function mkImageThumb(imageUrl, className) {
    if (imageUrl) {
      var img = document.createElement('img');
      img.className = className || 'miniapp-preview-thumb';
      img.src = imageUrl;
      img.alt = '';
      img.loading = 'lazy';
      return img;
    }
    var ph = document.createElement('div');
    ph.className = (className || 'miniapp-preview-thumb') + ' miniapp-preview-thumb--empty';
    ph.innerHTML = '<i class="bi bi-image"></i>';
    return ph;
  }

  function mkPreviewCard(title, imageUrl, cardClass) {
    var card = document.createElement('div');
    card.className = cardClass;
    card.appendChild(mkImageThumb(imageUrl, 'miniapp-preview-thumb'));
    var label = document.createElement('span');
    label.className = 'miniapp-preview-card-title';
    label.textContent = title;
    card.appendChild(label);
    return card;
  }

  function uploadMedia(file, onOk, onErr) {
    if (!uploadUrl) {
      if (onErr) onErr('آدرس آپلود تنظیم نشده.');
      return;
    }
    var fd = new FormData();
    fd.append('file', file);
    var csrf = form && form.querySelector('[name=csrfmiddlewaretoken]');
    if (csrf) fd.append('csrfmiddlewaretoken', csrf.value);
    fetch(uploadUrl, { method: 'POST', body: fd, credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && j.ok && j.url) onOk(j.url);
        else if (onErr) onErr((j && j.error) || 'آپلود ناموفق');
      })
      .catch(function () {
        if (onErr) onErr('خطا در آپلود');
      });
  }

  function uploadImage(file, onOk, onErr) {
    uploadMedia(file, onOk, onErr);
  }

  function mediaUploadField(currentUrl, onUploaded, options) {
    options = options || {};
    var accept = options.accept || 'image/*';
    var kind = options.kind || 'image';
    var uploadLabel = options.uploadLabel || 'آپلود فایل';
    var changeLabel = options.changeLabel || 'تغییر فایل';
    var wrap = document.createElement('div');
    wrap.className = 'miniapp-image-upload mb-2';

    function renderPreview(url) {
      var old = wrap.querySelector('.miniapp-media-upload-preview');
      if (old) old.remove();
      if (!url) return;
      var box = document.createElement('div');
      box.className = 'miniapp-media-upload-preview';
      if (kind === 'video') {
        var vid = document.createElement('video');
        vid.src = url;
        vid.controls = true;
        vid.playsInline = true;
        vid.className = 'miniapp-video-upload-preview';
        box.appendChild(vid);
      } else {
        box.appendChild(mkImageThumb(url, 'miniapp-slide-preview-thumb'));
      }
      wrap.insertBefore(box, wrap.firstChild);
    }

    renderPreview(currentUrl);

    var fileInp = document.createElement('input');
    fileInp.type = 'file';
    fileInp.accept = accept;
    fileInp.className = 'visually-hidden';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-panel-ghost btn-sm';
    btn.innerHTML =
      '<i class="bi bi-cloud-upload me-1"></i>' + (currentUrl ? changeLabel : uploadLabel);
    btn.addEventListener('click', function () {
      fileInp.click();
    });

    fileInp.addEventListener('change', function () {
      var f = fileInp.files && fileInp.files[0];
      if (!f) return;
      btn.disabled = true;
      btn.textContent = 'در حال آپلود…';
      uploadMedia(
        f,
        function (url) {
          currentUrl = url;
          onUploaded(url);
          renderPreview(url);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-cloud-upload me-1"></i>' + changeLabel;
          fileInp.value = '';
        },
        function () {
          btn.disabled = false;
          btn.innerHTML =
            '<i class="bi bi-cloud-upload me-1"></i>' + (currentUrl ? changeLabel : uploadLabel);
          fileInp.value = '';
        }
      );
    });

    wrap.appendChild(btn);
    wrap.appendChild(fileInp);
    return wrap;
  }

  function imageUploadField(currentUrl, onUploaded) {
    return mediaUploadField(currentUrl, onUploaded, {
      accept: 'image/*',
      kind: 'image',
      uploadLabel: 'آپلود تصویر',
      changeLabel: 'تغییر تصویر',
    });
  }

  function videoUploadField(currentUrl, onUploaded) {
    return mediaUploadField(currentUrl, onUploaded, {
      accept: 'video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv',
      kind: 'video',
      uploadLabel: 'آپلود ویدیو',
      changeLabel: 'تغییر ویدیو',
    });
  }

  function syncStoreTitle() {
    if (storeTitleEl) {
      storeTitleEl.textContent = formVal('hero_title') || 'ویترین';
    }
  }

  function bindLogoPreview() {
    if (!form) return;
    var logoInp = form.querySelector('[name="logo"]');
    if (!logoInp) return;
    logoInp.addEventListener('change', function () {
      var f = logoInp.files && logoInp.files[0];
      if (logoPreviewObjectUrl) {
        URL.revokeObjectURL(logoPreviewObjectUrl);
        logoPreviewObjectUrl = '';
      }
      if (f) logoPreviewObjectUrl = URL.createObjectURL(f);
      renderCanvas();
    });
    var bgInp = form.querySelector('[name="hero_background"]');
    if (!bgInp) return;
    bgInp.addEventListener('change', function () {
      var f = bgInp.files && bgInp.files[0];
      if (heroBgPreviewObjectUrl) {
        URL.revokeObjectURL(heroBgPreviewObjectUrl);
        heroBgPreviewObjectUrl = '';
      }
      if (f) heroBgPreviewObjectUrl = URL.createObjectURL(f);
      renderCanvas();
    });
  }

  function clearSelection() {
    selection = null;
    globalPanel = null;
    restoreMovedFields();
    renderCanvas();
    renderInspector();
  }

  function selectBlock(index) {
    selection = index;
    globalPanel = null;
    renderCanvas();
    renderInspector();
    scrollBlockIntoView(index);
  }

  function toggleBlock(index) {
    if (selection === index) clearSelection();
    else selectBlock(index);
  }

  var dragPayload = null;
  var pointerDrag = null;
  var pointerDragListenersBound = false;

  function moveBlockToIndex(fromIndex, toIndex) {
    if (fromIndex < 0 || fromIndex >= state.blocks.length) return fromIndex;
    if (toIndex < 0) toIndex = 0;
    if (toIndex > state.blocks.length) toIndex = state.blocks.length;
    if (fromIndex === toIndex || fromIndex + 1 === toIndex) return fromIndex;
    var blocks = state.blocks;
    var item = blocks.splice(fromIndex, 1)[0];
    var adjusted = toIndex > fromIndex ? toIndex - 1 : toIndex;
    blocks.splice(adjusted, 0, item);
    return adjusted;
  }

  function clearDropHighlights() {
    if (!threadEl) return;
    threadEl.querySelectorAll('.is-drop-active').forEach(function (el) {
      el.classList.remove('is-drop-active');
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

  function hitDropTarget(clientX, clientY) {
    if (!pointerDrag || !threadEl) return null;
    var el = elementAtPoint(clientX, clientY);
    if (!el || !threadEl.contains(el)) return null;
    var zone = el.closest('.flow-canvas-drop-zone');
    if (zone) {
      var insertIndex = parseInt(zone.getAttribute('data-insert-index'), 10);
      if (!isNaN(insertIndex)) {
        return { type: 'line', insertIndex: insertIndex, zone: zone };
      }
    }
    return null;
  }

  function updateDropHighlights(target) {
    clearDropHighlights();
    if (target && target.type === 'line' && target.zone) {
      target.zone.classList.add('is-drop-active');
    }
  }

  function applyPointerDrop(target) {
    if (!pointerDrag || !pointerDrag.active || !target) return;
    var payload = pointerDrag.payload;
    if (target.type === 'line' && payload.kind === 'block') {
      var fromIndex = payload.indices[0];
      if (target.insertIndex === fromIndex || target.insertIndex === fromIndex + 1) return;
      var newIdx = moveBlockToIndex(fromIndex, target.insertIndex);
      selectBlock(newIdx);
    }
  }

  function finishPointerDrag(clientX, clientY) {
    if (!pointerDrag) return;
    var wasActive = pointerDrag.active;
    var target = wasActive ? hitDropTarget(clientX, clientY) : null;
    if (pointerDrag.host) {
      pointerDrag.host.classList.remove('is-dragging');
      pointerDrag.host.style.pointerEvents = '';
      pointerDrag.host.style.visibility = '';
    }
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
      if (dx < 3 && dy < 3) return;
      pointerDrag.active = true;
      dragPayload = pointerDrag.payload;
      if (pointerDrag.host) {
        pointerDrag.host.classList.add('is-dragging');
        pointerDrag.host.style.pointerEvents = 'none';
        pointerDrag.ghost = createDragGhost(pointerDrag.host);
      }
      if (threadEl) threadEl.classList.add('is-canvas-dragging');
    }
    e.preventDefault();
    positionDragGhost(e.clientX, e.clientY);
    pointerDrag.dropTarget = hitDropTarget(e.clientX, e.clientY);
    updateDropHighlights(pointerDrag.dropTarget);
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
    document.addEventListener(
      'touchmove',
      function (e) {
        if (!pointerDrag || !e.touches.length) return;
        onDocumentPointerMove(e.touches[0]);
      },
      { passive: false }
    );
    document.addEventListener('touchend', function (e) {
      if (!pointerDrag) return;
      var t = e.changedTouches && e.changedTouches[0];
      finishPointerDrag(t ? t.clientX : pointerDrag.startX, t ? t.clientY : pointerDrag.startY);
    });
  }

  function attachDragSource(sourceEl, payload, hostSelector, ignoreSelector) {
    if (!sourceEl) return;
    function startPointerDrag(clientX, clientY, e) {
      if (e) {
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
    }
    sourceEl.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      if (ignoreSelector && e.target && e.target.closest(ignoreSelector)) return;
      startPointerDrag(e.clientX, e.clientY, e);
    });
    sourceEl.addEventListener(
      'touchstart',
      function (e) {
        if (!e.touches.length) return;
        var t = e.touches[0];
        var under = document.elementFromPoint(t.clientX, t.clientY);
        if (ignoreSelector && under && under.closest(ignoreSelector)) return;
        startPointerDrag(t.clientX, t.clientY, e);
      },
      { passive: false }
    );
  }

  function decorateBlockDrag(wrap, index) {
    if (!wrap || index < 0) return;
    wrap.classList.add('flow-canvas-block--draggable');
    attachDragSource(wrap, { kind: 'block', indices: [index] }, '.flow-canvas-block', '.flow-canvas-drop-zone');
  }

  function appendDropZone(insertIndex) {
    if (!threadEl) return;
    var zone = document.createElement('div');
    zone.className = 'flow-canvas-drop-zone';
    zone.setAttribute('data-insert-index', String(insertIndex));
    zone.innerHTML =
      '<span class="flow-canvas-drop-zone-line" aria-hidden="true"></span>' +
      '<span class="flow-canvas-drop-zone-label">رها کنید</span>';
    threadEl.appendChild(zone);
  }

  function appendInspectorBlockActions(container, blockIndex) {
    var tools = document.createElement('div');
    tools.className = 'flow-inspector-item-actions d-flex flex-wrap gap-2 mb-3 pb-3 border-bottom';

    if (blockIndex > 0) {
      var moveUp = document.createElement('button');
      moveUp.type = 'button';
      moveUp.className = 'btn btn-panel-ghost btn-sm';
      moveUp.innerHTML = '<i class="bi bi-arrow-up"></i> بالا';
      moveUp.addEventListener('click', function () {
        moveBlock(-1, blockIndex);
      });
      tools.appendChild(moveUp);
    }

    if (blockIndex < state.blocks.length - 1) {
      var moveDown = document.createElement('button');
      moveDown.type = 'button';
      moveDown.className = 'btn btn-panel-ghost btn-sm';
      moveDown.innerHTML = '<i class="bi bi-arrow-down"></i> پایین';
      moveDown.addEventListener('click', function () {
        moveBlock(1, blockIndex);
      });
      tools.appendChild(moveDown);
    }

    var del = document.createElement('button');
    del.type = 'button';
    del.className = 'btn btn-panel-ghost btn-sm text-danger';
    del.innerHTML = '<i class="bi bi-trash"></i> حذف';
    del.addEventListener('click', function () {
      state.blocks.splice(blockIndex, 1);
      clearSelection();
    });
    tools.appendChild(del);
    container.appendChild(tools);
  }

  function renderBlockPreview(block, index) {
    var wrap = document.createElement('div');
    wrap.className =
      'flow-canvas-block flow-canvas-block--miniapp flow-canvas-block--' +
      block.type +
      (selection === index ? ' is-selected' : '');
    wrap.setAttribute('data-block-index', String(index));

    var badge = document.createElement('div');
    badge.className = 'flow-canvas-block-badge';
    badge.innerHTML = '<i class="bi bi-grip-vertical"></i> ' + (BLOCK_LABELS[block.type] || block.type);
    wrap.appendChild(badge);

    var body = document.createElement('div');
    body.className = 'flow-canvas-block-body flow-canvas-block-body--miniapp';

    if (block.type === 'hero') {
      var primary = formVal('theme_primary') || '#334155';
      var logo = logoUrl();
      var heroBg = heroBackgroundUrl();
      if (block.variant === 'banner') {
        var heroBanner = document.createElement('div');
        heroBanner.className = 'miniapp-preview-hero-banner';
        if (heroBg) {
          heroBanner.classList.add('has-background');
          heroBanner.style.backgroundImage =
            'linear-gradient(to top, rgba(15,23,42,0.78), rgba(15,23,42,0.25)), url(' + heroBg + ')';
        } else {
          heroBanner.style.setProperty('--hero-primary', primary);
        }
        var heroInner = document.createElement('div');
        heroInner.className = 'miniapp-preview-hero-banner-inner';
        if (logo) {
          heroInner.appendChild(mkImageThumb(logo, 'miniapp-preview-hero-logo'));
        }
        var heroText = document.createElement('div');
        heroText.className = 'miniapp-preview-hero-text';
        heroText.innerHTML =
          '<strong>' +
          escapeHtml(formVal('hero_title') || 'ویترین') +
          '</strong><span>' +
          escapeHtml(formVal('hero_subtitle') || 'زیرعنوان') +
          '</span>';
        heroInner.appendChild(heroText);
        heroBanner.appendChild(heroInner);
        body.appendChild(heroBanner);
      } else {
        var heroCompact = document.createElement('div');
        heroCompact.className = 'miniapp-preview-hero-compact';
        if (logo) {
          heroCompact.appendChild(mkImageThumb(logo, 'miniapp-preview-hero-logo miniapp-preview-hero-logo--sm'));
        }
        var compactTitle = document.createElement('strong');
        compactTitle.textContent = formVal('hero_title') || 'ویترین';
        heroCompact.appendChild(compactTitle);
        body.appendChild(heroCompact);
      }
    } else if (block.type === 'search') {
      body.innerHTML =
        '<div class="miniapp-preview-search"><i class="bi bi-search"></i> ' +
        escapeHtml(block.placeholder || 'جستجو…') +
        '</div>';
    } else if (block.type === 'slider') {
      var track = document.createElement('div');
      track.className = 'miniapp-preview-slider-track';
      (block.slides || []).forEach(function (slide, si) {
        var card = document.createElement('div');
        card.className = 'miniapp-preview-slide' + (slide.image_url ? ' has-image' : '');
        if (slide.image_url) {
          card.style.backgroundImage =
            'linear-gradient(to top, rgba(15,23,42,0.78), rgba(15,23,42,0.2)), url(' + slide.image_url + ')';
        }
        var slideText = document.createElement('div');
        slideText.className = 'miniapp-preview-slide-text';
        slideText.innerHTML =
          '<strong>' +
          escapeHtml(slide.title || 'اسلاید ' + (si + 1)) +
          '</strong>' +
          (slide.subtitle ? '<span>' + escapeHtml(slide.subtitle) + '</span>' : '');
        card.appendChild(slideText);
        track.appendChild(card);
      });
      if (!track.children.length) {
        track.innerHTML = '<div class="miniapp-preview-slide miniapp-preview-slide--empty">اسلاید خالی</div>';
      }
      body.appendChild(track);
    } else if (block.type === 'categories') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || '') + '</div>';
      var grid = document.createElement('div');
      grid.className = 'miniapp-preview-cats cols-' + (block.columns || 2);
      var cats = categories.slice(0, block.limit || 8);
      if (!cats.length) {
        grid.appendChild(mkPreviewCard('دسته نمونه', '', 'miniapp-preview-cat'));
        grid.appendChild(mkPreviewCard('دسته', '', 'miniapp-preview-cat'));
      } else {
        cats.forEach(function (c) {
          grid.appendChild(mkPreviewCard(c.name, c.image_url || '', 'miniapp-preview-cat'));
        });
      }
      body.appendChild(grid);
    } else if (block.type === 'featured') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || '') + '</div>';
      var rowF = document.createElement('div');
      rowF.className =
        block.layout === 'grid'
          ? 'miniapp-preview-products miniapp-preview-products--grid'
          : 'miniapp-preview-products-row';
      var list = featuredItems().slice(0, block.limit || 6);
      if (!list.length) list = items.slice(0, Math.min(block.limit || 4, 4));
      if (!list.length) {
        rowF.appendChild(mkPreviewCard('★ محصول ویژه', '', 'miniapp-preview-product-card'));
      } else {
        list.forEach(function (it) {
          rowF.appendChild(mkPreviewCard(it.title, it.image_url || '', 'miniapp-preview-product-card'));
        });
      }
      body.appendChild(rowF);
    } else if (block.type === 'products') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || '') + '</div>';
      var gridP = document.createElement('div');
      gridP.className =
        'miniapp-preview-products ' +
        (block.layout === 'list' ? 'miniapp-preview-products--list' : 'miniapp-preview-products--grid');
      var prods = items.slice(0, block.limit || 4);
      if (!prods.length) {
        gridP.appendChild(mkPreviewCard('محصول', '', 'miniapp-preview-product'));
        gridP.appendChild(mkPreviewCard('محصول', '', 'miniapp-preview-product'));
      } else {
        prods.forEach(function (it) {
          if (block.layout === 'list') {
            var listRow = document.createElement('div');
            listRow.className = 'miniapp-preview-product miniapp-preview-product--list';
            listRow.appendChild(mkImageThumb(it.image_url || '', 'miniapp-preview-thumb miniapp-preview-thumb--list'));
            var listTitle = document.createElement('strong');
            listTitle.textContent = it.title;
            listRow.appendChild(listTitle);
            gridP.appendChild(listRow);
          } else {
            gridP.appendChild(mkPreviewCard(it.title, it.image_url || '', 'miniapp-preview-product'));
          }
        });
      }
      body.appendChild(gridP);
    } else if (block.type === 'spacer') {
      body.innerHTML = '<div class="miniapp-preview-spacer size-' + (block.size || 'md') + '"></div>';
    } else if (block.type === 'announcement_bar') {
      body.innerHTML =
        '<div class="miniapp-preview-announcement" style="background:' +
        escapeHtml(block.bg || '#111') +
        ';color:' +
        escapeHtml(block.color || '#fff') +
        '">' +
        escapeHtml(block.text || 'اعلان') +
        '</div>';
    } else if (block.type === 'story_bar') {
      var storyTrack = document.createElement('div');
      storyTrack.className = 'miniapp-preview-story-track';
      (block.items || []).forEach(function (story) {
        var chip = document.createElement('div');
        chip.className = 'miniapp-preview-story';
        if (story.image) {
          chip.appendChild(mkImageThumb(story.image, 'miniapp-preview-story-img'));
        } else {
          var ph = document.createElement('div');
          ph.className = 'miniapp-preview-story-img miniapp-preview-thumb--empty';
          ph.innerHTML = '<i class="bi bi-circle"></i>';
          chip.appendChild(ph);
        }
        var lbl = document.createElement('span');
        lbl.className = 'miniapp-preview-story-label';
        lbl.textContent = story.title || 'استوری';
        chip.appendChild(lbl);
        storyTrack.appendChild(chip);
      });
      body.appendChild(storyTrack);
    } else if (block.type === 'countdown') {
      body.innerHTML =
        '<div class="miniapp-preview-countdown" style="--accent:' +
        escapeHtml(block.accent || '#c2402f') +
        '"><strong>' +
        escapeHtml(block.title || 'فروش ویژه') +
        '</strong><div class="miniapp-preview-countdown-timer">۰۷ : ۱۲ : ۳۴ : ۵۶</div>' +
        (block.cta_label ? '<span class="miniapp-preview-countdown-cta">' + escapeHtml(block.cta_label) + '</span>' : '') +
        '</div>';
    } else if (block.type === 'coupon') {
      body.innerHTML =
        '<div class="miniapp-preview-coupon"><strong>' +
        escapeHtml(block.title || 'کد تخفیف') +
        '</strong>' +
        (block.subtitle ? '<span class="miniapp-preview-coupon-sub">' + escapeHtml(block.subtitle) + '</span>' : '') +
        '<code>' +
        escapeHtml(block.code || 'SALE') +
        '</code></div>';
    } else if (block.type === 'product_carousel') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || 'محصولات') + '</div>';
      var carousel = document.createElement('div');
      carousel.className = 'miniapp-preview-products-row';
      var carouselItems = itemsForCarouselSource(block);
      if (!carouselItems.length) {
        carousel.appendChild(mkPreviewCard('محصول نمونه', '', 'miniapp-preview-product-card'));
        carousel.appendChild(mkPreviewCard('محصول', '', 'miniapp-preview-product-card'));
      } else {
        carouselItems.forEach(function (it) {
          carousel.appendChild(mkPreviewCard(it.title, it.image_url || '', 'miniapp-preview-product-card'));
        });
      }
      body.appendChild(carousel);
    } else if (block.type === 'banner_grid') {
      var bgrid = document.createElement('div');
      bgrid.className = 'miniapp-preview-banner-grid cols-' + (block.columns || 2);
      (block.items || []).forEach(function (banner) {
        var cell = document.createElement('div');
        cell.className = 'miniapp-preview-banner-cell';
        if (banner.image) {
          cell.appendChild(mkImageThumb(banner.image, 'miniapp-preview-thumb'));
        } else {
          cell.className += ' miniapp-preview-banner-cell--empty';
          cell.innerHTML = '<i class="bi bi-image"></i>';
        }
        bgrid.appendChild(cell);
      });
      if (!bgrid.children.length) {
        bgrid.innerHTML = '<div class="miniapp-preview-banner-cell miniapp-preview-banner-cell--empty"><i class="bi bi-image"></i></div>';
      }
      body.appendChild(bgrid);
    } else if (block.type === 'faq') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || 'سوالات متداول') + '</div>';
      (block.items || []).slice(0, 4).forEach(function (item, fi) {
        var row = document.createElement('div');
        row.className = 'miniapp-preview-faq-item' + (fi === 0 ? ' is-open' : '');
        row.innerHTML =
          '<span class="miniapp-preview-faq-q">' +
          escapeHtml(item.q || 'سوال') +
          '</span><span class="miniapp-preview-faq-toggle">' +
          (fi === 0 ? '−' : '+') +
          '</span>' +
          (fi === 0 && item.a ? '<div class="miniapp-preview-faq-a">' + escapeHtml(item.a) + '</div>' : '');
        body.appendChild(row);
      });
    } else if (block.type === 'info') {
      body.innerHTML =
        '<div class="miniapp-preview-info">' +
        '<p>' +
        escapeHtml(block.about || 'درباره ما') +
        '</p>' +
        (block.hours ? '<small>ساعت: ' + escapeHtml(block.hours) + '</small>' : '') +
        (block.address ? '<small>' + escapeHtml(block.address) + '</small>' : '') +
        '</div>';
    } else if (block.type === 'video') {
      var videoWrap = document.createElement('div');
      videoWrap.className = 'miniapp-preview-video-wrap';
      if (block.title) {
        videoWrap.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title) + '</div>';
      }
      var videoBox = document.createElement('div');
      videoBox.className = 'miniapp-preview-video';
      if (block.poster) {
        videoBox.style.backgroundImage = 'url(' + block.poster + ')';
        videoBox.classList.add('has-poster');
      }
      videoBox.innerHTML = '<i class="bi bi-play-circle"></i>';
      videoWrap.appendChild(videoBox);
      body.appendChild(videoWrap);
    } else if (block.type === 'testimonials') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || 'نظر مشتری‌ها') + '</div>';
      var tTrack = document.createElement('div');
      tTrack.className = 'miniapp-preview-testimonials-track';
      (block.items || []).forEach(function (t) {
        var card = document.createElement('div');
        card.className = 'miniapp-preview-testimonial';
        var stars = '★'.repeat(Math.min(5, t.rating || 5));
        card.innerHTML =
          '<div class="miniapp-preview-testimonial-stars">' +
          stars +
          '</div><p>' +
          escapeHtml(t.text || '') +
          '</p><strong>' +
          escapeHtml(t.name || '') +
          '</strong>';
        tTrack.appendChild(card);
      });
      if (!tTrack.children.length) {
        tTrack.innerHTML = '<div class="miniapp-preview-testimonial"><p>نظر مشتری نمونه</p></div>';
      }
      body.appendChild(tTrack);
    } else if (block.type === 'trust_badges') {
      var badges = document.createElement('div');
      badges.className = 'miniapp-preview-trust-badges';
      (block.items || []).forEach(function (badge) {
        var chip = document.createElement('span');
        chip.className = 'miniapp-preview-trust-badge';
        chip.innerHTML =
          '<span class="miniapp-preview-trust-icon">' +
          escapeHtml(badge.icon || '✓') +
          '</span>' +
          escapeHtml(badge.label || '');
        badges.appendChild(chip);
      });
      if (!badges.children.length) {
        badges.innerHTML = '<span class="miniapp-preview-trust-badge">اعتماد</span>';
      }
      body.appendChild(badges);
    } else if (block.type === 'bundle') {
      var bundleWrap = document.createElement('div');
      bundleWrap.className = 'miniapp-preview-bundle';
      var bundleHead = document.createElement('div');
      bundleHead.className = 'miniapp-preview-bundle-head';
      bundleHead.innerHTML = '<strong>' + escapeHtml(block.title || 'ست ویژه') + '</strong>';
      if (block.badge) {
        var badgeEl = document.createElement('span');
        badgeEl.className = 'miniapp-preview-bundle-badge';
        badgeEl.textContent = block.badge;
        bundleHead.appendChild(badgeEl);
      }
      bundleWrap.appendChild(bundleHead);
      var bundleRow = document.createElement('div');
      bundleRow.className = 'miniapp-preview-products-row';
      bundlePreviewItems(block).forEach(function (it) {
        bundleRow.appendChild(mkPreviewCard(it.title, it.image_url || '', 'miniapp-preview-product-card'));
      });
      if (!bundleRow.children.length) {
        bundleRow.appendChild(mkPreviewCard('محصول', '', 'miniapp-preview-product-card'));
      }
      bundleWrap.appendChild(bundleRow);
      if (block.bundle_price) {
        var price = document.createElement('div');
        price.className = 'miniapp-preview-bundle-price';
        price.textContent = formatTomanFromRial(block.bundle_price);
        bundleWrap.appendChild(price);
      }
      body.appendChild(bundleWrap);
    } else if (block.type === 'rich_text') {
      var rt = document.createElement('div');
      rt.className = 'miniapp-preview-rich-text align-' + (block.align || 'right');
      if (block.title) {
        rt.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title) + '</div>';
      }
      var htmlBox = document.createElement('div');
      htmlBox.className = 'miniapp-preview-rich-text-body';
      htmlBox.innerHTML = block.html || '<p>متن آزاد</p>';
      rt.appendChild(htmlBox);
      body.appendChild(rt);
    } else {
      body.innerHTML =
        '<div class="miniapp-preview-generic text-muted small">' +
        escapeHtml(BLOCK_LABELS[block.type] || block.type || 'بلوک') +
        '</div>';
    }

    wrap.appendChild(body);
    decorateBlockDrag(wrap, index);
    wrap.addEventListener('click', function (e) {
      stopProp(e);
      toggleBlock(index);
    });
    return wrap;
  }

  function renderCanvas() {
    if (!threadEl) return;
    threadEl.innerHTML = '';
    syncStoreTitle();
    updateBlockCountLabel();
    renderBlocksOutline();

    if (!state.blocks.length) {
      threadEl.innerHTML =
        '<div class="flow-chat-empty flow-canvas-empty">' +
        '<i class="bi bi-layout-text-window-reverse"></i>' +
        '<p>صفحه خالی است. از پنل چپ یک المان اضافه کنید.</p>' +
        '<p class="flow-canvas-empty-hint">بعد از افزودن، المان را بکشید و جابه‌جا کنید</p></div>';
    } else {
      appendDropZone(0);
      state.blocks.forEach(function (block, i) {
        threadEl.appendChild(renderBlockPreview(block, i));
        appendDropZone(i + 1);
      });
    }
    syncHidden();
  }

  function mkDeselectBtn(label) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn btn-panel-ghost btn-sm flow-inspector-deselect mb-3';
    b.innerHTML = '<i class="bi bi-x-lg"></i> ' + (label || 'لغو انتخاب');
    b.addEventListener('click', clearSelection);
    return b;
  }

  function vault() {
    return root && root.parentElement
      ? root.parentElement.querySelector('.miniapp-inspector-vault')
      : document.querySelector('.miniapp-inspector-vault');
  }

  function restoreMovedFields() {
    var staticFields = vault();
    if (!staticFields) return;
    movedFieldNodes.forEach(function (node) {
      staticFields.appendChild(node);
    });
    movedFieldNodes = [];
  }

  function moveFormField(host, staticFields, name, onChange) {
    var el = staticFields.querySelector('[name="' + name + '"]');
    var wrap = el && (el.closest('.mb-3') || el.parentElement);
    if (!wrap) return;
    host.appendChild(wrap);
    movedFieldNodes.push(wrap);
    wrap.querySelectorAll('input, textarea, select').forEach(function (inp) {
      inp.addEventListener('input', onChange);
      inp.addEventListener('change', onChange);
    });
  }

  function fieldLabel(text) {
    var l = document.createElement('label');
    l.className = 'form-label small mb-1';
    l.textContent = text;
    return l;
  }

  function fieldHint(text) {
    var p = document.createElement('p');
    p.className = 'miniapp-field-hint';
    p.textContent = text;
    return p;
  }

  function mkStoryThumbEl(url) {
    if (url) return mkImageThumb(url, 'miniapp-story-thumb');
    var ph = document.createElement('div');
    ph.className = 'miniapp-story-thumb miniapp-story-thumb--empty';
    var ic = document.createElement('i');
    ic.className = 'bi bi-camera';
    ph.appendChild(ic);
    return ph;
  }

  function iconBtn(icon, title, className, onClick) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = className || 'btn btn-panel-ghost btn-sm';
    btn.title = title;
    btn.setAttribute('aria-label', title);
    btn.innerHTML = '<i class="bi bi-' + icon + '"></i>';
    btn.addEventListener('click', onClick);
    return btn;
  }

  function itemPickerSource() {
    return pickerItems.length ? pickerItems : items;
  }

  function categoryPickerSource() {
    return pickerCategories.length ? pickerCategories : categories;
  }

  function itemPickerOptions() {
    var opts = [['', '— یک محصول انتخاب کنید —']];
    itemPickerSource().forEach(function (it) {
      var slug = (it.slug || '').trim();
      var label = (it.title || slug).trim();
      if (slug && label) opts.push([slug, label]);
    });
    return opts;
  }

  function categoryPickerOptions() {
    var opts = [['', '— یک دسته انتخاب کنید —']];
    categoryPickerSource().forEach(function (c) {
      var slug = (c.slug || '').trim();
      var label = (c.name || slug).trim();
      if (slug && label) opts.push([slug, label]);
    });
    return opts;
  }

  function tagPickerOptions() {
    var opts = [['', '— یک برچسب انتخاب کنید —']];
    pickerTags.forEach(function (t) {
      var slug = (t.slug || '').trim();
      var label = (t.name || slug).trim();
      if (slug && label) opts.push([slug, label]);
    });
    return opts;
  }

  function appendItemPickerField(parent, value, onChange, label) {
    parent.appendChild(fieldLabel(label || 'انتخاب محصول'));
    parent.appendChild(
      searchableSelectInput(value || '', itemPickerOptions(), onChange, {
        searchPlaceholder: 'جستجوی نام محصول…',
        listSize: 6,
      })
    );
  }

  function appendCategoryPickerField(parent, value, onChange, label) {
    parent.appendChild(fieldLabel(label || 'انتخاب دسته‌بندی'));
    parent.appendChild(
      searchableSelectInput(value || '', categoryPickerOptions(), onChange, {
        searchPlaceholder: 'جستجوی نام دسته…',
        listSize: 6,
      })
    );
  }

  function appendTagPickerField(parent, value, onChange) {
    parent.appendChild(fieldLabel('انتخاب برچسب'));
    if (!pickerTags.length) {
      parent.appendChild(fieldHint('برچسبی در فروشگاه تعریف نشده است.'));
      parent.appendChild(textInput(value || '', '', 120, onChange));
      return;
    }
    parent.appendChild(
      searchableSelectInput(value || '', tagPickerOptions(), onChange, {
        searchPlaceholder: 'جستجوی برچسب…',
        listSize: 6,
      })
    );
  }

  function multiProductPickerField(selectedSlugs, onChange) {
    if (!selectedSlugs) selectedSlugs = [];
    var wrap = document.createElement('div');
    wrap.className = 'miniapp-multi-product-picker mb-2';

    var selectedWrap = document.createElement('div');
    selectedWrap.className = 'miniapp-multi-product-picker__selected';

    function itemBySlug(slug) {
      var list = itemPickerSource();
      for (var i = 0; i < list.length; i++) {
        if (list[i].slug === slug) return list[i];
      }
      return null;
    }

    function renderSelected() {
      selectedWrap.innerHTML = '';
      if (!selectedSlugs.length) {
        var empty = document.createElement('p');
        empty.className = 'miniapp-field-hint mb-0';
        empty.textContent = 'هنوز محصولی انتخاب نشده';
        selectedWrap.appendChild(empty);
        return;
      }
      selectedSlugs.forEach(function (slug) {
        var it = itemBySlug(slug);
        var chip = document.createElement('div');
        chip.className = 'miniapp-product-chip';
        var label = document.createElement('span');
        label.textContent = it ? it.title : slug;
        chip.appendChild(label);
        chip.appendChild(
          iconBtn('x', 'حذف', 'miniapp-product-chip-remove', function () {
            var next = selectedSlugs.filter(function (s) {
              return s !== slug;
            });
            selectedSlugs = next;
            onChange(next);
            renderSelected();
          })
        );
        selectedWrap.appendChild(chip);
      });
    }

    renderSelected();
    wrap.appendChild(selectedWrap);
    wrap.appendChild(fieldLabel('افزودن محصول'));
    wrap.appendChild(
      searchableSelectInput('', itemPickerOptions(), function (slug) {
        if (!slug || selectedSlugs.indexOf(slug) >= 0) return;
        var next = selectedSlugs.concat([slug]);
        selectedSlugs = next;
        onChange(next);
        renderSelected();
      }, {
        searchPlaceholder: 'جستجو و افزودن محصول…',
        listSize: 5,
      })
    );
    return wrap;
  }

  function appendTargetValueField(parent, target) {
    if (!target || !target.kind) return;
    if (target.kind === 'item') {
      appendItemPickerField(parent, target.value || '', function (v) {
        target.value = v;
        bump();
      });
      return;
    }
    if (target.kind === 'category') {
      appendCategoryPickerField(parent, target.value || '', function (v) {
        target.value = v;
        bump();
      });
      return;
    }
    if (target.kind === 'url') {
      parent.appendChild(fieldLabel('آدرس لینک'));
      parent.appendChild(
        textInput(target.value || '', 'https://example.com', 512, function (v) {
          target.value = v;
          bump();
        })
      );
    }
  }

  function appendStoryTargetFields(parent, target, onKindChange) {
    if (!target) target = { kind: '', value: '' };
    parent.appendChild(fieldLabel('دکمه «مشاهده» (اختیاری)'));
    parent.appendChild(
      selectInput(target.kind || '', [
        ['', 'بدون لینک'],
        ['item', 'محصول'],
        ['category', 'دسته‌بندی'],
        ['flash_sale', 'صفحه حراج'],
        ['home', 'صفحه اصلی'],
        ['url', 'لینک خارجی'],
      ], function (v) {
        target.kind = v;
        if (!v) target.value = '';
        if (onKindChange) onKindChange();
        else bump();
      })
    );
    if (target.kind && target.kind !== 'flash_sale' && target.kind !== 'home') {
      appendTargetValueField(parent, target);
    }
  }

  function textInput(value, placeholder, maxLen, onInput) {
    var inp = document.createElement('input');
    inp.type = 'text';
    inp.className = 'form-control panel-input mb-2';
    inp.value = value || '';
    inp.placeholder = placeholder || '';
    if (maxLen) inp.maxLength = maxLen;
    inp.addEventListener('input', function () {
      onInput(inp.value);
    });
    return inp;
  }

  function textAreaInput(value, placeholder, maxLen, onInput) {
    var ta = document.createElement('textarea');
    ta.className = 'form-control panel-input mb-2';
    ta.rows = 3;
    ta.value = value || '';
    ta.placeholder = placeholder || '';
    if (maxLen) ta.maxLength = maxLen;
    ta.addEventListener('input', function () {
      onInput(ta.value);
    });
    return ta;
  }

  function selectInput(value, options, onChange) {
    var sel = document.createElement('select');
    sel.className = 'form-select panel-input mb-2';
    options.forEach(function (o) {
      var opt = document.createElement('option');
      opt.value = o[0];
      opt.textContent = o[1];
      sel.appendChild(opt);
    });
    sel.value = value;
    sel.addEventListener('change', function () {
      onChange(sel.value);
    });
    return sel;
  }

  function findDiscountCode(id) {
    var pk = parseInt(id, 10);
    if (isNaN(pk)) return null;
    for (var i = 0; i < discountCodes.length; i += 1) {
      if (discountCodes[i].id === pk) return discountCodes[i];
    }
    return null;
  }

  function applyCouponSelection(block, discountId) {
    var dc = findDiscountCode(discountId);
    if (!dc) {
      block.discount_id = null;
      block.code = '';
      return;
    }
    block.discount_id = dc.id;
    block.code = dc.code;
  }

  function appendCouponPicker(host, block, bumpFn) {
    host.appendChild(fieldLabel('کد تخفیف مینی‌اپ'));
    if (!discountCodes.length) {
      var empty = document.createElement('p');
      empty.className = 'small text-muted';
      empty.textContent = 'ابتدا از بخش «کدهای تخفیف» در مینی‌اپ یک کد بسازید.';
      host.appendChild(empty);
      return;
    }
    var options = [['', '— انتخاب کنید —']];
    discountCodes.forEach(function (dc) {
      options.push([String(dc.id), dc.label || dc.code]);
    });
    var selVal = block.discount_id != null ? String(block.discount_id) : '';
    if (!selVal && block.code) {
      discountCodes.forEach(function (dc) {
        if (String(dc.code || '').toUpperCase() === String(block.code || '').toUpperCase()) {
          selVal = String(dc.id);
          block.discount_id = dc.id;
        }
      });
    }
    host.appendChild(
      selectInput(selVal, options, function (v) {
        if (v) applyCouponSelection(block, v);
        else {
          block.discount_id = null;
          block.code = '';
        }
        bumpFn();
      })
    );
    if (block.code) {
      var preview = document.createElement('div');
      preview.className = 'small text-muted mb-2';
      preview.textContent = 'کد انتخاب‌شده: ' + block.code;
      host.appendChild(preview);
    }
  }

  function searchableSelectInput(selectedValue, options, onChange, config) {
    config = config || {};
    var wrap = document.createElement('div');
    wrap.className = 'miniapp-searchable-select mb-2';

    var searchInp = document.createElement('input');
    searchInp.type = 'search';
    searchInp.className = 'form-control panel-input miniapp-searchable-select__search';
    searchInp.placeholder = config.searchPlaceholder || 'جستجوی نام…';
    searchInp.setAttribute('autocomplete', 'off');

    var sel = document.createElement('select');
    sel.className = 'form-select panel-input miniapp-searchable-select__list';
    sel.size = config.listSize || 6;

    function norm(s) {
      return String(s || '').trim().toLowerCase();
    }

    function labelForValue(val) {
      for (var i = 0; i < options.length; i++) {
        if (options[i][0] === val) return options[i][1];
      }
      return '';
    }

    function matchesQuery(val, label, q) {
      if (!q) return true;
      return norm(label).indexOf(q) !== -1 || norm(val).indexOf(q) !== -1;
    }

    function fillOptions(query) {
      var q = norm(query);
      sel.innerHTML = '';
      var count = 0;
      options.forEach(function (pair) {
        var val = pair[0];
        var label = pair[1];
        if (val === '' && q) return;
        if (val !== '' && !matchesQuery(val, label, q)) return;
        var opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        sel.appendChild(opt);
        count++;
      });
      if (!count) {
        var none = document.createElement('option');
        none.value = '';
        none.textContent = 'نتیجه‌ای یافت نشد';
        none.disabled = true;
        sel.appendChild(none);
      } else if (selectedValue) {
        for (var j = 0; j < sel.options.length; j++) {
          if (sel.options[j].value === selectedValue) {
            sel.value = selectedValue;
            break;
          }
        }
      }
    }

    searchInp.addEventListener('input', function () {
      fillOptions(searchInp.value);
    });

    sel.addEventListener('change', function () {
      selectedValue = sel.value;
      onChange(selectedValue);
      searchInp.value = selectedValue ? labelForValue(selectedValue) : '';
    });

    fillOptions('');
    if (selectedValue) {
      searchInp.value = labelForValue(selectedValue);
      sel.value = selectedValue;
    }

    wrap.appendChild(searchInp);
    wrap.appendChild(sel);
    return wrap;
  }

  function mountHeroFields(host, block) {
    var staticFields = vault();
    if (!staticFields) return;
    ['hero_title', 'hero_subtitle', 'logo', 'hero_background'].forEach(function (name) {
      moveFormField(host, staticFields, name, function () {
        renderCanvas();
      });
    });
    host.appendChild(fieldLabel('نوع هیرو'));
    host.appendChild(
      selectInput(
        block.variant || 'banner',
        [
          ['banner', 'بنر بزرگ'],
          ['compact', 'هدر فشرده'],
        ],
        function (v) {
          block.variant = v;
          bump();
        }
      )
    );
  }

  function mountThemeFields(host) {
    var staticFields = vault();
    if (!staticFields) return;
    ['theme_primary', 'theme_accent', 'label_buy_now'].forEach(function (name) {
      moveFormField(host, staticFields, name, renderCanvas);
    });
  }

  function renderBlockSettings(block, host) {
    if (block.type === 'hero') {
      mountHeroFields(host, block);
      return;
    }
    if (block.type === 'search') {
      host.appendChild(fieldLabel('متن placeholder'));
      host.appendChild(
        textInput(block.placeholder, 'جستجو…', 64, function (v) {
          block.placeholder = v;
          bump();
        })
      );
      return;
    }
    if (block.type === 'slider') {
      host.appendChild(fieldLabel('اسلایدها'));
      var list = document.createElement('div');
      list.className = 'miniapp-slide-list';
      function renderSlides() {
        list.innerHTML = '';
        (block.slides || []).forEach(function (slide, si) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item';
          card.appendChild(fieldLabel('اسلاید ' + (si + 1)));
          card.appendChild(
            textInput(slide.title, 'عنوان', 120, function (v) {
              slide.title = v;
              bump();
            })
          );
          card.appendChild(
            textInput(slide.subtitle, 'زیرعنوان', 200, function (v) {
              slide.subtitle = v;
              bump();
            })
          );
          card.appendChild(fieldLabel('تصویر اسلاید'));
          card.appendChild(
            imageUploadField(slide.image_url || '', function (url) {
              slide.image_url = url;
            })
          );
          card.appendChild(
            textInput(slide.image_url, 'یا آدرس تصویر (URL)', 512, function (v) {
              slide.image_url = v;
              bump();
            })
          );
          card.appendChild(
            textInput(slide.link_url, 'لینک (اختیاری)', 512, function (v) {
              slide.link_url = v;
              bump();
            })
          );
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger mb-2';
          rm.textContent = 'حذف اسلاید';
          rm.addEventListener('click', function () {
            block.slides.splice(si, 1);
            if (!block.slides.length) {
              block.slides.push({ title: '', subtitle: '', image_url: '', link_url: '' });
            }
            renderSlides();
            bump();
          });
          card.appendChild(rm);
          list.appendChild(card);
        });
      }
      renderSlides();
      host.appendChild(list);
      var addSlide = document.createElement('button');
      addSlide.type = 'button';
      addSlide.className = 'btn btn-panel-ghost btn-sm';
      addSlide.textContent = '+ اسلاید';
      addSlide.addEventListener('click', function () {
        if (!block.slides) block.slides = [];
        block.slides.push({ title: 'اسلاید جدید', subtitle: '', image_url: '', link_url: '' });
        renderSlides();
        bump();
      });
      host.appendChild(addSlide);
      return;
    }
    if (block.type === 'categories') {
      host.appendChild(fieldLabel('عنوان بخش'));
      host.appendChild(
        textInput(block.title, 'دسته‌بندی‌ها', 80, function (v) {
          block.title = v;
          bump();
        })
      );
      host.appendChild(fieldLabel('ستون‌ها'));
      host.appendChild(
        selectInput(
          String(block.columns || 2),
          [
            ['2', '۲ ستون'],
            ['3', '۳ ستون'],
          ],
          function (v) {
            block.columns = parseInt(v, 10) || 2;
            bump();
          }
        )
      );
      host.appendChild(fieldLabel('حداکثر تعداد'));
      host.appendChild(
        textInput(String(block.limit || 8), '8', 2, function (v) {
          block.limit = parseInt(v, 10) || 8;
          bump();
        })
      );
      return;
    }
    if (block.type === 'featured') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(
        textInput(block.title, 'محصولات ویژه', 80, function (v) {
          block.title = v;
          bump();
        })
      );
      host.appendChild(fieldLabel('تعداد'));
      host.appendChild(
        textInput(String(block.limit || 6), '6', 2, function (v) {
          block.limit = parseInt(v, 10) || 6;
          bump();
        })
      );
      host.appendChild(fieldLabel('چیدمان'));
      host.appendChild(
        selectInput(
          block.layout || 'scroll',
          [
            ['scroll', 'اسکرول افقی'],
            ['grid', 'شبکه'],
          ],
          function (v) {
            block.layout = v;
            bump();
          }
        )
      );
      var note = document.createElement('p');
      note.className = 'small text-muted';
      note.textContent = 'محصولات با برچسب «ویژه» در لیست محصولات نمایش داده می‌شوند.';
      host.appendChild(note);
      return;
    }
    if (block.type === 'products') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(
        textInput(block.title, 'همه محصولات', 80, function (v) {
          block.title = v;
          bump();
        })
      );
      host.appendChild(fieldLabel('چیدمان'));
      host.appendChild(
        selectInput(
          block.layout || 'grid',
          [
            ['grid', 'شبکه‌ای'],
            ['list', 'لیستی'],
          ],
          function (v) {
            block.layout = v;
            bump();
          }
        )
      );
      var staticFields = vault();
      if (staticFields) {
        host.appendChild(fieldLabel('چیدمان پیش‌فرض (تم)'));
        moveFormField(host, staticFields, 'theme_layout', renderCanvas);
      }
      return;
    }
    if (block.type === 'spacer') {
      host.appendChild(fieldLabel('اندازه'));
      host.appendChild(
        selectInput(
          block.size || 'md',
          [
            ['sm', 'کوچک'],
            ['md', 'متوسط'],
            ['lg', 'بزرگ'],
          ],
          function (v) {
            block.size = v;
            bump();
          }
        )
      );
      return;
    }
    if (block.type === 'announcement_bar') {
      host.appendChild(fieldLabel('متن'));
      host.appendChild(textInput(block.text, '', 200, function (v) { block.text = v; bump(); }));
      host.appendChild(fieldLabel('لینک (اختیاری)'));
      host.appendChild(textInput(block.link, '', 512, function (v) { block.link = v; bump(); }));
      host.appendChild(fieldLabel('رنگ پس‌زمینه'));
      host.appendChild(textInput(block.bg, '#111111', 16, function (v) { block.bg = v; bump(); }));
      host.appendChild(fieldLabel('رنگ متن'));
      host.appendChild(textInput(block.color, '#ffffff', 16, function (v) { block.color = v; bump(); }));
      return;
    }
    if (block.type === 'countdown') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      var jalaliParts = window.SepJalaliPicker
        ? window.SepJalaliPicker.isoToJalaliParts(block.ends_at)
        : { date: '', time: '' };
      if (!block._jalali_end_date && jalaliParts.date) block._jalali_end_date = jalaliParts.date;
      if (!block._jalali_end_time && jalaliParts.time) block._jalali_end_time = jalaliParts.time;
      host.appendChild(fieldLabel('تاریخ پایان (شمسی)'));
      var dateWrap = document.createElement('div');
      var dateIn = document.createElement('input');
      dateIn.type = 'text';
      dateIn.className = 'form-control panel-input';
      dateIn.readOnly = true;
      dateIn.setAttribute('data-jalali-date', '1');
      dateIn.placeholder = '۱۴۰۳/۰۸/۱۵';
      dateIn.value = block._jalali_end_date || '';
      dateIn.addEventListener('change', function () {
        block._jalali_end_date = dateIn.value;
        if (window.SepJalaliPicker) {
          block.ends_at = window.SepJalaliPicker.jalaliToIso(
            block._jalali_end_date,
            block._jalali_end_time || '23:59',
          );
        }
        bump();
      });
      dateWrap.appendChild(dateIn);
      host.appendChild(dateWrap);
      host.appendChild(fieldLabel('ساعت پایان'));
      var timeIn = document.createElement('input');
      timeIn.type = 'text';
      timeIn.className = 'form-control panel-input';
      timeIn.setAttribute('data-jalali-time', '1');
      timeIn.placeholder = '۲۳:۵۹';
      timeIn.value = block._jalali_end_time || jalaliParts.time || '23:59';
      timeIn.addEventListener('change', function () {
        block._jalali_end_time = timeIn.value;
        if (window.SepJalaliPicker && block._jalali_end_date) {
          block.ends_at = window.SepJalaliPicker.jalaliToIso(block._jalali_end_date, block._jalali_end_time);
        }
        bump();
      });
      host.appendChild(timeIn);
      if (window.SepJalaliPicker) {
        window.SepJalaliPicker.initDate(dateIn);
        window.SepJalaliPicker.initTime(timeIn);
      }
      host.appendChild(fieldLabel('دکمه CTA'));
      host.appendChild(textInput(block.cta_label, 'مشاهده حراج', 40, function (v) { block.cta_label = v; bump(); }));
      if (!block.cta_target) block.cta_target = { kind: 'flash_sale', value: '' };
      host.appendChild(fieldLabel('مقصد CTA'));
      host.appendChild(
        selectInput(block.cta_target.kind || 'flash_sale', [
          ['flash_sale', 'صفحه حراج'],
          ['category', 'دسته'],
          ['item', 'محصول'],
          ['home', 'صفحه اصلی'],
        ], function (v) {
          block.cta_target.kind = v;
          block.cta_target.value = '';
          bumpInspector();
        })
      );
      if (block.cta_target.kind === 'category' || block.cta_target.kind === 'item') {
        appendTargetValueField(host, block.cta_target);
      }
      host.appendChild(fieldLabel('رنگ'));
      host.appendChild(textInput(block.accent, '#c2402f', 16, function (v) { block.accent = v; bump(); }));
      return;
    }
    if (block.type === 'coupon') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      appendCouponPicker(host, block, bump);
      host.appendChild(fieldLabel('زیرعنوان'));
      host.appendChild(textInput(block.subtitle, '', 120, function (v) { block.subtitle = v; bump(); }));
      return;
    }
    if (block.type === 'product_carousel') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, 'پرفروش‌ترین‌ها', 80, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('منبع'));
      host.appendChild(
        selectInput(block.source || 'featured', [
          ['featured', 'ویژه'],
          ['newest', 'جدیدترین'],
          ['bestselling', 'پرفروش'],
          ['discounted', 'تخفیف‌دار'],
          ['flash_sale', 'حراج'],
          ['category', 'دسته'],
          ['tag', 'برچسب'],
        ], function (v) { block.source = v; bumpInspector(); })
      );
      if (block.source === 'category') {
        appendCategoryPickerField(host, block.category || '', function (v) {
          block.category = v;
          bump();
        });
      }
      if (block.source === 'tag') {
        appendTagPickerField(host, block.tag || '', function (v) {
          block.tag = v;
          bump();
        });
      }
      host.appendChild(fieldLabel('تعداد'));
      host.appendChild(textInput(String(block.limit || 10), '10', 2, function (v) { block.limit = parseInt(v, 10) || 10; bump(); }));
      return;
    }
    if (block.type === 'video') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('ویدیو'));
      host.appendChild(videoUploadField(block.url || '', function (url) { block.url = url; bump(); }));
      host.appendChild(fieldHint('یا آدرس مستقیم وارد کنید (حداکثر ۵۰ مگابایت برای آپلود)'));
      host.appendChild(textInput(block.url, 'https://…', 512, function (v) { block.url = v; bump(); }));
      host.appendChild(fieldLabel('پوستر (اختیاری)'));
      host.appendChild(imageUploadField(block.poster || '', function (url) { block.poster = url; bump(); }));
      return;
    }
    if (block.type === 'info') {
      host.appendChild(fieldLabel('درباره'));
      host.appendChild(textAreaInput(block.about, '', 2000, function (v) { block.about = v; bump(); }));
      host.appendChild(fieldLabel('آدرس'));
      host.appendChild(textInput(block.address, '', 300, function (v) { block.address = v; bump(); }));
      host.appendChild(fieldLabel('ساعت کاری'));
      host.appendChild(textInput(block.hours, '', 120, function (v) { block.hours = v; bump(); }));
      host.appendChild(fieldLabel('تلفن (با کاما)'));
      host.appendChild(textInput((block.phones || []).join(', '), '', 200, function (v) {
        block.phones = v.split(/[,،]/).map(function (s) { return s.trim(); }).filter(Boolean);
        bump();
      }));
      return;
    }
    if (block.type === 'rich_text') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('HTML'));
      host.appendChild(textAreaInput(block.html, '<p>متن</p>', 8000, function (v) { block.html = v; bump(); }));
      return;
    }
    if (block.type === 'story_bar') {
      if (!block.items) block.items = [];
      host.appendChild(
        fieldHint('استوری‌ها در بالای ویترین نمایش داده می‌شوند. هر استوری می‌تواند چند اسلاید داشته باشد.')
      );
      var storyList = document.createElement('div');
      storyList.className = 'miniapp-story-list';

      function renderStories() {
        storyList.innerHTML = '';
        if (!block.items.length) {
          var empty = document.createElement('div');
          empty.className = 'miniapp-story-empty';
          empty.textContent = 'هنوز استوری اضافه نشده — دکمه پایین را بزنید.';
          storyList.appendChild(empty);
          return;
        }
        block.items.forEach(function (story, si) {
          if (!story.slides || !story.slides.length) {
            story.slides = [{ image: story.image || '', duration: 5, target: { kind: '', value: '' } }];
          }
          var card = document.createElement('details');
          card.className = 'miniapp-story-card';
          card.open = si === 0;

          var summary = document.createElement('summary');
          summary.className = 'miniapp-story-card-head';
          summary.appendChild(mkStoryThumbEl(story.image || (story.slides[0] && story.slides[0].image) || ''));

          var headText = document.createElement('div');
          headText.className = 'miniapp-story-card-head-text';
          var titleEl = document.createElement('strong');
          titleEl.className = 'miniapp-story-card-title';
          titleEl.textContent = story.title || 'استوری ' + (si + 1);
          var meta = document.createElement('span');
          meta.className = 'miniapp-story-card-meta';
          meta.textContent = story.slides.length + ' اسلاید';
          headText.appendChild(titleEl);
          headText.appendChild(meta);
          summary.appendChild(headText);

          var headActions = document.createElement('div');
          headActions.className = 'miniapp-story-card-head-actions';
          if (si > 0) {
            headActions.appendChild(
              iconBtn('arrow-up', 'جابجایی به بالا', 'btn btn-panel-ghost btn-sm', function (e) {
                e.preventDefault();
                var tmp = block.items[si];
                block.items[si] = block.items[si - 1];
                block.items[si - 1] = tmp;
                renderStories();
                bump();
              })
            );
          }
          if (si < block.items.length - 1) {
            headActions.appendChild(
              iconBtn('arrow-down', 'جابجایی به پایین', 'btn btn-panel-ghost btn-sm', function (e) {
                e.preventDefault();
                var tmp = block.items[si];
                block.items[si] = block.items[si + 1];
                block.items[si + 1] = tmp;
                renderStories();
                bump();
              })
            );
          }
          headActions.appendChild(
            iconBtn('trash', 'حذف استوری', 'btn btn-panel-ghost btn-sm text-danger', function (e) {
              e.preventDefault();
              if (!window.confirm('این استوری حذف شود؟')) return;
              block.items.splice(si, 1);
              renderStories();
              bump();
            })
          );
          summary.appendChild(headActions);
          card.appendChild(summary);

          var body = document.createElement('div');
          body.className = 'miniapp-story-card-body';

          body.appendChild(fieldLabel('عنوان'));
          body.appendChild(
            textInput(story.title, 'مثلاً تخفیف ویژه', 64, function (v) {
              story.title = v;
              titleEl.textContent = v || 'استوری ' + (si + 1);
              bump();
            })
          );

          body.appendChild(fieldLabel('تصویر کاور (حلقه)'));
          body.appendChild(fieldHint('روی دایره استوری در ویترین دیده می‌شود.'));
          body.appendChild(
            imageUploadField(story.image || '', function (url) {
              story.image = url;
              renderStories();
              bump();
            })
          );

          body.appendChild(fieldLabel('اسلایدها'));
          var slidesWrap = document.createElement('div');
          slidesWrap.className = 'miniapp-story-slides';

          story.slides.forEach(function (slide, slideIdx) {
            if (!slide.target) slide.target = { kind: '', value: '' };
            var slideCard = document.createElement('div');
            slideCard.className = 'miniapp-story-slide';

            var slideTop = document.createElement('div');
            slideTop.className = 'miniapp-story-slide-top';
            slideTop.appendChild(fieldLabel('اسلاید ' + (slideIdx + 1)));
            if (story.slides.length > 1) {
              slideTop.appendChild(
                iconBtn('x-lg', 'حذف اسلاید', 'btn btn-panel-ghost btn-sm text-danger', function () {
                  story.slides.splice(slideIdx, 1);
                  renderStories();
                  bump();
                })
              );
            }
            slideCard.appendChild(slideTop);

            slideCard.appendChild(
              imageUploadField(slide.image || '', function (url) {
                slide.image = url;
                if (!story.image && slideIdx === 0) story.image = url;
                renderStories();
                bump();
              })
            );

            slideCard.appendChild(fieldLabel('متن روی اسلاید (اختیاری)'));
            slideCard.appendChild(
              textInput(slide.text || '', 'توضیح کوتاه', 200, function (v) {
                slide.text = v;
                bump();
              })
            );

            slideCard.appendChild(fieldLabel('مدت نمایش (ثانیه)'));
            slideCard.appendChild(
              textInput(String(slide.duration || 5), '۵', 2, function (v) {
                slide.duration = Math.min(30, Math.max(1, parseInt(v, 10) || 5));
                bump();
              })
            );

            appendStoryTargetFields(slideCard, slide.target, function () {
              renderStories();
              bump();
            });

            slidesWrap.appendChild(slideCard);
          });

          body.appendChild(slidesWrap);

          var addSlide = document.createElement('button');
          addSlide.type = 'button';
          addSlide.className = 'btn btn-panel-ghost btn-sm miniapp-story-add-slide';
          addSlide.innerHTML = '<i class="bi bi-plus-lg me-1"></i>اسلاید جدید';
          addSlide.addEventListener('click', function () {
            story.slides.push({ image: '', duration: 5, target: { kind: '', value: '' } });
            renderStories();
            bump();
          });
          body.appendChild(addSlide);
          card.appendChild(body);
          storyList.appendChild(card);
        });
      }

      renderStories();
      host.appendChild(storyList);

      var addStory = document.createElement('button');
      addStory.type = 'button';
      addStory.className = 'btn btn-panel-primary btn-sm w-100 miniapp-story-add';
      addStory.innerHTML = '<i class="bi bi-plus-circle me-1"></i>افزودن استوری';
      addStory.addEventListener('click', function () {
        block.items.push({
          title: 'استوری جدید',
          image: '',
          slides: [{ image: '', duration: 5, target: { kind: '', value: '' } }],
        });
        renderStories();
        bump();
      });
      host.appendChild(addStory);
      return;
    }
    if (block.type === 'banner_grid') {
      if (!block.items) block.items = [];
      host.appendChild(fieldLabel('ستون‌ها'));
      host.appendChild(
        selectInput(String(block.columns || 2), [['2', '۲'], ['3', '۳'], ['4', '۴']], function (v) {
          block.columns = parseInt(v, 10) || 2;
          bump();
        })
      );
      var bannerList = document.createElement('div');
      function renderBanners() {
        bannerList.innerHTML = '';
        block.items.forEach(function (banner, bi) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item mb-2';
          card.appendChild(fieldLabel('بنر ' + (bi + 1)));
          card.appendChild(imageUploadField(banner.image || '', function (url) { banner.image = url; bump(); }));
          if (!banner.target) banner.target = { kind: 'category', value: '' };
          card.appendChild(fieldLabel('مقصد کلیک'));
          card.appendChild(
            selectInput(banner.target.kind || 'category', [
              ['category', 'دسته‌بندی'],
              ['item', 'محصول'],
            ], function (v) {
              banner.target.kind = v;
              banner.target.value = '';
              renderBanners();
              bump();
            })
          );
          appendTargetValueField(card, banner.target);
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف';
          rm.addEventListener('click', function () {
            block.items.splice(bi, 1);
            renderBanners();
            bump();
          });
          card.appendChild(rm);
          bannerList.appendChild(card);
        });
      }
      renderBanners();
      host.appendChild(bannerList);
      var addBanner = document.createElement('button');
      addBanner.type = 'button';
      addBanner.className = 'btn btn-panel-ghost btn-sm';
      addBanner.textContent = '+ بنر';
      addBanner.addEventListener('click', function () {
        block.items.push({ image: '', target: { kind: 'category', value: '' } });
        renderBanners();
        bump();
      });
      host.appendChild(addBanner);
      return;
    }
    if (block.type === 'faq') {
      if (!block.items) block.items = [];
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, 'سوالات متداول', 80, function (v) { block.title = v; bump(); }));
      var faqList = document.createElement('div');
      function renderFaqItems() {
        faqList.innerHTML = '';
        block.items.forEach(function (item, fi) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item mb-2';
          card.appendChild(textInput(item.q, 'سوال', 200, function (v) { item.q = v; bump(); }));
          card.appendChild(textAreaInput(item.a, 'پاسخ', 1000, function (v) { item.a = v; bump(); }));
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف';
          rm.addEventListener('click', function () {
            block.items.splice(fi, 1);
            renderFaqItems();
            bump();
          });
          card.appendChild(rm);
          faqList.appendChild(card);
        });
      }
      renderFaqItems();
      host.appendChild(faqList);
      var addFaq = document.createElement('button');
      addFaq.type = 'button';
      addFaq.className = 'btn btn-panel-ghost btn-sm';
      addFaq.textContent = '+ سوال';
      addFaq.addEventListener('click', function () {
        block.items.push({ q: '', a: '' });
        renderFaqItems();
        bump();
      });
      host.appendChild(addFaq);
      return;
    }
    if (block.type === 'testimonials') {
      if (!block.items) block.items = [];
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, 'نظر مشتری‌ها', 80, function (v) { block.title = v; bump(); }));
      var testimonialList = document.createElement('div');
      function renderTestimonials() {
        testimonialList.innerHTML = '';
        block.items.forEach(function (item, ti) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item mb-2';
          card.appendChild(fieldLabel('نظر ' + (ti + 1)));
          card.appendChild(textInput(item.name, 'نام', 64, function (v) { item.name = v; bump(); }));
          card.appendChild(textAreaInput(item.text, 'متن نظر', 500, function (v) { item.text = v; bump(); }));
          card.appendChild(fieldLabel('امتیاز (۱–۵)'));
          card.appendChild(
            selectInput(String(item.rating || 5), [['5', '۵'], ['4', '۴'], ['3', '۳'], ['2', '۲'], ['1', '۱']], function (v) {
              item.rating = parseInt(v, 10) || 5;
              bump();
            })
          );
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف';
          rm.addEventListener('click', function () {
            block.items.splice(ti, 1);
            renderTestimonials();
            bump();
          });
          card.appendChild(rm);
          testimonialList.appendChild(card);
        });
      }
      renderTestimonials();
      host.appendChild(testimonialList);
      var addTestimonial = document.createElement('button');
      addTestimonial.type = 'button';
      addTestimonial.className = 'btn btn-panel-ghost btn-sm';
      addTestimonial.textContent = '+ نظر';
      addTestimonial.addEventListener('click', function () {
        block.items.push({ name: '', text: '', rating: 5 });
        renderTestimonials();
        bump();
      });
      host.appendChild(addTestimonial);
      return;
    }
    if (block.type === 'trust_badges') {
      if (!block.items) block.items = [];
      var trustList = document.createElement('div');
      function renderTrust() {
        trustList.innerHTML = '';
        block.items.forEach(function (item, bi) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item mb-2';
          card.appendChild(fieldLabel('نشان ' + (bi + 1)));
          card.appendChild(textInput(item.icon, 'ایموجی', 8, function (v) { item.icon = v; bump(); }));
          card.appendChild(textInput(item.label, 'برچسب', 64, function (v) { item.label = v; bump(); }));
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف';
          rm.addEventListener('click', function () {
            block.items.splice(bi, 1);
            renderTrust();
            bump();
          });
          card.appendChild(rm);
          trustList.appendChild(card);
        });
      }
      renderTrust();
      host.appendChild(trustList);
      var addTrust = document.createElement('button');
      addTrust.type = 'button';
      addTrust.className = 'btn btn-panel-ghost btn-sm';
      addTrust.textContent = '+ نشان';
      addTrust.addEventListener('click', function () {
        block.items.push({ icon: '✅', label: '' });
        renderTrust();
        bump();
      });
      host.appendChild(addTrust);
      return;
    }
    if (block.type === 'bundle') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('برچسب (اختیاری)'));
      host.appendChild(textInput(block.badge, '', 40, function (v) { block.badge = v; bump(); }));
      host.appendChild(fieldLabel('قیمت باندل (تومان)'));
      host.appendChild(textInput(String(tomanFromRial(block.bundle_price || 0)), '0', 12, function (v) { block.bundle_price = rialFromToman(v); bump(); }));
      host.appendChild(fieldLabel('محصولات'));
      host.appendChild(multiProductPickerField(block.item_slugs || [], function (slugs) {
        block.item_slugs = slugs;
        bump();
      }));
      return;
    }
  }

  function renderInspector() {
    if (!inspectorBody) return;
    restoreMovedFields();
    inspectorBody.innerHTML = '';

    if (globalPanel === 'theme') {
      if (inspectorTitle) inspectorTitle.textContent = 'تم کلی';
      if (inspectorHint) inspectorHint.textContent = 'رنگ‌ها و برچسب خرید';
      inspectorBody.appendChild(mkDeselectBtn('بستن'));
      mountThemeFields(inspectorBody);
      return;
    }

    if (selection === null || !state.blocks[selection]) {
      if (inspectorTitle) inspectorTitle.textContent = 'ویژگی‌ها';
      if (inspectorHint) inspectorHint.textContent = 'روی canvas کلیک کنید';
      inspectorBody.innerHTML =
        '<div class="flow-canvas-inspector-empty">' +
        '<i class="bi bi-hand-index"></i>' +
        '<p>یک المان را روی canvas انتخاب کنید تا اینجا ویرایش شود.</p></div>';
      return;
    }

    var block = state.blocks[selection];
    if (inspectorTitle) inspectorTitle.textContent = BLOCK_LABELS[block.type] || block.type;
    if (inspectorHint) {
      inspectorHint.textContent =
        'المان ' + (selection + 1) + ' از ' + state.blocks.length + ' · Escape برای لغو';
    }

    inspectorBody.appendChild(mkDeselectBtn());
    appendInspectorBlockActions(inspectorBody, selection);
    renderBlockSettings(block, inspectorBody);
  }

  function bump() {
    syncHidden();
    renderCanvas();
  }

  function bumpInspector() {
    syncHidden();
    renderCanvas();
    if (selection !== null || globalPanel) renderInspector();
  }

  function addBlock(type) {
    var b = defaultBlock(type);
    if (!b) return;
    var insertAt = state.blocks.length;
    if (selection !== null) insertAt = selection + 1;
    state.blocks.splice(insertAt, 0, b);
    selectBlock(insertAt);
  }

  function moveBlock(delta, fromIndex) {
    var idx = fromIndex != null ? fromIndex : selection;
    if (idx === null || idx === undefined) return;
    var next = idx + delta;
    if (next < 0 || next >= state.blocks.length) return;
    var tmp = state.blocks[idx];
    state.blocks[idx] = state.blocks[next];
    state.blocks[next] = tmp;
    selectBlock(next);
  }

  function bindFormThemeSync() {
    if (!form) return;
    form.querySelectorAll('[name="theme_primary"], [name="theme_accent"], [name="hero_title"], [name="hero_subtitle"], [name="label_buy_now"]').forEach(function (el) {
      el.addEventListener('input', renderCanvas);
    });
  }

  function mount() {
    root = $('miniapp-canvas-editor');
    form = $('miniapp-flow-form');
    threadEl = $('miniapp-canvas-thread');
    hiddenEl = $('id_page_layout');
    inspectorBody = $('miniapp-inspector-body');
    inspectorTitle = $('miniapp-inspector-title');
    inspectorHint = $('miniapp-inspector-hint');
    storeTitleEl = $('miniapp-canvas-store-title');
    paletteEl = $('miniapp-block-palette');
    outlineEl = $('miniapp-blocks-outline');
    blockCountEl = $('miniapp-editor-block-count');
    if (!root || !form || !threadEl) return;

    uploadUrl = root.getAttribute('data-upload-url') || '';
    logoSavedUrl = root.getAttribute('data-logo-url') || '';
    heroBgSavedUrl = root.getAttribute('data-hero-background-url') || '';

    try {
      categories = JSON.parse(root.getAttribute('data-categories') || '[]');
    } catch (e) {
      categories = [];
    }
    try {
      items = JSON.parse(root.getAttribute('data-items') || '[]');
    } catch (e2) {
      items = [];
    }
    try {
      pickerCategories = JSON.parse(root.getAttribute('data-picker-categories') || '[]');
    } catch (e3) {
      pickerCategories = [];
    }
    try {
      pickerItems = JSON.parse(root.getAttribute('data-picker-items') || '[]');
    } catch (e4) {
      pickerItems = [];
    }
    try {
      pickerTags = JSON.parse(root.getAttribute('data-picker-tags') || '[]');
    } catch (e5) {
      pickerTags = [];
    }
    try {
      discountCodes = JSON.parse(root.getAttribute('data-discount-codes') || '[]');
    } catch (e6) {
      discountCodes = [];
    }

    state.blocks = parseInitialBlocks();
    syncHidden();

    renderBlockPalette();

    var themeBtn = root.querySelector('[data-inspector-global="theme"]');
    if (themeBtn) {
      themeBtn.addEventListener('click', function () {
        globalPanel = 'theme';
        selection = null;
        renderCanvas();
        renderInspector();
      });
    }

    bindPointerDragListeners();

    if (threadEl) {
      threadEl.addEventListener('click', function (e) {
        if (e.target.closest('.flow-canvas-block')) return;
        if (e.target.closest('.flow-canvas-drop-zone')) return;
        if (globalPanel) {
          globalPanel = null;
          renderInspector();
          return;
        }
        clearSelection();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && (selection !== null || globalPanel)) clearSelection();
    });

    bindFormThemeSync();
    bindLogoPreview();
    if (form) {
      form.addEventListener('submit', syncHidden);
    }
    renderCanvas();
    renderInspector();
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
