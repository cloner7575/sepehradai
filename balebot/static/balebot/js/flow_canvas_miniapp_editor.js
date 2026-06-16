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
  };

  var root = null;
  var form = null;
  var threadEl = null;
  var hiddenEl = null;
  var inspectorBody = null;
  var inspectorTitle = null;
  var inspectorHint = null;
  var storeTitleEl = null;
  var categories = [];
  var items = [];
  var state = { blocks: [] };
  var selection = null;
  var globalPanel = null;
  var movedFieldNodes = [];

  function $(id) {
    return document.getElementById(id);
  }

  function newBlockId() {
    return 'b_' + Math.random().toString(16).slice(2, 10);
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

  function syncStoreTitle() {
    if (storeTitleEl) {
      storeTitleEl.textContent = formVal('hero_title') || 'فروشگاه';
    }
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

    var badge = document.createElement('div');
    badge.className = 'flow-canvas-block-badge';
    badge.innerHTML = '<i class="bi bi-grip-vertical"></i> ' + (BLOCK_LABELS[block.type] || block.type);
    wrap.appendChild(badge);

    var body = document.createElement('div');
    body.className = 'flow-canvas-block-body flow-canvas-block-body--miniapp';

    if (block.type === 'hero') {
      var primary = formVal('theme_primary') || '#334155';
      if (block.variant === 'banner') {
        body.innerHTML =
          '<div class="miniapp-preview-hero-banner" style="--hero-primary:' +
          primary +
          '"><strong>' +
          escapeHtml(formVal('hero_title') || 'فروشگاه') +
          '</strong><span>' +
          escapeHtml(formVal('hero_subtitle') || 'زیرعنوان') +
          '</span></div>';
      } else {
        body.innerHTML =
          '<div class="miniapp-preview-hero-compact"><strong>' +
          escapeHtml(formVal('hero_title') || 'فروشگاه') +
          '</strong></div>';
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
        card.className = 'miniapp-preview-slide';
        if (slide.image_url) {
          card.style.backgroundImage = 'url(' + slide.image_url + ')';
        }
        card.innerHTML =
          '<strong>' +
          escapeHtml(slide.title || 'اسلاید ' + (si + 1)) +
          '</strong>' +
          (slide.subtitle ? '<span>' + escapeHtml(slide.subtitle) + '</span>' : '');
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
        grid.innerHTML = '<div class="miniapp-preview-cat">دسته نمونه</div><div class="miniapp-preview-cat">دسته</div>';
      } else {
        cats.forEach(function (c) {
          var cell = document.createElement('div');
          cell.className = 'miniapp-preview-cat';
          cell.textContent = c.name;
          grid.appendChild(cell);
        });
      }
      body.appendChild(grid);
    } else if (block.type === 'featured') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || '') + '</div>';
      var row = document.createElement('div');
      row.className = 'miniapp-preview-products-row';
      var list = featuredItems().slice(0, block.limit || 6);
      if (!list.length) list = items.slice(0, Math.min(block.limit || 4, 4));
      if (!list.length) {
        row.innerHTML = '<div class="miniapp-preview-product-card">★ محصول ویژه</div>';
      } else {
        list.forEach(function (it) {
          var card = document.createElement('div');
          card.className = 'miniapp-preview-product-card';
          card.textContent = it.title;
          row.appendChild(card);
        });
      }
      body.appendChild(row);
    } else if (block.type === 'products') {
      body.innerHTML = '<div class="miniapp-preview-section-title">' + escapeHtml(block.title || '') + '</div>';
      var gridP = document.createElement('div');
      gridP.className =
        'miniapp-preview-products ' +
        (block.layout === 'list' ? 'miniapp-preview-products--list' : 'miniapp-preview-products--grid');
      var prods = items.slice(0, block.limit || 4);
      if (!prods.length) {
        gridP.innerHTML = '<div class="miniapp-preview-product">محصول</div><div class="miniapp-preview-product">محصول</div>';
      } else {
        prods.forEach(function (it) {
          var p = document.createElement('div');
          p.className = 'miniapp-preview-product';
          p.innerHTML = '<strong>' + escapeHtml(it.title) + '</strong>';
          gridP.appendChild(p);
        });
      }
      body.appendChild(gridP);
    } else if (block.type === 'spacer') {
      body.innerHTML = '<div class="miniapp-preview-spacer size-' + (block.size || 'md') + '"></div>';
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

    if (!state.blocks.length) {
      threadEl.innerHTML =
        '<div class="flow-chat-empty flow-canvas-empty">' +
        '<i class="bi bi-layout-text-window-reverse"></i>' +
        '<p>صفحه خالی است. از نوار بالا هیرو، اسلایدر، دسته‌ها یا محصولات اضافه کنید.</p></div>';
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
    ['hero_title', 'hero_subtitle', 'logo'].forEach(function (name) {
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
          card.appendChild(
            textInput(slide.image_url, 'آدرس تصویر (URL)', 512, function (v) {
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

  function moveBlock(delta) {
    if (selection === null) return;
    var next = selection + delta;
    if (next < 0 || next >= state.blocks.length) return;
    var tmp = state.blocks[selection];
    state.blocks[selection] = state.blocks[next];
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
    if (!root || !form || !threadEl) return;

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

    var toolbar = $('miniapp-canvas-toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('[data-add-block]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          addBlock(btn.getAttribute('data-add-block'));
        });
      });
      var themeBtn = toolbar.querySelector('[data-inspector-global="theme"]');
      if (themeBtn) {
        themeBtn.addEventListener('click', function () {
          globalPanel = 'theme';
          selection = null;
          renderCanvas();
          renderInspector();
        });
      }
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
    if (form) {
      form.addEventListener('submit', syncHidden);
    }
    renderCanvas();
    renderInspector();
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
