(function () {
  var TAB_HASH = {
    'sec-basics': 'basics',
    'sec-commerce': 'commerce',
    'sec-media': 'media',
    'sec-publish': 'publish',
  };

  var WIZARD_STEP_LABELS = {
    basics: 'اطلاعات',
    commerce: 'قیمت',
    media: 'رسانه',
    publish: 'انتشار',
  };

  var TYPE_GUIDES = {};
  var SALE_MODE_LABELS = {};
  var wizardApi = null;

  function loadTypeGuides() {
    var el = document.getElementById('item-type-guides-data');
    if (!el) return;
    try {
      TYPE_GUIDES = JSON.parse(el.textContent || '{}');
    } catch (e) {
      TYPE_GUIDES = {};
    }
  }

  function isWizardMode() {
    var form = document.getElementById('catalog-item-form');
    return form && form.getAttribute('data-item-wizard') === '1';
  }

  function currentType() {
    var select = document.getElementById('id_item_type');
    if (!select) return 'product';
    if (select.value === 'portfolio') return 'showcase';
    return select.value;
  }

  function getGuide(type) {
    return TYPE_GUIDES[type] || TYPE_GUIDES.product || {};
  }

  function getWizardSteps() {
    var guide = getGuide(currentType());
    if (guide.show_commerce) {
      return ['basics', 'commerce', 'media', 'publish'];
    }
    return ['basics', 'media', 'publish'];
  }

  function slugifyTitle(raw) {
    return String(raw || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^\w\u0600-\u06FF-]+/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 80);
  }

  function setBlockVisible(block, show) {
    if (!block) return;
    block.classList.toggle('settings-block-hidden', !show);
    block.setAttribute('aria-hidden', show ? 'false' : 'true');
  }

  function readSelectLabels(selectId, target) {
    var select = document.getElementById(selectId);
    if (!select) return;
    Array.prototype.slice.call(select.options).forEach(function (opt) {
      target[opt.value] = opt.textContent.trim();
    });
  }

  function formatPrice(value) {
    var num = parseInt(String(value || '').replace(/[^\d]/g, ''), 10);
    if (!num || num <= 0) return '—';
    try {
      return new Intl.NumberFormat('fa-IR').format(num) + ' ریال';
    } catch (e) {
      return num + ' ریال';
    }
  }

  function updateTypeGuide() {
    var guide = getGuide(currentType());
    var box = document.getElementById('item-type-guide');
    if (!box) return;
    box.innerHTML =
      '<i class="bi bi-lightbulb me-1"></i><strong>' +
      (guide.label || 'محصول') +
      ':</strong> ' +
      (guide.summary || '');
  }

  function updateMediaHint() {
    var guide = getGuide(currentType());
    var hint = document.getElementById('media-upload-hint');
    if (hint && guide.media_hint) {
      hint.textContent = guide.media_hint;
    }
  }

  function updateStatusBar() {
    var type = currentType();
    var guide = getGuide(type);
    var saleSelect = document.getElementById('id_sale_mode');
    var priceInput = document.getElementById('id_price');
    var activeInput = document.getElementById('id_is_active');

    var typeValue = document.getElementById('status-type-value');
    var saleValue = document.getElementById('status-sale-value');
    var priceValue = document.getElementById('status-price-value');
    var activeValue = document.getElementById('status-active-value');
    var activeItem = document.getElementById('status-active-item');
    var priceItem = document.getElementById('status-price-item');

    var isDownload = type === 'download';
    var isShowcase = type === 'showcase';

    if (typeValue) typeValue.textContent = guide.label || type;
    if (saleValue) {
      if (isDownload) saleValue.textContent = 'دانلود رایگان';
      else if (isShowcase) saleValue.textContent = 'فقط درخواست تماس';
      else if (saleSelect) saleValue.textContent = SALE_MODE_LABELS[saleSelect.value] || saleSelect.value;
    }
    if (priceValue) {
      priceValue.textContent = isDownload ? 'رایگان' : isShowcase ? '—' : formatPrice(priceInput && priceInput.value);
    }
    if (priceItem) {
      var hasPrice = !isDownload && !isShowcase && priceInput && parseInt(priceInput.value || '0', 10) > 0;
      priceItem.classList.toggle('is-ok', isDownload || hasPrice);
      priceItem.classList.toggle('is-warn', !isDownload && !isShowcase && !hasPrice);
    }
    if (activeValue && activeInput) {
      activeValue.textContent = activeInput.checked ? 'فعال' : 'غیرفعال';
    }
    if (activeItem && activeInput) {
      activeItem.classList.toggle('is-ok', activeInput.checked);
      activeItem.classList.toggle('is-off', !activeInput.checked);
    }
  }

  function applyTypeDefaults(type, force) {
    var guide = getGuide(type);
    var saleSelect = document.getElementById('id_sale_mode');
    if (saleSelect && guide.default_sale_mode && (force || !saleSelect.dataset.userTouched)) {
      saleSelect.value = guide.default_sale_mode;
    }
    if (type === 'showcase' || type === 'download') {
      var priceInput = document.getElementById('id_price');
      if (priceInput) priceInput.value = '';
    }
  }

  function syncItemTypeFields(forceDefaults) {
    var type = currentType();
    var guide = getGuide(type);

    var downloadBlock = document.getElementById('download-fields-block');
    var mediaBlock = document.getElementById('media-upload-block');
    var commerceBlock = document.getElementById('commerce-fields-block');
    var commercePanel = document.getElementById('commerce-panel');
    var commerceTab = document.getElementById('tab-commerce');
    var commerceWizardStep = document.getElementById('wizard-step-commerce');

    var showCommerce = !!guide.show_commerce;
    var showDownload = !!guide.show_download_block;

    setBlockVisible(downloadBlock, showDownload);
    setBlockVisible(mediaBlock, !showDownload);
    setBlockVisible(commerceBlock, showCommerce);
    setBlockVisible(document.getElementById('commerce-download-hint'), type === 'download');
    setBlockVisible(document.getElementById('commerce-showcase-hint'), type === 'showcase');
    setBlockVisible(document.getElementById('commerce-video-hint'), type === 'video');

    if (commercePanel) {
      commercePanel.classList.toggle('settings-block-hidden', !showCommerce && type !== 'video');
    }
    if (commerceTab) {
      commerceTab.classList.toggle('settings-block-hidden', !showCommerce);
      commerceTab.disabled = !showCommerce;
    }
    if (commerceWizardStep) {
      commerceWizardStep.classList.toggle('settings-block-hidden', !showCommerce);
      commerceWizardStep.setAttribute('aria-hidden', showCommerce ? 'false' : 'true');
    }

    if (forceDefaults) applyTypeDefaults(type, true);

    updateTypeGuide();
    updateMediaHint();
    updateStatusBar();

    if (wizardApi) wizardApi.refreshSteps();
  }

  function bindSlugAutofill() {
    var title = document.getElementById('id_title');
    var slug = document.getElementById('id_slug');
    if (!title || !slug) return;
    var touched = !!slug.value.trim();
    slug.addEventListener('input', function () {
      touched = !!slug.value.trim();
    });
    title.addEventListener('input', function () {
      if (touched) return;
      slug.value = slugifyTitle(title.value);
    });
  }

  function initTabs() {
    var tabBar = document.querySelector('.bot-setup-tabs');
    var tabs = document.querySelectorAll('.bot-setup-tabs [data-bot-setup-tab]');
    var panels = document.querySelectorAll('[data-bot-setup-panel]');
    if (!tabBar || !tabs.length || !panels.length) return;

    function activate(tabId, updateHash) {
      tabs.forEach(function (tab) {
        if (tab.disabled || tab.classList.contains('settings-block-hidden')) return;
        var isActive = tab.getAttribute('data-bot-setup-tab') === tabId;
        tab.classList.toggle('is-active', isActive);
        tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      panels.forEach(function (panel) {
        var isActive = panel.getAttribute('data-bot-setup-panel') === tabId;
        panel.classList.toggle('is-active', isActive);
        if (isActive) panel.removeAttribute('hidden');
        else panel.setAttribute('hidden', '');
      });
      if (updateHash !== false) {
        var hashKey = Object.keys(TAB_HASH).find(function (k) {
          return TAB_HASH[k] === tabId;
        });
        if (hashKey && window.location.hash !== '#' + hashKey) {
          history.replaceState(null, '', '#' + hashKey);
        }
      }
    }

    tabBar.addEventListener('click', function (e) {
      var tab = e.target.closest('[data-bot-setup-tab]');
      if (!tab || !tabBar.contains(tab) || tab.disabled) return;
      e.preventDefault();
      activate(tab.getAttribute('data-bot-setup-tab'));
    });

    var hash = (window.location.hash || '').replace('#', '');
    if (TAB_HASH[hash]) activate(TAB_HASH[hash], false);
    else activate('basics', false);

    window.addEventListener('hashchange', function () {
      var h = (window.location.hash || '').replace('#', '');
      if (TAB_HASH[h]) activate(TAB_HASH[h], false);
    });
  }

  function panelForStep(stepId) {
    return document.querySelector('[data-item-wizard-panel="' + stepId + '"]');
  }

  function showStepError(panel, message) {
    if (!panel) return;
    var existing = panel.querySelector('.campaign-wizard-step-error');
    if (existing) existing.remove();
    if (!message) return;
    var el = document.createElement('div');
    el.className = 'alert alert-danger campaign-wizard-step-error mt-3 mb-0';
    el.textContent = message;
    var body = panel.querySelector('.panel-card-body');
    if (body) body.prepend(el);
  }

  function validateWizardStep(stepId) {
    var panel = panelForStep(stepId);
    if (!panel) return true;

    showStepError(panel, '');

    if (stepId === 'commerce') {
      var type = currentType();
      if (!getGuide(type).show_commerce) return true;
    }

    var fields = panel.querySelectorAll('input, select, textarea');
    for (var i = 0; i < fields.length; i++) {
      var field = fields[i];
      if (field.type === 'hidden' || field.disabled) continue;
      if (field.closest('.settings-block-hidden')) continue;
      if (field.offsetParent === null && field.type !== 'file') continue;
      if (!field.checkValidity()) {
        field.reportValidity();
        return false;
      }
    }

    if (stepId === 'commerce') {
      var type = currentType();
      var saleSelect = document.getElementById('id_sale_mode');
      var priceInput = document.getElementById('id_price');
      var saleMode = saleSelect ? saleSelect.value : '';
      if (type === 'product' && saleMode !== 'request_only' && priceInput) {
        var price = parseInt(String(priceInput.value || '').replace(/[^\d]/g, ''), 10);
        if (!price || price <= 0) {
          priceInput.setCustomValidity('برای فروش محصول، قیمت را وارد کنید.');
          priceInput.reportValidity();
          priceInput.setCustomValidity('');
          return false;
        }
      }
      if (type === 'video' && saleSelect && saleSelect.value === 'buyable' && priceInput) {
        var videoPrice = parseInt(String(priceInput.value || '').replace(/[^\d]/g, ''), 10);
        if (!videoPrice || videoPrice <= 0) {
          priceInput.setCustomValidity('برای فروش دوره، قیمت را وارد کنید.');
          priceInput.reportValidity();
          priceInput.setCustomValidity('');
          return false;
        }
      }
    }

    if (stepId === 'media') {
      var itemType = currentType();
      if (itemType === 'download') {
        var downloadFile = document.getElementById('id_download_file');
        var downloadLink = document.getElementById('id_download_link');
        var hasFile = downloadFile && downloadFile.files && downloadFile.files.length > 0;
        var hasLink = downloadLink && (downloadLink.value || '').trim();
        if (!hasFile && !hasLink) {
          showStepError(panel, 'فایل دانلود یا لینک مستقیم را وارد کنید.');
          return false;
        }
      }
    }

    return true;
  }

  function findErrorStepIndex(steps) {
    for (var i = 0; i < steps.length; i++) {
      var panel = panelForStep(steps[i]);
      if (!panel) continue;
      if (
        panel.querySelector(
          '.is-invalid, .invalid-feedback, .text-danger, .alert-danger:not(.campaign-wizard-step-error)'
        )
      ) {
        return i;
      }
    }
    return -1;
  }

  function updateWizardStepNumbers(steps) {
    var nav = document.getElementById('item-wizard-nav');
    if (!nav) return;
    var visible = 0;
    nav.querySelectorAll('.campaign-wizard-step').forEach(function (btn) {
      if (btn.classList.contains('settings-block-hidden')) {
        btn.removeAttribute('data-wizard-order');
        return;
      }
      visible += 1;
      btn.setAttribute('data-wizard-order', String(visible));
      var numEl = btn.querySelector('.campaign-wizard-step-num');
      if (numEl) numEl.textContent = String(visible);
    });
    nav.querySelectorAll('.campaign-wizard-step-kicker').forEach(function (el) {
      /* kicker text updated per-panel in template — optional override */
    });
  }

  function initWizard() {
    var form = document.getElementById('catalog-item-form');
    var nav = document.getElementById('item-wizard-nav');
    var btnPrev = document.getElementById('item-wizard-prev');
    var btnNext = document.getElementById('item-wizard-next');
    var btnSubmit = document.getElementById('item-wizard-submit');
    var progressText = document.getElementById('item-wizard-progress');
    if (!form) return;

    var current = 0;
    var maxReached = 0;

    function steps() {
      return getWizardSteps();
    }

    function goTo(stepIndex, options) {
      options = options || {};
      var stepList = steps();
      if (stepIndex < 0 || stepIndex >= stepList.length) return;
      if (!options.skipValidation && stepIndex > current && !validateWizardStep(stepList[current])) {
        return;
      }

      current = stepIndex;
      if (current > maxReached) maxReached = current;

      var activeStepId = stepList[current];

      if (nav) {
        nav.querySelectorAll('.campaign-wizard-step').forEach(function (btn) {
          var stepId = btn.getAttribute('data-item-wizard-step');
          var idx = stepList.indexOf(stepId);
          var isActive = stepId === activeStepId;
          var isDone = idx >= 0 && idx < current;
          var isReachable = idx >= 0 && idx <= maxReached;
          btn.classList.toggle('is-active', isActive);
          btn.classList.toggle('is-done', isDone);
          btn.classList.toggle('is-disabled', !isReachable && !isActive);
          btn.setAttribute('aria-current', isActive ? 'step' : 'false');
        });
      }

      document.querySelectorAll('[data-item-wizard-panel]').forEach(function (panel) {
        var stepId = panel.getAttribute('data-item-wizard-panel');
        var isActive = stepId === activeStepId;
        panel.classList.toggle('is-active', isActive);
        if (isActive) panel.removeAttribute('hidden');
        else panel.setAttribute('hidden', '');
      });

      if (btnPrev) {
        btnPrev.disabled = current === 0;
        btnPrev.hidden = false;
      }
      if (btnNext) {
        var isLast = current === stepList.length - 1;
        btnNext.classList.toggle('settings-block-hidden', isLast);
        btnNext.hidden = isLast;
      }
      if (btnSubmit) {
        var showSubmit = current === stepList.length - 1;
        btnSubmit.classList.toggle('settings-block-hidden', !showSubmit);
        btnSubmit.hidden = !showSubmit;
      }

      if (progressText) {
        progressText.textContent =
          'مرحله ' +
          (current + 1) +
          ' از ' +
          stepList.length +
          ' — ' +
          (WIZARD_STEP_LABELS[activeStepId] || '');
      }

      document.querySelectorAll('.campaign-wizard-step-kicker').forEach(function (el) {
        el.textContent = 'مرحله ' + (current + 1) + ' از ' + stepList.length;
      });

      var activePanel = panelForStep(activeStepId);
      if (activePanel && options.focus !== false) {
        var focusable = activePanel.querySelector(
          'input:not([type="hidden"]), select, textarea, button'
        );
        if (focusable) {
          try {
            focusable.focus({ preventScroll: true });
          } catch (e) {
            focusable.focus();
          }
        }
      }

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function refreshSteps() {
      updateWizardStepNumbers(steps());
      var stepList = steps();
      var activeId = stepList[current];
      if (stepList.indexOf(activeId) < 0) {
        goTo(Math.min(current, stepList.length - 1), { skipValidation: true, focus: false });
      } else {
        goTo(current, { skipValidation: true, focus: false });
      }
    }

    wizardApi = { refreshSteps: refreshSteps };

    if (nav) {
      nav.addEventListener('click', function (e) {
        var btn = e.target.closest('.campaign-wizard-step');
        if (!btn || btn.classList.contains('settings-block-hidden')) return;
        e.preventDefault();
        var stepId = btn.getAttribute('data-item-wizard-step');
        var stepList = steps();
        var idx = stepList.indexOf(stepId);
        if (idx >= 0 && idx <= maxReached) {
          goTo(idx, { skipValidation: true });
        }
      });
    }

    if (btnNext) {
      btnNext.addEventListener('click', function () {
        goTo(current + 1);
      });
    }

    if (btnPrev) {
      btnPrev.addEventListener('click', function () {
        goTo(current - 1, { skipValidation: true });
      });
    }

    form.addEventListener('keydown', function (e) {
      var stepList = steps();
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA' && current < stepList.length - 1) {
        if (e.target.closest('#item-wizard-bar')) return;
        e.preventDefault();
        goTo(current + 1);
      }
    });

    form.addEventListener('submit', function (e) {
      var stepList = steps();
      if (current !== stepList.length - 1) {
        e.preventDefault();
        if (!validateWizardStep(stepList[current])) return;
        goTo(stepList.length - 1);
        return;
      }
      if (!validateWizardStep(stepList[current])) {
        e.preventDefault();
      }
    });

    updateWizardStepNumbers(steps());
    var errIdx = findErrorStepIndex(steps());
    if (errIdx >= 0) {
      maxReached = Math.max(maxReached, errIdx);
      goTo(errIdx, { skipValidation: true, focus: false });
    } else {
      goTo(0, { skipValidation: true, focus: false });
    }
  }

  function bindStatusInputs() {
    ['id_item_type', 'id_sale_mode', 'id_price', 'id_is_active'].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', updateStatusBar);
      el.addEventListener('change', function () {
        if (id === 'id_sale_mode') el.dataset.userTouched = '1';
        updateStatusBar();
      });
    });
  }

  function syncFlashSaleFields() {
    var toggle = document.getElementById('id_is_flash_sale');
    var dates = document.getElementById('flash-sale-dates');
    if (!toggle || !dates) return;
    var show = toggle.checked;
    setBlockVisible(dates, show);
  }

  function initFlashSale() {
    var toggle = document.getElementById('id_is_flash_sale');
    if (!toggle) return;
    toggle.addEventListener('change', syncFlashSaleFields);
    syncFlashSaleFields();
    if (window.SepJalaliPicker) {
      window.SepJalaliPicker.initAll(document.getElementById('catalog-item-form'));
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadTypeGuides();
    readSelectLabels('id_sale_mode', SALE_MODE_LABELS);

    var typeSelect = document.getElementById('id_item_type');
    if (typeSelect) {
      typeSelect.addEventListener('change', function () {
        syncItemTypeFields(true);
      });
      syncItemTypeFields(false);
    }

    bindSlugAutofill();
    bindStatusInputs();
    initFlashSale();

    if (isWizardMode()) {
      initWizard();
    } else {
      initTabs();
    }
  });
})();
