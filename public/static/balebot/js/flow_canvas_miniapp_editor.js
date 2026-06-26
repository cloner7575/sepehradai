(function () {
  'use strict';

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
      return { id: id, type: 'coupon', title: 'کد تخفیف', code: 'WELCOME10', subtitle: '', copy_label: 'کپی کد' };
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

  function uploadImage(file, onOk, onErr) {
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

  function imageUploadField(currentUrl, onUploaded) {
    var wrap = document.createElement('div');
    wrap.className = 'miniapp-image-upload mb-2';

    if (currentUrl) {
      var prev = mkImageThumb(currentUrl, 'miniapp-slide-preview-thumb');
      wrap.appendChild(prev);
    }

    var fileInp = document.createElement('input');
    fileInp.type = 'file';
    fileInp.accept = 'image/*';
    fileInp.className = 'visually-hidden';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-panel-ghost btn-sm';
    btn.innerHTML = '<i class="bi bi-cloud-upload me-1"></i>' + (currentUrl ? 'تغییر تصویر' : 'آپلود تصویر');
    btn.addEventListener('click', function () {
      fileInp.click();
    });

    fileInp.addEventListener('change', function () {
      var f = fileInp.files && fileInp.files[0];
      if (!f) return;
      btn.disabled = true;
      btn.textContent = 'در حال آپلود…';
      uploadImage(
        f,
        function (url) {
          onUploaded(url);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-cloud-upload me-1"></i>تغییر تصویر';
          fileInp.value = '';
        },
        function () {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-cloud-upload me-1"></i>آپلود تصویر';
          fileInp.value = '';
        }
      );
    });

    wrap.appendChild(btn);
    wrap.appendChild(fileInp);
    return wrap;
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

  function mkBlockActions(index) {
    var bar = document.createElement('div');
    bar.className = 'flow-canvas-block-actions';
    bar.addEventListener('click', stopProp);

    if (index > 0) {
      bar.appendChild(
        mkBtn('up', 'arrow-up', 'جابجایی بالا', function () {
          moveBlock(-1);
        })
      );
    }
    if (index < state.blocks.length - 1) {
      bar.appendChild(
        mkBtn('down', 'arrow-down', 'جابجایی پایین', function () {
          moveBlock(1);
        })
      );
    }
    bar.appendChild(
      mkBtn('del', 'trash', 'حذف', function () {
        state.blocks.splice(index, 1);
        clearSelection();
      })
    );
    return bar;
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
        price.textContent = Number(block.bundle_price).toLocaleString('fa-IR') + ' ریال';
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
    wrap.appendChild(mkBlockActions(index));
    wrap.addEventListener('click', function (e) {
      if (e.target.closest('.flow-canvas-block-actions')) return;
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
        '<p>صفحه خالی است. از پنل چپ یک المان اضافه کنید.</p></div>';
    } else {
      state.blocks.forEach(function (block, i) {
        threadEl.appendChild(renderBlockPreview(block, i));
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
          bump();
        })
      );
      if (block.cta_target.kind === 'category' || block.cta_target.kind === 'item') {
        host.appendChild(textInput(block.cta_target.value, 'slug', 120, function (v) {
          block.cta_target.value = v;
          bump();
        }));
      }
      host.appendChild(fieldLabel('رنگ'));
      host.appendChild(textInput(block.accent, '#c2402f', 16, function (v) { block.accent = v; bump(); }));
      return;
    }
    if (block.type === 'coupon') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('کد'));
      host.appendChild(textInput(block.code, 'WELCOME10', 40, function (v) { block.code = v; bump(); }));
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
        ], function (v) { block.source = v; bump(); })
      );
      if (block.source === 'category') {
        host.appendChild(fieldLabel('slug دسته'));
        host.appendChild(textInput(block.category, '', 120, function (v) { block.category = v; bump(); }));
      }
      if (block.source === 'tag') {
        host.appendChild(fieldLabel('برچسب'));
        host.appendChild(textInput(block.tag, '', 120, function (v) { block.tag = v; bump(); }));
      }
      host.appendChild(fieldLabel('تعداد'));
      host.appendChild(textInput(String(block.limit || 10), '10', 2, function (v) { block.limit = parseInt(v, 10) || 10; bump(); }));
      return;
    }
    if (block.type === 'video') {
      host.appendChild(fieldLabel('عنوان'));
      host.appendChild(textInput(block.title, '', 120, function (v) { block.title = v; bump(); }));
      host.appendChild(fieldLabel('آدرس ویدیو'));
      host.appendChild(textInput(block.url, '', 512, function (v) { block.url = v; bump(); }));
      host.appendChild(fieldLabel('پوستر'));
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
      host.appendChild(fieldLabel('استوری‌ها'));
      var storyList = document.createElement('div');
      function renderStories() {
        storyList.innerHTML = '';
        block.items.forEach(function (story, si) {
          var card = document.createElement('div');
          card.className = 'miniapp-slide-item mb-2';
          card.appendChild(fieldLabel('استوری ' + (si + 1)));
          card.appendChild(textInput(story.title, 'عنوان', 64, function (v) { story.title = v; bump(); }));
          card.appendChild(fieldLabel('تصویر کاور'));
          card.appendChild(imageUploadField(story.image || '', function (url) { story.image = url; bump(); }));
          if (!story.slides) story.slides = [{ image: story.image || '', duration: 5 }];
          var slidesWrap = document.createElement('div');
          slidesWrap.className = 'ms-2 border-start ps-2';
          story.slides.forEach(function (slide, slideIdx) {
            var slideCard = document.createElement('div');
            slideCard.className = 'mb-2 pb-2 border-bottom';
            slideCard.appendChild(fieldLabel('اسلاید ' + (slideIdx + 1)));
            slideCard.appendChild(imageUploadField(slide.image || '', function (url) {
              slide.image = url;
              bump();
            }));
            slideCard.appendChild(textInput(slide.image, 'URL تصویر', 512, function (v) {
              slide.image = v;
              bump();
            }));
            slideCard.appendChild(textInput(slide.text || '', 'متن (اختیاری)', 200, function (v) {
              slide.text = v;
              bump();
            }));
            slideCard.appendChild(textInput(String(slide.duration || 5), '5', 2, function (v) {
              slide.duration = parseInt(v, 10) || 5;
              bump();
            }));
            if (!slide.target) slide.target = { kind: 'item', value: '' };
            slideCard.appendChild(fieldLabel('لینک (اختیاری)'));
            slideCard.appendChild(
              selectInput(slide.target.kind || 'item', [
                ['item', 'محصول'],
                ['category', 'دسته'],
                ['flash_sale', 'حراج'],
                ['url', 'لینک'],
              ], function (v) {
                slide.target.kind = v;
                bump();
              })
            );
            if (slide.target.kind !== 'flash_sale') {
              slideCard.appendChild(textInput(slide.target.value, 'slug یا URL', 256, function (v) {
                slide.target.value = v;
                bump();
              }));
            }
            var rmSlide = document.createElement('button');
            rmSlide.type = 'button';
            rmSlide.className = 'btn btn-panel-ghost btn-sm text-danger';
            rmSlide.textContent = 'حذف اسلاید';
            rmSlide.addEventListener('click', function () {
              story.slides.splice(slideIdx, 1);
              renderStories();
              bump();
            });
            slideCard.appendChild(rmSlide);
            slidesWrap.appendChild(slideCard);
          });
          var addSlide = document.createElement('button');
          addSlide.type = 'button';
          addSlide.className = 'btn btn-panel-ghost btn-sm mb-2';
          addSlide.textContent = '+ اسلاید';
          addSlide.addEventListener('click', function () {
            story.slides.push({ image: '', duration: 5 });
            renderStories();
            bump();
          });
          card.appendChild(slidesWrap);
          card.appendChild(addSlide);
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn btn-panel-ghost btn-sm text-danger';
          rm.textContent = 'حذف استوری';
          rm.addEventListener('click', function () {
            block.items.splice(si, 1);
            renderStories();
            bump();
          });
          card.appendChild(rm);
          storyList.appendChild(card);
        });
      }
      renderStories();
      host.appendChild(storyList);
      var addStory = document.createElement('button');
      addStory.type = 'button';
      addStory.className = 'btn btn-panel-ghost btn-sm';
      addStory.textContent = '+ استوری';
      addStory.addEventListener('click', function () {
        block.items.push({ title: 'جدید', image: '', slides: [{ image: '', duration: 5 }] });
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
          card.appendChild(
            selectInput(banner.target.kind || 'category', [
              ['category', 'دسته'],
              ['item', 'محصول'],
            ], function (v) { banner.target.kind = v; bump(); })
          );
          card.appendChild(textInput(banner.target.value, 'slug', 120, function (v) { banner.target.value = v; bump(); }));
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
      host.appendChild(fieldLabel('قیمت باندل (ریال)'));
      host.appendChild(textInput(String(block.bundle_price || 0), '0', 12, function (v) { block.bundle_price = parseInt(v, 10) || 0; bump(); }));
      host.appendChild(fieldLabel('slug محصولات (با کاما)'));
      host.appendChild(textInput((block.item_slugs || []).join(', '), '', 500, function (v) {
        block.item_slugs = v.split(/[,،]/).map(function (s) { return s.trim(); }).filter(Boolean);
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
    renderBlockSettings(block, inspectorBody);
  }

  function bump() {
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

    if (threadEl) {
      threadEl.addEventListener('click', function (e) {
        if (e.target.closest('.flow-canvas-block')) return;
        if (e.target.closest('.flow-canvas-block-actions')) return;
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
