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
  ];

  var state = null;
  var hiddenId = 'id_start_flow';
  var uploadUrl = '';
  var miniAppUrl = '';
  var threadEl = null;
  var inspectorBody = null;
  var inspectorTitle = null;
  var inspectorHint = null;
  var selection = null;

  function $(id) {
    return document.getElementById(id);
  }

  function newNodeId() {
    return 'n_' + Math.random().toString(16).slice(2, 10);
  }

  function defaultButton() {
    return { id: newNodeId(), text: '', label_slug: '', action: null };
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
        var body = String(item.body || '').trim();
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
      var body = String(action.body || '').trim().slice(0, 4096);
      return body ? { type: 'text', body: body } : null;
    }
    if (isMediaType(t)) return normalizeMediaItem(action, t);
    if (t === 'sequence') return normalizeMiniSequence(action);
    if (t === 'url') {
      var url = String(action.url || '').trim().slice(0, 512);
      return url ? { type: 'url', url: url } : null;
    }
    if (t === 'buttons') return normalizeButtons({ type: 'buttons', rows: action.rows }, depth);
    return null;
  }

  function normalizeButton(btn, depth) {
    if (!btn || depth > MAX_DEPTH) return null;
    var text = String(btn.text || '').trim().slice(0, 64);
    var action = btn.action ? normalizeAction(btn.action, depth + 1) : null;
    if (!text && !action) return null;
    var out = {
      id: String(btn.id || newNodeId()).match(/^n_[a-f0-9]{8}$/) ? btn.id : newNodeId(),
      text: text || '…',
    };
    var slug = String(btn.label_slug || '').trim().slice(0, 140);
    if (slug) out.label_slug = slug;
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

  function normalizeSequence(seq, depth) {
    if (!seq || String(seq.type).toLowerCase() !== 'sequence') return defaultSequence();
    var items = [];
    (seq.items || []).forEach(function (item) {
      if (!item) return;
      var t = String(item.type || '').toLowerCase();
      if (t === 'text') {
        var body = String(item.body || '').trim();
        if (body) items.push({ type: 'text', body: body.slice(0, 4096) });
      } else if (isMediaType(t)) {
        var media = normalizeMediaItem(item, t);
        if (media) items.push(media);
      } else if (t === 'buttons') {
        var b = normalizeButtons(item, depth);
        if (b) items.push(b);
      }
    });
    return { type: 'sequence', items: items };
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

  function newContentNode(type) {
    if (type === 'text') return { type: 'text', body: '' };
    if (type === 'buttons') return { type: 'buttons', rows: [[defaultButton()]] };
    if (isMediaType(type)) return defaultMediaItem(type);
    return null;
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
    var toolbar = $('flow-canvas-toolbar');
    if (!toolbar) return;
    var label = toolbar.querySelector('.flow-canvas-editor-toolbar-label');
    if (!label) return;

    if (selection && selection.kind === 'button') {
      var ref = resolveAtPath(selection.path);
      var name = ref && ref.button ? (ref.button.text || '').trim() || 'دکمه' : 'دکمه';
      label.innerHTML =
        '<i class="bi bi-cursor"></i> افزودن به اکشن «' + escapeHtml(name) + '»';
      toolbar.classList.add('is-button-target');
    } else {
      label.innerHTML = '<i class="bi bi-plus-circle"></i> افزودن به جریان';
      toolbar.classList.remove('is-button-target');
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
    updateToolbarContext();
  }

  function toggleSelect(path, kind) {
    if (isSelected(path, kind)) clearSelection();
    else selectPath(path, kind);
  }

  function clearSelection() {
    selection = null;
    renderCanvas();
    renderInspector();
    updateToolbarContext();
  }

  function stopProp(e) {
    e.stopPropagation();
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

  function mkBlockActions(itemIndex) {
    var bar = document.createElement('div');
    bar.className = 'flow-canvas-block-actions';
    bar.addEventListener('click', stopProp);

    if (itemIndex > 0) {
      bar.appendChild(
        mkBtn('up', 'arrow-up', 'جابجایی بالا', function () {
          var items = state.root.items;
          var tmp = items[itemIndex - 1];
          items[itemIndex - 1] = items[itemIndex];
          items[itemIndex] = tmp;
          selectPath([{ kind: 'item', index: itemIndex - 1 }], 'item');
        })
      );
    }
    if (itemIndex < state.root.items.length - 1) {
      bar.appendChild(
        mkBtn('down', 'arrow-down', 'جابجایی پایین', function () {
          var items = state.root.items;
          var tmp = items[itemIndex + 1];
          items[itemIndex + 1] = items[itemIndex];
          items[itemIndex] = tmp;
          selectPath([{ kind: 'item', index: itemIndex + 1 }], 'item');
        })
      );
    }
    bar.appendChild(
      mkBtn('del', 'trash', 'حذف', function () {
        state.root.items.splice(itemIndex, 1);
        clearSelection();
      })
    );
    return bar;
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

    var bubble = document.createElement('div');
    bubble.className = 'flow-chat-bubble flow-chat-bubble--text flow-canvas-editable-bubble';
    bubble.textContent = (item.body || '').trim() || 'متن خالی — برای ویرایش کلیک کنید';
    if (!(item.body || '').trim()) bubble.classList.add('is-placeholder');

    wrap.appendChild(bubble);
    wrap.appendChild(mkBlockActions(itemIndex));
    wrap.addEventListener('click', function () {
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
    wrap.appendChild(mkBlockActions(itemIndex));
    wrap.addEventListener('click', function () {
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

    if (btn.label_slug) {
      var slug = document.createElement('small');
      slug.textContent = btn.label_slug;
      chip.appendChild(slug);
    } else if (btn.action) {
      var hint = document.createElement('small');
      hint.textContent = actionHint(btn.action);
      chip.appendChild(hint);
    }

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
      wrap.addEventListener('click', function (e) {
        if (e.target.closest('.flow-canvas-keyboard-btn')) return;
        toggleSelect(basePath, 'item');
      });
      wrap.appendChild(mkBlockActions(itemIndex));
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

        var label = document.createElement('span');
        label.textContent = (btn.text || '').trim() || 'دکمه جدید';
        chip.appendChild(label);

        if (btn.label_slug) {
          var slug = document.createElement('small');
          slug.textContent = btn.label_slug;
          chip.appendChild(slug);
        } else if (btn.action) {
          var hint = document.createElement('small');
          hint.textContent = actionHint(btn.action);
          chip.appendChild(hint);
        }

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
        '<i class="bi bi-diagram-3"></i>' +
        '<p>جریان خالی است. از نوار بالا متن، رسانه یا دکمه اضافه کنید.</p>';
      threadEl.appendChild(empty);
    }

    state.root.items.forEach(function (item, i) {
      var t = String(item.type || '');
      if (t === 'text') threadEl.appendChild(renderTextBlock(item, i));
      else if (isMediaType(t)) threadEl.appendChild(renderMediaBlock(item, i));
      else if (t === 'buttons') {
        var host = document.createElement('div');
        renderButtonsBlock(item, [{ kind: 'item', index: i }], host, false);
        threadEl.appendChild(host.firstChild);
      }
    });

    syncHidden();
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
      if (inspectorHint) inspectorHint.textContent = 'روی canvas کلیک کنید';
      inspectorBody.innerHTML =
        '<div class="flow-canvas-inspector-empty">' +
        '<i class="bi bi-hand-index"></i>' +
        '<p>یک پیام یا دکمه را روی canvas انتخاب کنید.</p></div>';
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
      if (inspectorTitle) inspectorTitle.textContent = t === 'text' ? 'پیام متنی' : t === 'buttons' ? 'بلوک دکمه' : MEDIA_LABELS[t] || 'آیتم';
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
      }
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
          bump();
        })
      );

      inspectorBody.appendChild(addFieldLabel('برچسب مخاطب (slug) — اختیاری'));
      inspectorBody.appendChild(
        addInput(btn.label_slug || '', 'مثلاً vip-user', 140, function (v) {
          btn.label_slug = v;
          bump();
        })
      );

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
  }

  function mount(root) {
    hiddenId = root.getAttribute('data-hidden-id') || 'id_start_flow';
    uploadUrl = root.getAttribute('data-upload-url') || '';
    miniAppUrl = root.getAttribute('data-mini-app-url') || '';
    threadEl = $('flow-canvas-thread');
    inspectorBody = $('flow-inspector-body');
    inspectorTitle = $('flow-inspector-title');
    inspectorHint = $('flow-inspector-hint');

    state = parseHidden();

    var toolbar = $('flow-canvas-toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('[data-add-type]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          addItem(btn.getAttribute('data-add-type'));
        });
      });
    }

    if (threadEl) {
      threadEl.addEventListener('click', function (e) {
        if (e.target.closest('.flow-canvas-block')) return;
        if (e.target.closest('.flow-canvas-block-actions')) return;
        clearSelection();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && selection) clearSelection();
    });

    renderCanvas();
    renderInspector();
    updateToolbarContext();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('flow-canvas-editor');
    if (root) mount(root);
  });
})();
