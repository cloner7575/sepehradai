(function () {
  function $(id) {
    return document.getElementById(id);
  }

  var MAX_SUB_DEPTH = 6;

  function defaultBtn(mode) {
    if (mode === 'start') {
      return {
        text: '',
        action: 'none',
        url: '',
        reply_text: '',
        flow_key: '',
      };
    }
    return { text: '' };
  }

  function emptySubmenuState(mode) {
    return { sections: [{ title: '', rows: [[defaultBtn(mode)]] }] };
  }

  function normalizeBtn(btn, mode) {
    var b = btn && typeof btn === 'object' ? btn : {};
    if (mode === 'start') {
      var act = String(b.action || 'none').trim().toLowerCase();
      if (['none', 'url', 'reply', 'submenu'].indexOf(act) < 0) act = 'none';
      var o = {
        text: String(b.text || '').slice(0, 64),
        action: act,
        url: String(b.url || '').slice(0, 512),
        reply_text: String(b.reply_text || '').slice(0, 3500),
        flow_key: String(b.flow_key || '').slice(0, 64),
      };
      if (act === 'url' && !o.url) o.action = 'none';
      if (act === 'reply' && !o.reply_text) o.action = 'none';
      if (act === 'submenu') {
        o.submenu = normalizeSubmenuState(b.submenu, mode);
      }
      return o;
    }
    return { text: String(b.text || '').slice(0, 64) };
  }

  function normalizeSubmenuState(raw, mode) {
    var base = emptySubmenuState(mode);
    if (!raw || typeof raw !== 'object' || !Array.isArray(raw.sections)) {
      return base;
    }
    base.sections = raw.sections.map(function (sec) {
      if (!sec || typeof sec !== 'object') {
        return { title: '', rows: [[defaultBtn(mode)]] };
      }
      var rows = Array.isArray(sec.rows) ? sec.rows : [];
      if (!rows.length) rows = [[defaultBtn(mode)]];
      return {
        title: String(sec.title || '').slice(0, 120),
        rows: rows.map(function (row) {
          if (!Array.isArray(row) || !row.length) return [defaultBtn(mode)];
          return row.map(function (btn) {
            return normalizeBtn(btn, mode);
          });
        }),
      };
    });
    if (!base.sections.length) base.sections = [{ title: '', rows: [[defaultBtn(mode)]] }];
    return base;
  }

  function parseHidden(hiddenId, mode) {
    var el = $(hiddenId);
    if (!el || !String(el.value).trim()) {
      return defaultState(mode);
    }
    try {
      var data = JSON.parse(el.value);
      if (Array.isArray(data)) {
        return {
          sections: [
            {
              title: '',
              rows: data.length
                ? data.map(function (row) {
                    return (row || []).map(function (btn) {
                      return normalizeBtn(btn, mode);
                    });
                  })
                : [[defaultBtn(mode)]],
            },
          ],
        };
      }
      if (data && Array.isArray(data.sections)) {
        data.sections.forEach(function (sec) {
          (sec.rows || []).forEach(function (row) {
            row.forEach(function (btn, bi) {
              row[bi] = normalizeBtn(btn, mode);
            });
          });
        });
        return data;
      }
      return defaultState(mode);
    } catch (e) {
      return defaultState(mode);
    }
  }

  function defaultState(mode) {
    return { sections: [{ title: '', rows: [[defaultBtn(mode)]] }] };
  }

  function ensureShape(state, mode, opts) {
    opts = opts || {};
    var allowEmptyCampaign =
      mode === 'campaign' &&
      opts.allowEmptyCampaignSections === true &&
      state &&
      Array.isArray(state.sections) &&
      state.sections.length === 0;
    if (allowEmptyCampaign) {
      return { sections: [] };
    }
    if (!state.sections || !state.sections.length) return defaultState(mode);
    state.sections.forEach(function (sec) {
      if (!sec.rows || !sec.rows.length) sec.rows = [[defaultBtn(mode)]];
      sec.rows.forEach(function (row) {
        row.forEach(function (btn, i) {
          row[i] = normalizeBtn(btn, mode);
        });
      });
    });
    return state;
  }

  function sync(state, hiddenId) {
    var el = $(hiddenId);
    if (el) el.value = JSON.stringify(state);
  }

  function flattenRows(state) {
    var out = [];
    (state.sections || []).forEach(function (sec) {
      (sec.rows || []).forEach(function (row) {
        out.push(row);
      });
    });
    return out;
  }

  function rowHasVisibleButton(row) {
    if (!row || !row.length) return false;
    for (var i = 0; i < row.length; i++) {
      var t = row[i] && row[i].text ? String(row[i].text).trim() : '';
      if (t) return true;
    }
    return false;
  }

  function previewStartSection(sec, box, mode, depth) {
    var rows = sec.rows || [];
    var secWrap = document.createElement('div');
    secWrap.className = 'kb-preview-section';
    if (depth > 0) secWrap.className += ' kb-preview-nested';

    var head = document.createElement('div');
    head.className = 'kb-preview-section-head';
    var lvl = document.createElement('span');
    lvl.className = 'kb-preview-level';
    lvl.textContent =
      depth > 0 ? 'زیرمنو · لایه ' + (depth + 1) : 'بلوک';
    head.appendChild(lvl);
    var titleStr = (sec.title || '').trim();
    if (titleStr) {
      var name = document.createElement('span');
      name.className = 'kb-preview-section-name';
      name.textContent = titleStr;
      head.appendChild(name);
    }
    secWrap.appendChild(head);

    var rowsHost = document.createElement('div');
    rowsHost.className = 'kb-preview-section-rows';

    rows.forEach(function (row) {
      if (rowHasVisibleButton(row)) {
        /* anyBtn set outside */
      }

      var rowEl = document.createElement('div');
      rowEl.className = 'kb-preview-row kb-preview-row-nested';
      (row || []).forEach(function (btn) {
        var t = (btn && btn.text) || '';
        var s = document.createElement('span');
        s.className = 'kb-preview-btn';
        var label = String(t).trim() || '…';
        if (mode === 'start' && btn) {
          var a = btn.action || 'none';
          if (a === 'url') label += ' · 🔗';
          else if (a === 'reply') label += ' · 💬';
          else if (a === 'submenu') label += ' · 📂';
        }
        s.textContent = label;
        rowEl.appendChild(s);
      });

      rowsHost.appendChild(rowEl);
    });

    secWrap.appendChild(rowsHost);
    box.appendChild(secWrap);
  }

  function previewStartRecursive(levelObj, box, mode, depth) {
    var secs = levelObj.sections || [];
    secs.forEach(function (sec) {
      previewStartSection(sec, box, mode, depth);
      (sec.rows || []).forEach(function (row) {
        (row || []).forEach(function (btn) {
          if (
            mode === 'start' &&
            btn &&
            btn.action === 'submenu' &&
            btn.submenu &&
            btn.submenu.sections &&
            btn.submenu.sections.length
          ) {
            var inner = document.createElement('div');
            inner.className = 'kb-preview-submenu ms-3 border-start ps-2 mt-1';
            previewStartRecursive(btn.submenu, inner, mode, depth + 1);
            box.appendChild(inner);
          }
        });
      });
    });
  }

  function preview(state, mode, previewInnerId) {
    var box = $(previewInnerId || 'kb-preview-inner');
    if (!box) return;
    box.innerHTML = '';
    var secs = state.sections || [];
    if (!secs.length) {
      box.innerHTML =
        '<span class="text-muted small">هنوز دکمه‌ای نیست.</span>';
      return;
    }

    if (mode === 'start') {
      var anyBtn = false;
      secs.forEach(function (sec) {
        (sec.rows || []).forEach(function (row) {
          if (rowHasVisibleButton(row)) anyBtn = true;
        });
      });
      if (!anyBtn) {
        box.innerHTML =
          '<span class="text-muted small">هنوز دکمه‌ای با متن پر نشده.</span>';
        return;
      }
      previewStartRecursive(state, box, mode, 0);
      return;
    }

    var anyBtn = false;
    secs.forEach(function (sec, si) {
      var rows = sec.rows || [];
      var secWrap = document.createElement('div');
      secWrap.className = 'kb-preview-section';

      var head = document.createElement('div');
      head.className = 'kb-preview-section-head';
      var lvl = document.createElement('span');
      lvl.className = 'kb-preview-level';
      lvl.textContent = 'بلوک ' + (si + 1);
      head.appendChild(lvl);
      var titleStr = (sec.title || '').trim();
      if (titleStr) {
        var name = document.createElement('span');
        name.className = 'kb-preview-section-name';
        name.textContent = titleStr;
        head.appendChild(name);
      }
      secWrap.appendChild(head);

      var rowsHost = document.createElement('div');
      rowsHost.className = 'kb-preview-section-rows';

      rows.forEach(function (row, ri) {
        if (rowHasVisibleButton(row)) anyBtn = true;

        var rowMeta = document.createElement('div');
        rowMeta.className = 'kb-preview-row-meta';
        rowMeta.textContent =
          '└ ردیف ' + (ri + 1) + ' — دکمه‌ها در یک خط کنار هم';

        var rowEl = document.createElement('div');
        rowEl.className = 'kb-preview-row kb-preview-row-nested';
        (row || []).forEach(function (btn) {
          var t = (btn && btn.text) || '';
          var s = document.createElement('span');
          s.className = 'kb-preview-btn';
          var label = String(t).trim() || '…';
          s.textContent = label;
          rowEl.appendChild(s);
        });

        rowsHost.appendChild(rowMeta);
        rowsHost.appendChild(rowEl);
      });

      secWrap.appendChild(rowsHost);
      box.appendChild(secWrap);
    });

    if (!anyBtn) {
      box.innerHTML =
        '<span class="text-muted small">هنوز دکمه‌ای با متن پر نشده؛ هر بلوک چند ردیف و هر ردیف چند دکمه می‌تواند داشته باشد.</span>';
    }
  }

  function mount(root, opts) {
    var mode = opts.mode || 'campaign';
    var hiddenId = opts.hiddenId || 'id_inline_keyboard';
    var previewInnerId = opts.previewInnerId || 'kb-preview-inner';
    var sectionsHostId = opts.sectionsHostId || 'kb-sections';

    var state = ensureShape(parseHidden(hiddenId, mode), mode, opts);

    function expandCollapsiblePanel() {
      if (!opts.collapsiblePanelId) return;
      var panel = $(opts.collapsiblePanelId);
      if (panel && panel.classList.contains('d-none')) {
        panel.classList.remove('d-none');
      }
    }

    function doSync() {
      sync(state, hiddenId);
      preview(state, mode, previewInnerId);
    }

    function commitBtn(si, ri, bi, patch) {
      var cur = state.sections[si].rows[ri][bi];
      var merged;
      if (mode === 'start') {
        merged = Object.assign({}, normalizeBtn(cur, mode), patch);
        merged.text = String(merged.text || '').slice(0, 64);
        merged.action = merged.action || 'none';
        merged.url = String(merged.url || '').slice(0, 512);
        merged.reply_text = String(merged.reply_text || '').slice(0, 3500);
        merged.flow_key = String(merged.flow_key || '').slice(0, 64);
        if (merged.action === 'submenu') {
          if (!merged.submenu) merged.submenu = emptySubmenuState(mode);
          else merged.submenu = normalizeSubmenuState(merged.submenu, mode);
        } else {
          delete merged.submenu;
        }
        state.sections[si].rows[ri][bi] = merged;
      } else {
        merged = {
          text: String(
            (patch && patch.text) !== undefined
              ? patch.text
              : (cur && cur.text) || '',
          ).slice(0, 64),
        };
        state.sections[si].rows[ri][bi] = merged;
      }
      doSync();
    }

    function commitBtnInLevel(levelObj, si, ri, bi, patch) {
      var cur = levelObj.sections[si].rows[ri][bi];
      var merged = Object.assign({}, normalizeBtn(cur, mode), patch);
      merged.text = String(merged.text || '').slice(0, 64);
      merged.action = merged.action || 'none';
      merged.url = String(merged.url || '').slice(0, 512);
      merged.reply_text = String(merged.reply_text || '').slice(0, 3500);
      merged.flow_key = String(merged.flow_key || '').slice(0, 64);
      if (merged.action === 'submenu') {
        if (!merged.submenu) merged.submenu = emptySubmenuState(mode);
        else merged.submenu = normalizeSubmenuState(merged.submenu, mode);
      } else {
        delete merged.submenu;
      }
      levelObj.sections[si].rows[ri][bi] = merged;
      doSync();
      render();
    }

    function renderStartLevel(levelObj, hostEl, depth) {
      if (depth > MAX_SUB_DEPTH) return;
      if (!levelObj.sections || !levelObj.sections.length) {
        levelObj.sections = [{ title: '', rows: [[defaultBtn(mode)]] }];
      }

      levelObj.sections.forEach(function (sec, si) {
        var card = document.createElement('div');
        card.className = 'kb-section kb-section-tree panel-card mb-4';
        if (depth > 0) card.className += ' kb-section-submenu';

        var head = document.createElement('div');
        head.className =
          'panel-card-header flex-wrap gap-2 align-items-center kb-section-head';

        var badge = document.createElement('span');
        badge.className = 'badge kb-section-badge rounded-pill';
        badge.textContent =
          depth === 0
            ? 'سطح ۱ · بلوک ' + (si + 1)
            : 'زیرمنو · بلوک ' + (si + 1);

        var titleInp = document.createElement('input');
        titleInp.type = 'text';
        titleInp.className =
          'form-control panel-input kb-section-title flex-grow-1';
        titleInp.placeholder =
          'عنوان گروه (اختیاری — فقط برای نظم دیدن در پنل)';
        titleInp.value = sec.title || '';
        titleInp.addEventListener('input', function () {
          levelObj.sections[si].title = titleInp.value;
          doSync();
        });

        var rmSec = document.createElement('button');
        rmSec.type = 'button';
        rmSec.className = 'btn btn-panel-ghost btn-sm';
        rmSec.innerHTML = '<i class="bi bi-trash"></i>';
        rmSec.title = 'حذف بلوک';
        rmSec.addEventListener('click', function () {
          levelObj.sections.splice(si, 1);
          if (!levelObj.sections.length) {
            levelObj.sections = [{ title: '', rows: [[defaultBtn(mode)]] }];
          }
          render();
          doSync();
        });

        head.appendChild(badge);
        head.appendChild(titleInp);
        head.appendChild(rmSec);

        var body = document.createElement('div');
        body.className = 'panel-card-body kb-section-nested-body';

        (sec.rows || []).forEach(function (row, ri) {
          var rowBox = document.createElement('div');
          rowBox.className = 'kb-row kb-row-nested mb-3 p-3 rounded';

          var hint = document.createElement('div');
          hint.className = 'small text-muted mb-2 kb-row-hint';
          hint.innerHTML =
            '<span class="kb-row-level">ردیف ' +
            (ri + 1) +
            (depth > 0 ? ' · زیرمنو' : '') +
            '</span> — در بله در یک خط کنار هم';

          var flex = document.createElement('div');
          flex.className = 'd-flex flex-wrap gap-2 align-items-start';

          row.forEach(function (btn, bi) {
            var wrap = document.createElement('div');
            wrap.className = 'kb-btn-stack flex-grow-1';

            var inner = document.createElement('div');
            inner.className = 'w-100';
            var rowInp = document.createElement('div');
            rowInp.className = 'input-group input-group-sm mb-2';

            var inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'form-control panel-input';
            inp.placeholder = 'متن دکمه';
            inp.maxLength = 64;
            inp.value = (btn && btn.text) || '';
            inp.addEventListener('input', function () {
              commitBtnInLevel(levelObj, si, ri, bi, { text: inp.value });
            });

            var rm = document.createElement('button');
            rm.type = 'button';
            rm.className = 'btn btn-outline-danger';
            rm.innerHTML = '<i class="bi bi-x-lg"></i>';
            rm.addEventListener('click', function () {
              levelObj.sections[si].rows[ri].splice(bi, 1);
              if (!levelObj.sections[si].rows[ri].length) {
                levelObj.sections[si].rows.splice(ri, 1);
              }
              if (!levelObj.sections[si].rows.length) {
                levelObj.sections[si].rows = [[defaultBtn(mode)]];
              }
              render();
              doSync();
            });

            rowInp.appendChild(inp);
            rowInp.appendChild(rm);
            inner.appendChild(rowInp);

            var actionSel = document.createElement('select');
            actionSel.className =
              'form-select form-select-sm panel-input mb-2 kb-action-select';
            [
              ['none', 'فقط تأیید (اعلان کوتاه)'],
              ['url', 'باز کردن لینک'],
              ['reply', 'ارسال متن به کاربر'],
              ['submenu', 'نمایش زیرمنو (دکمه‌های بعدی)'],
            ].forEach(function (opt) {
              var o = document.createElement('option');
              o.value = opt[0];
              o.textContent = opt[1];
              actionSel.appendChild(o);
            });
            actionSel.value = (btn && btn.action) || 'none';

            var flowInp = document.createElement('input');
            flowInp.type = 'text';
            flowInp.className =
              'form-control form-control-sm panel-input mb-2 kb-flow-key-field';
            flowInp.placeholder = 'کلید فرم (flow_key) — ذخیرهٔ انتخاب';
            flowInp.maxLength = 64;
            flowInp.value = (btn && btn.flow_key) || '';
            flowInp.addEventListener('input', function () {
              commitBtnInLevel(levelObj, si, ri, bi, { flow_key: flowInp.value });
            });

            var urlInp = document.createElement('input');
            urlInp.type = 'url';
            urlInp.className =
              'form-control form-control-sm panel-input mb-2 kb-url-field';
            urlInp.placeholder = 'https://...';
            urlInp.value = (btn && btn.url) || '';

            var replyTa = document.createElement('textarea');
            replyTa.className =
              'form-control form-control-sm panel-input kb-reply-field';
            replyTa.rows = 2;
            replyTa.placeholder = 'متنی که با کلیک برای کاربر فرستاده می‌شود';
            replyTa.value = (btn && btn.reply_text) || '';

            function readDeps() {
              return {
                action: actionSel.value,
                url: urlInp.value,
                reply_text: replyTa.value,
                flow_key: flowInp.value,
              };
            }

            function toggleExtras() {
              var a = actionSel.value;
              urlInp.style.display = a === 'url' ? 'block' : 'none';
              replyTa.style.display = a === 'reply' ? 'block' : 'none';
            }

            actionSel.addEventListener('change', function () {
              commitBtnInLevel(levelObj, si, ri, bi, readDeps());
              toggleExtras();
            });
            urlInp.addEventListener('input', function () {
              commitBtnInLevel(levelObj, si, ri, bi, readDeps());
            });
            replyTa.addEventListener('input', function () {
              commitBtnInLevel(levelObj, si, ri, bi, readDeps());
            });

            inner.appendChild(actionSel);
            inner.appendChild(flowInp);
            inner.appendChild(urlInp);
            inner.appendChild(replyTa);
            toggleExtras();
            wrap.appendChild(inner);

            var sm = btn && btn.submenu;
            var showSub =
              (btn && btn.action === 'submenu') ||
              (sm &&
                sm.sections &&
                sm.sections.length &&
                depth < MAX_SUB_DEPTH);
            if (showSub && depth < MAX_SUB_DEPTH) {
              if (!btn.submenu) btn.submenu = emptySubmenuState(mode);
              var subWrap = document.createElement('div');
              subWrap.className =
                'kb-submenu-editor mt-3 p-2 rounded border border-secondary border-opacity-25';
              var subLabel = document.createElement('div');
              subLabel.className = 'small fw-semibold mb-2 text-muted';
              subLabel.textContent = 'محتوای زیرمنو (بعد از کلیک روی این دکمه)';
              subWrap.appendChild(subLabel);
              renderStartLevel(btn.submenu, subWrap, depth + 1);
              wrap.appendChild(subWrap);
            }

            flex.appendChild(wrap);
          });

          var addBtn = document.createElement('button');
          addBtn.type = 'button';
          addBtn.className = 'btn btn-panel-ghost btn-sm align-self-center';
          addBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
          addBtn.title = 'افزودن دکمه به همین ردیف';
          addBtn.addEventListener('click', function () {
            levelObj.sections[si].rows[ri].push(defaultBtn(mode));
            render();
            doSync();
          });
          flex.appendChild(addBtn);

          var rmRow = document.createElement('button');
          rmRow.type = 'button';
          rmRow.className = 'btn btn-panel-ghost btn-sm text-danger mt-2';
          rmRow.innerHTML = '<i class="bi bi-dash-lg"></i> حذف ردیف';
          rmRow.addEventListener('click', function () {
            levelObj.sections[si].rows.splice(ri, 1);
            if (!levelObj.sections[si].rows.length) {
              levelObj.sections[si].rows = [[defaultBtn(mode)]];
            }
            render();
            doSync();
          });

          rowBox.appendChild(hint);
          rowBox.appendChild(flex);
          rowBox.appendChild(rmRow);
          body.appendChild(rowBox);
        });

        var addRow = document.createElement('button');
        addRow.type = 'button';
        addRow.className = 'btn btn-panel-primary btn-sm';
        addRow.innerHTML =
          '<i class="bi bi-layout-text-sidebar-reverse me-1"></i> ردیف دیگر در این بلوک';
        addRow.addEventListener('click', function () {
          levelObj.sections[si].rows.push([defaultBtn(mode)]);
          render();
          doSync();
        });
        body.appendChild(addRow);

        card.appendChild(head);
        card.appendChild(body);
        hostEl.appendChild(card);
      });

      if (depth > 0) {
        var addSec = document.createElement('button');
        addSec.type = 'button';
        addSec.className = 'btn btn-panel-ghost btn-sm';
        addSec.innerHTML =
          '<i class="bi bi-columns-gap me-1"></i> افزودن بلوک در این سطح';
        addSec.addEventListener('click', function () {
          levelObj.sections.push({ title: '', rows: [[defaultBtn(mode)]] });
          render();
          doSync();
        });
        hostEl.appendChild(addSec);
      }
    }

    function render() {
      state = ensureShape(state, mode, opts);
      var host = $(sectionsHostId);
      if (!host) return;
      host.innerHTML = '';

      if (mode === 'start') {
        renderStartLevel(state, host, 0);
        doSync();
        return;
      }

      if (mode === 'campaign' && (!state.sections || !state.sections.length)) {
        doSync();
        return;
      }

      state.sections.forEach(function (sec, si) {
        var card = document.createElement('div');
        card.className = 'kb-section kb-section-tree panel-card mb-4';

        var head = document.createElement('div');
        head.className =
          'panel-card-header flex-wrap gap-2 align-items-center kb-section-head';

        var badge = document.createElement('span');
        badge.className = 'badge kb-section-badge rounded-pill';
        badge.textContent = 'سطح ۱ · بلوک ' + (si + 1);

        var titleInp = document.createElement('input');
        titleInp.type = 'text';
        titleInp.className =
          'form-control panel-input kb-section-title flex-grow-1';
        titleInp.placeholder =
          'عنوان گروه (اختیاری — فقط برای نظم دیدن در پنل)';
        titleInp.value = sec.title || '';
        titleInp.addEventListener('input', function () {
          state.sections[si].title = titleInp.value;
          doSync();
        });

        var rmSec = document.createElement('button');
        rmSec.type = 'button';
        rmSec.className = 'btn btn-panel-ghost btn-sm';
        rmSec.innerHTML = '<i class="bi bi-trash"></i>';
        rmSec.title = 'حذف بلوک';
        rmSec.addEventListener('click', function () {
          state.sections.splice(si, 1);
          if (!state.sections.length) {
            state =
              mode === 'campaign' && opts.allowEmptyCampaignSections
                ? { sections: [] }
                : defaultState(mode);
          }
          render();
          doSync();
        });

        head.appendChild(badge);
        head.appendChild(titleInp);
        head.appendChild(rmSec);

        var body = document.createElement('div');
        body.className = 'panel-card-body kb-section-nested-body';

        (sec.rows || []).forEach(function (row, ri) {
          var rowBox = document.createElement('div');
          rowBox.className = 'kb-row kb-row-nested mb-3 p-3 rounded';

          var hint = document.createElement('div');
          hint.className = 'small text-muted mb-2 kb-row-hint';
          hint.innerHTML =
            '<span class="kb-row-level">سطح ۲ · ردیف ' +
            (ri + 1) +
            '</span> — چند دکمه زیر هم در همین بلوک؛ در بله در یک خط کنار هم دیده می‌شوند';

          var flex = document.createElement('div');
          flex.className = 'd-flex flex-wrap gap-2 align-items-start';

          row.forEach(function (btn, bi) {
            var wrap = document.createElement('div');
            wrap.className = 'input-group input-group-sm kb-btn-group';

            var inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'form-control panel-input';
            inp.placeholder = 'متن دکمه';
            inp.maxLength = 64;
            inp.value = (btn && btn.text) || '';
            inp.addEventListener('input', function () {
              commitBtn(si, ri, bi, { text: inp.value });
            });

            var rm = document.createElement('button');
            rm.type = 'button';
            rm.className = 'btn btn-outline-danger';
            rm.innerHTML = '<i class="bi bi-x-lg"></i>';
            rm.addEventListener('click', function () {
              state.sections[si].rows[ri].splice(bi, 1);
              if (!state.sections[si].rows[ri].length) {
                state.sections[si].rows.splice(ri, 1);
              }
              if (!state.sections[si].rows.length) {
                state.sections[si].rows = [[defaultBtn(mode)]];
              }
              render();
              doSync();
            });

            wrap.appendChild(inp);
            wrap.appendChild(rm);
            flex.appendChild(wrap);
          });

          var addBtn = document.createElement('button');
          addBtn.type = 'button';
          addBtn.className = 'btn btn-panel-ghost btn-sm align-self-center';
          addBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
          addBtn.title = 'افزودن دکمه به همین ردیف';
          addBtn.addEventListener('click', function () {
            state.sections[si].rows[ri].push(defaultBtn(mode));
            render();
            doSync();
          });
          flex.appendChild(addBtn);

          var rmRow = document.createElement('button');
          rmRow.type = 'button';
          rmRow.className = 'btn btn-panel-ghost btn-sm text-danger mt-2';
          rmRow.innerHTML = '<i class="bi bi-dash-lg"></i> حذف ردیف';
          rmRow.addEventListener('click', function () {
            state.sections[si].rows.splice(ri, 1);
            if (!state.sections[si].rows.length) {
              state.sections[si].rows = [[defaultBtn(mode)]];
            }
            render();
            doSync();
          });

          rowBox.appendChild(hint);
          rowBox.appendChild(flex);
          rowBox.appendChild(rmRow);
          body.appendChild(rowBox);
        });

        var addRow = document.createElement('button');
        addRow.type = 'button';
        addRow.className = 'btn btn-panel-primary btn-sm';
        addRow.innerHTML =
          '<i class="bi bi-layout-text-sidebar-reverse me-1"></i> ردیف دیگر در این بلوک';
        addRow.addEventListener('click', function () {
          state.sections[si].rows.push([defaultBtn(mode)]);
          render();
          doSync();
        });
        body.appendChild(addRow);

        card.appendChild(head);
        card.appendChild(body);
        host.appendChild(card);
      });

      doSync();
    }

    var addSecBtn = $(opts.addSectionBtnId || 'kb-add-section');
    if (addSecBtn) {
      addSecBtn.addEventListener('click', function () {
        expandCollapsiblePanel();
        if (mode === 'start') {
          state.sections.push({ title: '', rows: [[defaultBtn(mode)]] });
          render();
        } else {
          state.sections.push({ title: '', rows: [[defaultBtn(mode)]] });
          render();
        }
      });
    }

    var form = root.closest('form');
    if (form) {
      form.addEventListener('submit', function () {
        doSync();
      });
    }

    var collapsedInitially =
      mode === 'campaign' &&
      opts.collapsiblePanelId &&
      opts.allowEmptyCampaignSections === true &&
      !opts.startExpanded;

    if (collapsedInitially) {
      doSync();
    } else {
      render();
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var campaignRoot = $('keyboard-builder-root');
    if (campaignRoot) {
      mount(campaignRoot, {
        mode: 'campaign',
        hiddenId: 'id_inline_keyboard',
        sectionsHostId: 'kb-sections',
        previewInnerId: 'kb-preview-inner',
        addSectionBtnId: 'kb-add-section',
        allowEmptyCampaignSections: true,
        collapsiblePanelId: 'kb-builder-collapsible',
        startExpanded:
          campaignRoot.getAttribute('data-keyboard-expanded') === 'true',
      });
    }
    var startRoot = $('keyboard-builder-root-start');
    if (startRoot) {
      mount(startRoot, {
        mode: 'start',
        hiddenId: 'id_start_inline_keyboard',
        sectionsHostId: 'kb-sections-start',
        previewInnerId: 'kb-preview-inner-start',
        addSectionBtnId: 'kb-add-section-start',
      });
    }
  });
})();
