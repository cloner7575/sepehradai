(function () {
  var TAB_HASH = {
    'sec-status': 'status',
    'sec-access': 'access',
    'sec-branding': 'branding',
    'sec-payment': 'payment',
    'sec-checkout': 'checkout',
  };

  var PAYMENT_METHODS = {
    admin_cart: 'ارسال سبد به ادمین',
    card_to_card: 'کارت به کارت',
    bale: 'پرداخت بله',
  };

  function setBlockVisible(block, show) {
    if (!block) return;
    block.classList.toggle('settings-block-hidden', !show);
    block.setAttribute('aria-hidden', show ? 'false' : 'true');
  }

  function bindToggle(checkboxId, blockId) {
    var cb = document.getElementById(checkboxId);
    var block = document.getElementById(blockId);
    if (!cb || !block) return;
    function sync() {
      setBlockVisible(block, cb.checked);
    }
    cb.addEventListener('change', sync);
    sync();
  }

  function paymentAdminReady() {
    var cb = document.getElementById('id_payment_admin_enabled');
    var chat = document.getElementById('id_admin_notify_chat_id');
    return !!(cb && cb.checked && chat && String(chat.value || '').trim());
  }

  function paymentCardToCardReady() {
    var cb = document.getElementById('id_payment_card_to_card_enabled');
    var card = document.getElementById('id_card_to_card_number');
    var sheba = document.getElementById('id_card_to_card_sheba');
    var holder = document.getElementById('id_card_to_card_holder');
    if (!cb || !cb.checked || !card || !sheba || !holder) return false;
    var digits = String(card.value || '').replace(/\D/g, '');
    var shebaVal = String(sheba.value || '').replace(/\s/g, '').toUpperCase();
    if (!shebaVal.startsWith('IR')) {
      shebaVal = 'IR' + shebaVal.replace(/\D/g, '');
    }
    return digits.length >= 16 && /^IR\d{24}$/.test(shebaVal) && String(holder.value || '').trim().length > 0;
  }

  function paymentBaleReady() {
    var cb = document.getElementById('id_payment_bale_enabled');
    var card = document.getElementById('id_bale_payment_card_number');
    if (!cb || !cb.checked || !card) return false;
    return String(card.value || '').trim().length > 0;
  }

  function readyPaymentMethodIds() {
    var ids = [];
    if (paymentAdminReady()) ids.push('admin_cart');
    if (paymentCardToCardReady()) ids.push('card_to_card');
    if (paymentBaleReady()) ids.push('bale');
    return ids;
  }

  function setStatusEl(el, ready, onMessage, offMessage) {
    if (!el) return;
    el.classList.toggle('text-success', ready);
    el.classList.toggle('text-warning', !ready);
    el.innerHTML = ready
      ? '<i class="bi bi-check-circle-fill me-1"></i>' + onMessage
      : '<i class="bi bi-exclamation-circle me-1"></i>' + offMessage;
  }

  function updatePaymentDefaultOptions() {
    var select = document.getElementById('id_payment_default_method');
    if (!select) return;
    var ready = readyPaymentMethodIds();
    var current = select.value;
    Array.prototype.slice.call(select.options).forEach(function (opt) {
      var allowed = ready.indexOf(opt.value) >= 0;
      opt.hidden = !allowed;
      opt.disabled = !allowed;
    });
    if (ready.length && ready.indexOf(current) < 0) {
      select.value = ready[0];
    }
  }

  function updateTopStatusBar(anyReady, labels, isEnabled) {
    var paymentItem = document.getElementById('status-payment-item');
    var paymentValue = document.getElementById('status-payment-value');
    var purchaseItem = document.getElementById('status-purchase-item');
    var purchaseValue = document.getElementById('status-purchase-value');

    if (paymentItem && paymentValue) {
      paymentItem.classList.toggle('is-ok', anyReady);
      paymentItem.classList.toggle('is-warn', !anyReady);
      paymentValue.textContent = anyReady ? labels.join('، ') : 'تنظیم نشده';
    }

    if (purchaseItem && purchaseValue) {
      var canPurchase = anyReady && isEnabled;
      purchaseItem.classList.remove('is-ok', 'is-warn', 'is-off');
      if (canPurchase) {
        purchaseItem.classList.add('is-ok');
        purchaseValue.textContent = 'فعال';
      } else if (isEnabled) {
        purchaseItem.classList.add('is-warn');
        purchaseValue.textContent = 'نیاز به پرداخت';
      } else {
        purchaseItem.classList.add('is-off');
        purchaseValue.textContent = 'غیرفعال';
      }
    }
  }

  function updatePaymentReadiness() {
    var box = document.getElementById('payment-readiness');
    var adminReady = paymentAdminReady();
    var cardReady = paymentCardToCardReady();
    var baleReady = paymentBaleReady();
    var anyReady = adminReady || cardReady || baleReady;
    var isEnabled = !!(document.getElementById('id_is_enabled') && document.getElementById('id_is_enabled').checked);

    setStatusEl(
      document.getElementById('payment-admin-status'),
      adminReady,
      'این روش برای خرید کاربران آماده است.',
      'برای فعال شدن، چت‌آیدی ادمین را وارد کنید.',
    );
    setStatusEl(
      document.getElementById('payment-card-to-card-status'),
      cardReady,
      'این روش برای خرید کاربران آماده است.',
      'برای فعال شدن، شماره کارت، شبا و نام صاحب حساب را کامل کنید.',
    );
    setStatusEl(
      document.getElementById('payment-bale-status'),
      baleReady,
      'این روش برای خرید کاربران آماده است.',
      'برای فعال شدن، شماره کارت ۱۶ رقمی را وارد کنید.',
    );

    var labels = readyPaymentMethodIds().map(function (id) {
      return PAYMENT_METHODS[id] || id;
    });
    updateTopStatusBar(anyReady, labels, isEnabled);

    if (box) {
      box.classList.remove('alert-success', 'alert-warning', 'alert-info');
      if (anyReady) {
        box.classList.add('alert-success');
        box.innerHTML =
          '<i class="bi bi-check-circle-fill me-1"></i>' +
          'خرید برای کاربران با روش' +
          (labels.length > 1 ? '‌های' : '') +
          ' <strong>' +
          labels.join('</strong> و <strong>') +
          '</strong> فعال است.';
      } else {
        box.classList.add('alert-warning');
        box.innerHTML =
          '<i class="bi bi-exclamation-triangle me-1"></i>' +
          'هنوز هیچ روش پرداختی کامل نشده است. حداقل یکی از روش‌ها را با اطلاعات لازم تکمیل کنید.';
      }
    }

    updatePaymentDefaultOptions();
  }

  function bindPaymentInputs() {
    [
      'id_payment_admin_enabled',
      'id_admin_notify_chat_id',
      'id_payment_card_to_card_enabled',
      'id_card_to_card_number',
      'id_card_to_card_sheba',
      'id_card_to_card_holder',
      'id_payment_bale_enabled',
      'id_bale_payment_card_number',
      'id_is_enabled',
    ].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', updatePaymentReadiness);
      el.addEventListener('change', updatePaymentReadiness);
    });
    updatePaymentReadiness();
  }

  function initTabs() {
    var tabBar = document.querySelector('.bot-setup-tabs');
    var tabs = document.querySelectorAll('.bot-setup-tabs [data-bot-setup-tab]');
    var panels = document.querySelectorAll('[data-bot-setup-panel]');
    if (!tabBar || !tabs.length || !panels.length) return;

    function activate(tabId, updateHash) {
      tabs.forEach(function (tab) {
        var isActive = tab.getAttribute('data-bot-setup-tab') === tabId;
        tab.classList.toggle('is-active', isActive);
        tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      panels.forEach(function (panel) {
        var isActive = panel.getAttribute('data-bot-setup-panel') === tabId;
        panel.classList.toggle('is-active', isActive);
        if (isActive) {
          panel.removeAttribute('hidden');
        } else {
          panel.setAttribute('hidden', '');
        }
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
      if (!tab || !tabBar.contains(tab)) return;
      e.preventDefault();
      activate(tab.getAttribute('data-bot-setup-tab'));
    });

    var hash = (window.location.hash || '').replace('#', '');
    if (TAB_HASH[hash]) {
      activate(TAB_HASH[hash], false);
    } else {
      activate('status', false);
    }

    window.addEventListener('hashchange', function () {
      var h = (window.location.hash || '').replace('#', '');
      if (TAB_HASH[h]) activate(TAB_HASH[h], false);
    });
  }

  function initColorPreview() {
    var primary = document.getElementById('id_theme_primary');
    var accent = document.getElementById('id_theme_accent');
    var previewPrimary = document.getElementById('preview-primary');
    var previewAccent = document.getElementById('preview-accent');
    if (!primary || !previewPrimary) return;
    function sync() {
      if (previewPrimary && primary.value) previewPrimary.style.background = primary.value;
      if (previewAccent && accent && accent.value) previewAccent.style.background = accent.value;
    }
    primary.addEventListener('input', sync);
    if (accent) accent.addEventListener('input', sync);
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindToggle('id_payment_admin_enabled', 'admin-payment-block');
    bindToggle('id_payment_card_to_card_enabled', 'card-to-card-payment-block');
    bindToggle('id_payment_bale_enabled', 'bale-payment-block');
    bindToggle('id_require_channel_membership', 'channel-access-block');
    bindPaymentInputs();
    initTabs();
    initColorPreview();
  });
})();
