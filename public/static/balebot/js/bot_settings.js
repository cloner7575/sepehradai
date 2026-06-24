(function () {
  var TAB_HASH = {
    'sec-connection': 'connection',
    'sec-start': 'welcome',
    'sec-commands': 'commands',
    'sec-support': 'support',
    'sec-advanced': 'panel',
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
      activate('connection', false);
    }

    window.addEventListener('hashchange', function () {
      var h = (window.location.hash || '').replace('#', '');
      if (TAB_HASH[h]) activate(TAB_HASH[h], false);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindToggle('id_collect_contact_on_start', 'contact-fields-block');
    bindToggle('id_enable_support', 'support-fields-block');
    initTabs();
  });
})();
