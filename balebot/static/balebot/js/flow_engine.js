(function () {
  'use strict';

  var studio = document.getElementById('flow-engine-studio');
  if (!studio) return;

  var tabs = studio.querySelectorAll('[data-studio-tab]');
  var panes = studio.querySelectorAll('[data-studio-pane]');

  function activateTab(name) {
    tabs.forEach(function (tab) {
      var active = tab.getAttribute('data-studio-tab') === name;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    panes.forEach(function (pane) {
      var active = pane.getAttribute('data-studio-pane') === name;
      pane.classList.toggle('is-active', active);
      pane.hidden = !active;
    });
    if (window.history.replaceState) {
      var url = new URL(window.location.href);
      url.searchParams.set('tab', name);
      window.history.replaceState({}, '', url);
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      activateTab(tab.getAttribute('data-studio-tab'));
    });
  });

  var initial = studio.getAttribute('data-active-tab') || 'bot';
  activateTab(initial);

  var miniPreview = document.getElementById('flow-miniapp-live-preview');
  var miniForm = document.getElementById('flow-miniapp-form');
  if (miniPreview && miniForm) {
    var titleInput = miniForm.querySelector('[name="hero_title"]');
    var subInput = miniForm.querySelector('[name="hero_subtitle"]');
    var primaryInput = miniForm.querySelector('[name="theme_primary"]');
    var accentInput = miniForm.querySelector('[name="theme_accent"]');
    var previewTitle = miniPreview.querySelector('.catalog-preview-title');
    var previewSub = miniPreview.querySelector('.catalog-preview-sub');
    var previewHeader = miniPreview.querySelector('.catalog-preview-header');
    var swatches = miniPreview.querySelectorAll('.catalog-color-swatch');

    function syncMiniPreview() {
      if (previewTitle && titleInput) {
        previewTitle.textContent = titleInput.value.trim() || 'فروشگاه';
      }
      if (previewSub && subInput) {
        previewSub.textContent = subInput.value.trim();
        previewSub.style.display = subInput.value.trim() ? '' : 'none';
      }
      if (previewHeader && primaryInput) {
        previewHeader.style.setProperty('--preview-primary', primaryInput.value || '#334155');
      }
      if (swatches.length >= 2) {
        if (primaryInput) swatches[0].style.background = primaryInput.value || '#334155';
        if (accentInput) swatches[1].style.background = accentInput.value || '#64748b';
      }
    }

    [titleInput, subInput, primaryInput, accentInput].forEach(function (el) {
      if (el) el.addEventListener('input', syncMiniPreview);
    });
    syncMiniPreview();
  }
})();
