(function () {
  function $(id) {
    return document.getElementById(id);
  }

  var MAX_DEPTH = 20;
  var uploadUrl = '';

  function depthClass(d) {
    return 'panel-input-depth-' + Math.min(d, 5);
  }

  function newNodeId() {
    var h = Math.random().toString(16).slice(2, 10);
    return 'n_' + h;
  }

  function defaultButton() {
    return { id: newNodeId(), text: '', label_slug: '', action: null };
  }

  function defaultSequence() {
    return { type: 'sequence', items: [] };
  }

  function emptyFlow() {
    return { version: 2, root: defaultSequence() };
  }

  function actionLabelSuffix(action) {
    if (!action || !action.type) return '';
    var t = action.type;
    if (t === 'url') return ' · 🔗';
    if (t === 'text') return ' · 💬';
    if (t === 'image') return ' · 🖼';
    if (t === 'buttons') return ' · 📂';
    return '';
  }

  function normalizeAction(action, depth) {
    if (!action || depth > MAX_DEPTH) return null;
    var a = action;
    var t = String(a.type || '').toLowerCase();
    if (t === 'text') {
      var body = String(a.body || '').trim().slice(0, 4096);
      return body ? { type: 'text', body: body } : null;
    }
    if (t === 'image') {
      var mid = String(a.media_id || '').trim();
      return mid
        ? {
            type: 'image',
            media_id: mid,
            caption: String(a.caption || '').slice(0, 1024),
          }
        : null;
    }
    if (t === 'url') {
      var url = String(a.url || '').trim().slice(0, 512);
      return url ? { type: 'url', url: url } : null;
    }
    if (t === 'buttons') {
      return normalizeButtons({ type: 'buttons', rows: a.rows }, depth);
    }
    return null;
  }

  function normalizeButton(btn, depth) {
    if (!btn || depth > MAX_DEPTH) return null;
    var text = String(btn.text || '').trim().slice(0, 64);
    var action = btn.action ? normalizeAction(btn.action, depth + 1) : null;
    if (!text && !action) return null;
    var out = {
      id: String(btn.id || newNodeId()).match(/^n_[a-f0-9]{8}$/)
        ? btn.id
        : newNodeId(),
      text: text || '…',
    };
    var slug = String(btn.label_slug || '').trim().slice(0, 140);
    if (slug) out.label_slug = slug;
    if (action) out.action = action;
    return out;
  }

  function normalizeButtons(node, depth) {
    if (!node || depth > MAX_DEPTH) return null;
    var rowsIn = node.rows || [];
    var rowsOut = [];
    rowsIn.forEach(function (row) {
      if (!Array.isArray(row)) return;
      var r = [];
      row.forEach(function (b) {
        var nb = normalizeButton(b, depth);
        if (nb) r.push(nb);
      });
      if (r.length) rowsOut.push(r);
    });
    if (!rowsOut.length) return null;
    return { type: 'buttons', rows: rowsOut };
  }

  function normalizeSequence(seq, depth) {
    if (!seq || String(seq.type).toLowerCase() !== 'sequence') {
      return defaultSequence();
    }
    var items = [];
    (seq.items || []).forEach(function (item) {
      if (!item) return;
      var t = String(item.type || '').toLowerCase();
      if (t === 'text') {
        var body = String(item.body || '').trim();
        if (body) items.push({ type: 'text', body: body.slice(0, 4096) });
      } else if (t === 'image') {
        var mid = String(item.media_id || '').trim();
        if (mid)
          items.push({
            type: 'image',
            media_id: mid,
            caption: String(item.caption || '').slice(0, 1024),
          });
      } else if (t === 'buttons') {
        var b = normalizeButtons(item, depth);
        if (b) items.push(b);
      }
    });
    return { type: 'sequence', items: items };
  }

  function parseHidden(hiddenId) {
    var el = $(hiddenId);
    if (!el || !String(el.value).trim()) return emptyFlow();
    try {
      var data = JSON.parse(el.value);
      if (data && data.version === 2 && data.root) {
        return {
          version: 2,
          root: normalizeSequence(data.root, 0),
        };
      }
    } catch (e) {
      /* ignore */
    }
    return emptyFlow();
  }

  function syncState(state, hiddenId) {
    var el = $(hiddenId);
    if (el) el.value = JSON.stringify(state);
  }

  function uploadImage(file, onOk, onErr) {
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

  function mount(opts) {
    var hiddenId = opts.hiddenId || 'id_start_flow';
    var hostId = opts.hostId || 'flow-builder-host';
    uploadUrl = opts.uploadUrl || '';

    var state = parseHidden(hiddenId);
    var host = $(hostId);
    if (!host) return;

    function doSync() {
      syncState(state, hiddenId);
      updatePreview();
    }

    function updatePreview() {
      var box = $('flow-builder-preview');
      if (!box) return;
      box.innerHTML = '';
      var any = false;

      function appendButtonsPreview(node, title, nestLevel) {
        if (!node || node.type !== 'buttons') return;
        any = true;
        var block = document.createElement('div');
        block.className =
          'flow-preview-block' + (nestLevel > 0 ? ' flow-preview-nested' : '');

        if (title) {
          var ttl = document.createElement('div');
          ttl.className = 'flow-preview-block-title';
          ttl.textContent = title;
          block.appendChild(ttl);
        }

        var rowsHost = document.createElement('div');
        (node.rows || []).forEach(function (row) {
          if (!Array.isArray(row) || !row.length) return;
          var rowEl = document.createElement('div');
          rowEl.className = 'kb-preview-row kb-preview-row-nested';
          var visible = false;
          row.forEach(function (btn) {
            var t = String((btn && btn.text) || '').trim();
            if (!t && !(btn && btn.action)) return;
            visible = true;
            var s = document.createElement('span');
            s.className = 'kb-preview-btn';
            s.textContent = (t || '…') + actionLabelSuffix(btn && btn.action);
            rowEl.appendChild(s);
          });
          if (visible) rowsHost.appendChild(rowEl);
        });

        if (!rowsHost.children.length) {
          var emptyRow = document.createElement('div');
          emptyRow.className = 'text-muted small';
          emptyRow.textContent = 'ردیف خالی';
          rowsHost.appendChild(emptyRow);
        }
        block.appendChild(rowsHost);
        box.appendChild(block);

        (node.rows || []).forEach(function (row, ri) {
          (row || []).forEach(function (btn, bi) {
            if (
              btn &&
              btn.action &&
              btn.action.type === 'buttons' &&
              btn.action.rows
            ) {
              appendButtonsPreview(
                btn.action,
                'زیرمنوی «' + (btn.text || 'دکمه') + '»',
                nestLevel + 1
              );
            }
          });
        });
      }

      (state.root.items || []).forEach(function (item, i) {
        if (item && item.type === 'buttons') {
          appendButtonsPreview(item, 'بلوک دکمه ' + (i + 1), 0);
        }
      });

      if (!any) {
        box.innerHTML =
          '<span class="text-muted small">هنوز بلوک دکمه‌ای اضافه نشده. با «افزودن دکمه‌ها» شروع کنید.</span>';
      }
    }

    function appendImageFields(
      target,
      holder,
      depth,
      getAction,
      setAction,
      onChange
    ) {
      var fileInp = document.createElement('input');
      fileInp.type = 'file';
      fileInp.accept = 'image/*';
      fileInp.className =
        'form-control form-control-sm panel-input ' + depthClass(depth);

      var status = document.createElement('div');
      status.className = 'small text-muted mt-1';

      function refreshStatus() {
        var act = getAction();
        status.textContent =
          act && act.media_id
            ? 'آپلود شده · ' + act.media_id.slice(0, 8) + '…'
            : 'فایلی انتخاب نشده';
      }
      refreshStatus();

      fileInp.addEventListener('change', function () {
        var f = fileInp.files && fileInp.files[0];
        if (!f) return;
        status.textContent = 'در حال آپلود…';
        uploadImage(
          f,
          function (j) {
            var act = getAction() || { type: 'image', media_id: '', caption: '' };
            act.type = 'image';
            act.media_id = j.media_id;
            if (act.caption === undefined) act.caption = '';
            setAction(act);
            refreshStatus();
            onChange();
          },
          function (err) {
            status.textContent = err;
          }
        );
      });

      var cap = document.createElement('textarea');
      cap.className =
        'form-control form-control-sm panel-input ' + depthClass(depth) + ' mt-2';
      cap.rows = 2;
      cap.placeholder = 'کپشن / زیرنویس عکس (اختیاری)';
      cap.maxLength = 1024;
      var act0 = getAction();
      cap.value = (act0 && act0.caption) || '';
      cap.addEventListener('input', function () {
        var act = getAction() || { type: 'image', media_id: '', caption: '' };
        act.type = 'image';
        act.caption = cap.value;
        setAction(act);
        onChange();
      });

      target.appendChild(fileInp);
      target.appendChild(status);
      target.appendChild(cap);
    }

    function renderButtonEditor(btn, depth, onChange) {
      var wrap = document.createElement('div');
      wrap.className =
        'flow-btn-card mb-2 p-2 rounded border border-secondary border-opacity-25 ' +
        depthClass(depth);

      var textLbl = document.createElement('label');
      textLbl.className = 'form-label small mb-1';
      textLbl.textContent = 'متن روی دکمه (در بله)';

      var textInp = document.createElement('input');
      textInp.type = 'text';
      textInp.className = 'form-control form-control-sm panel-input ' + depthClass(depth);
      textInp.placeholder = 'مثلاً ثبت‌نام کلاس';
      textInp.maxLength = 64;
      textInp.value = btn.text || '';
      textInp.addEventListener('input', function () {
        btn.text = textInp.value;
        onChange();
      });

      var slugLbl = document.createElement('label');
      slugLbl.className = 'form-label small mb-1 mt-2';
      slugLbl.textContent = 'لیبل (slug) — اختیاری';

      var slugInp = document.createElement('input');
      slugInp.type = 'text';
      slugInp.className = 'form-control form-control-sm panel-input ' + depthClass(depth);
      slugInp.placeholder = 'مثلاً ai-class';
      slugInp.value = btn.label_slug || '';
      slugInp.addEventListener('input', function () {
        btn.label_slug = slugInp.value;
        onChange();
      });

      var actionLbl = document.createElement('label');
      actionLbl.className = 'form-label small mb-1 mt-2';
      actionLbl.textContent = 'اکشن با کلیک';

      var actionSel = document.createElement('select');
      actionSel.className =
        'form-select form-select-sm panel-input ' + depthClass(depth);
      [
        ['', 'بدون اکشن (بن‌بست → متن پیش‌فرض)'],
        ['text', 'ارسال متن'],
        ['buttons', 'زیرمنو — دکمه‌های بعدی'],
        ['image', 'ارسال عکس'],
        ['url', 'باز کردن لینک'],
      ].forEach(function (o) {
        var opt = document.createElement('option');
        opt.value = o[0];
        opt.textContent = o[1];
        actionSel.appendChild(opt);
      });
      actionSel.value = (btn.action && btn.action.type) || '';

      var extras = document.createElement('div');
      extras.className = 'flow-action-extras mt-2';

      function rebuildExtras() {
        extras.innerHTML = '';
        var t = actionSel.value;
        var prev = btn.action;

        if (t === 'text') {
          var bodyLbl = document.createElement('label');
          bodyLbl.className = 'form-label small mb-1';
          bodyLbl.textContent = 'متن پیام (جدا از برچسب دکمه)';

          var bodyTa = document.createElement('textarea');
          bodyTa.className =
            'form-control form-control-sm panel-input ' + depthClass(depth + 1);
          bodyTa.rows = 3;
          bodyTa.placeholder = 'متنی که پس از کلیک برای کاربر ارسال می‌شود';
          bodyTa.maxLength = 4096;
          bodyTa.value =
            prev && prev.type === 'text' ? prev.body || '' : '';
          bodyTa.addEventListener('input', function () {
            btn.action = { type: 'text', body: bodyTa.value };
            onChange();
          });
          btn.action = { type: 'text', body: bodyTa.value };
          extras.appendChild(bodyLbl);
          extras.appendChild(bodyTa);
        } else if (t === 'url') {
          var urlInp = document.createElement('input');
          urlInp.type = 'url';
          urlInp.className =
            'form-control form-control-sm panel-input ' + depthClass(depth + 1);
          urlInp.placeholder = 'https://...';
          urlInp.value = prev && prev.type === 'url' ? prev.url || '' : '';
          urlInp.addEventListener('input', function () {
            btn.action = { type: 'url', url: urlInp.value };
            onChange();
          });
          btn.action = { type: 'url', url: urlInp.value };
          extras.appendChild(urlInp);
        } else if (t === 'image') {
          var imgLbl = document.createElement('label');
          imgLbl.className = 'form-label small mb-1';
          imgLbl.textContent = 'عکس و کپشن';
          extras.appendChild(imgLbl);

          var mediaId =
            prev && prev.type === 'image' ? prev.media_id || '' : '';
          var caption =
            prev && prev.type === 'image' ? prev.caption || '' : '';
          btn.action = { type: 'image', media_id: mediaId, caption: caption };

          appendImageFields(
            extras,
            btn,
            depth + 1,
            function () {
              return btn.action;
            },
            function (act) {
              btn.action = act;
            },
            onChange
          );
        } else if (t === 'buttons') {
          var sub =
            prev && prev.type === 'buttons'
              ? prev
              : { type: 'buttons', rows: [[defaultButton()]] };
          btn.action = sub;
          renderButtonsNode(btn.action, depth + 1, extras, onChange);
        } else {
          btn.action = null;
        }
        onChange();
      }

      actionSel.addEventListener('change', rebuildExtras);
      wrap.appendChild(textLbl);
      wrap.appendChild(textInp);
      wrap.appendChild(slugLbl);
      wrap.appendChild(slugInp);
      wrap.appendChild(actionLbl);
      wrap.appendChild(actionSel);
      wrap.appendChild(extras);
      rebuildExtras();
      return wrap;
    }

    function renderButtonsNode(node, depth, parentEl, onChange) {
      var box = document.createElement('div');
      box.className =
        'flow-buttons-node ms-2 border-start ps-2 ' + depthClass(depth);
      if (!node.rows || !node.rows.length) node.rows = [[defaultButton()]];

      var miniPreview = document.createElement('div');
      miniPreview.className = 'flow-buttons-inline-preview mb-2 p-2 rounded';
      miniPreview.setAttribute('data-flow-inline-preview', '1');

      function refreshInlinePreview() {
        miniPreview.innerHTML = '';
        var lbl = document.createElement('div');
        lbl.className = 'small text-muted mb-1';
        lbl.textContent = 'همین بلوک — پیش‌نمایش سریع';
        miniPreview.appendChild(lbl);
        var host = document.createElement('div');
        host.className = 'kb-preview-host';
        (node.rows || []).forEach(function (row) {
          if (!Array.isArray(row)) return;
          var rowEl = document.createElement('div');
          rowEl.className = 'kb-preview-row kb-preview-row-nested';
          row.forEach(function (b) {
            var t = String((b && b.text) || '').trim() || '…';
            var s = document.createElement('span');
            s.className = 'kb-preview-btn';
            s.textContent = t + actionLabelSuffix(b && b.action);
            rowEl.appendChild(s);
          });
          if (rowEl.children.length) host.appendChild(rowEl);
        });
        if (!host.children.length) {
          host.innerHTML = '<span class="text-muted small">دکمه‌ای نیست</span>';
        }
        miniPreview.appendChild(host);
      }
      refreshInlinePreview();

      var wrappedOnChange = function () {
        refreshInlinePreview();
        onChange();
      };

      node.rows.forEach(function (row, ri) {
        var rowBox = document.createElement('div');
        rowBox.className = 'mb-2';
        var hint = document.createElement('div');
        hint.className = 'small text-muted mb-1';
        hint.textContent = 'ردیف ' + (ri + 1);
        rowBox.appendChild(hint);

        row.forEach(function (btn, bi) {
          rowBox.appendChild(
            renderButtonEditor(btn, depth, function () {
              node.rows[ri][bi] = btn;
              wrappedOnChange();
            })
          );
        });

        var addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-panel-ghost btn-sm';
        addBtn.textContent = '+ دکمه';
        addBtn.addEventListener('click', function () {
          row.push(defaultButton());
          render();
        });
        rowBox.appendChild(addBtn);

        var rmRow = document.createElement('button');
        rmRow.type = 'button';
        rmRow.className = 'btn btn-panel-ghost btn-sm text-danger ms-1';
        rmRow.textContent = 'حذف ردیف';
        rmRow.addEventListener('click', function () {
          node.rows.splice(ri, 1);
          if (!node.rows.length) node.rows = [[defaultButton()]];
          render();
        });
        rowBox.appendChild(rmRow);
        box.appendChild(rowBox);
      });

      var addRow = document.createElement('button');
      addRow.type = 'button';
      addRow.className = 'btn btn-panel-primary btn-sm';
      addRow.textContent = '+ ردیف دکمه';
      addRow.addEventListener('click', function () {
        node.rows.push([defaultButton()]);
        render();
      });
      box.insertBefore(miniPreview, box.firstChild);
      box.appendChild(addRow);
      parentEl.appendChild(box);
    }

    function renderSequenceItem(item, idx, depth) {
      var card = document.createElement('div');
      card.className = 'flow-item-card panel-card mb-3 ' + depthClass(depth);

      var head = document.createElement('div');
      head.className =
        'panel-card-header py-2 d-flex justify-content-between align-items-center';
      var t = String(item.type || '');
      head.innerHTML =
        '<span class="small fw-semibold">' +
        (t === 'text' ? 'متن' : t === 'image' ? 'عکس' : 'دکمه‌ها') +
        '</span>';

      var rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'btn btn-panel-ghost btn-sm text-danger';
      rm.innerHTML = '<i class="bi bi-trash"></i>';
      rm.addEventListener('click', function () {
        state.root.items.splice(idx, 1);
        render();
      });
      head.appendChild(rm);
      card.appendChild(head);

      var body = document.createElement('div');
      body.className = 'panel-card-body';

      if (t === 'text') {
        var ta = document.createElement('textarea');
        ta.className = 'form-control panel-input ' + depthClass(depth);
        ta.rows = 3;
        ta.value = item.body || '';
        ta.addEventListener('input', function () {
          item.body = ta.value;
          doSync();
        });
        body.appendChild(ta);
      } else if (t === 'image') {
        item.caption = item.caption || '';
        appendImageFields(
          body,
          item,
          depth,
          function () {
            return {
              type: 'image',
              media_id: item.media_id || '',
              caption: item.caption || '',
            };
          },
          function (act) {
            item.media_id = act.media_id;
            item.caption = act.caption || '';
          },
          doSync
        );
      } else if (t === 'buttons') {
        renderButtonsNode(item, depth, body, doSync);
      }

      card.appendChild(body);
      return card;
    }

    function render() {
      host.innerHTML = '';
      var toolbar = document.createElement('div');
      toolbar.className = 'd-flex flex-wrap gap-2 mb-3';
      [
        ['text', 'افزودن متن'],
        ['image', 'افزودن عکس'],
        ['buttons', 'افزودن دکمه‌ها'],
      ].forEach(function (pair) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-panel-ghost btn-sm';
        b.textContent = pair[1];
        b.addEventListener('click', function () {
          if (pair[0] === 'text') {
            state.root.items.push({ type: 'text', body: '' });
          } else if (pair[0] === 'image') {
            state.root.items.push({ type: 'image', media_id: '', caption: '' });
          } else {
            state.root.items.push({
              type: 'buttons',
              rows: [[defaultButton()]],
            });
          }
          render();
        });
        toolbar.appendChild(b);
      });
      host.appendChild(toolbar);

      if (!state.root.items.length) {
        var empty = document.createElement('p');
        empty.className = 'text-muted small';
        empty.textContent =
          'هنوز آیتمی نیست. پس از پیام استارت، آیتم‌های جریان اینجا نمایش داده می‌شوند.';
        host.appendChild(empty);
      }

      state.root.items.forEach(function (item, i) {
        host.appendChild(renderSequenceItem(item, i, 0));
      });
      doSync();
    }

    render();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('flow-builder-root');
    if (!root) return;
    mount({
      hiddenId: root.getAttribute('data-hidden-id') || 'id_start_flow',
      hostId: 'flow-builder-host',
      uploadUrl: root.getAttribute('data-upload-url') || '',
    });
  });
})();
