(function () {
  'use strict';

  var TRANSLIT = {
    '\u0622': 'a', '\u0627': 'a', '\u0628': 'b', '\u067e': 'p', '\u062a': 't', '\u062b': 's',
    '\u062c': 'j', '\u0686': 'ch', '\u062d': 'h', '\u062e': 'kh', '\u062f': 'd', '\u0630': 'z',
    '\u0631': 'r', '\u0632': 'z', '\u0698': 'zh', '\u0633': 's', '\u0634': 'sh', '\u0635': 's',
    '\u0636': 'z', '\u0637': 't', '\u0638': 'z', '\u0639': 'a', '\u063a': 'gh', '\u0641': 'f',
    '\u0642': 'gh', '\u06a9': 'k', '\u06af': 'g', '\u0644': 'l', '\u0645': 'm', '\u0646': 'n',
    '\u0648': 'v', '\u0647': 'h', '\u06cc': 'y', '\u064a': 'y', '\u200c': '-',
  };

  function transliterate(raw) {
    var out = '';
    for (var i = 0; i < raw.length; i++) {
      var ch = raw.charAt(i);
      out += TRANSLIT[ch] || ch;
    }
    return out;
  }

  function slugifyTitle(raw) {
    return transliterate(String(raw || ''))
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]+/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 80);
  }

  function $(id) {
    return document.getElementById(id);
  }

  function bindSlugAutofill() {
    var nameInput = $('id_name');
    var slugInput = $('id_slug');
    if (!nameInput || !slugInput) return;

    var touched = !!slugInput.value.trim();
    slugInput.addEventListener('input', function () {
      touched = !!slugInput.value.trim();
      updateSlugStatus();
    });
    nameInput.addEventListener('input', function () {
      updateNameStatus();
      if (!touched) {
        slugInput.value = slugifyTitle(nameInput.value);
        updateSlugStatus();
      }
    });
  }

  function updateNameStatus() {
    var nameInput = $('id_name');
    var name = (nameInput && nameInput.value.trim()) || '—';
    var previewName = $('cat-preview-name');
    var statusName = $('cat-status-name');
    if (previewName) previewName.textContent = name === '—' ? 'نام دسته' : name;
    if (statusName) statusName.textContent = name;
  }

  function updateSlugStatus() {
    var slugInput = $('id_slug');
    var slug = (slugInput && slugInput.value.trim()) || 'خودکار';
    var statusSlug = $('cat-status-slug');
    if (statusSlug) statusSlug.textContent = slug;
  }

  function bindActiveToggle() {
    var activeInput = $('id_is_active');
    var statusActive = $('cat-status-active');
    var statusItem = $('cat-status-active-item');
    if (!activeInput) return;

    function sync() {
      var on = activeInput.checked;
      if (statusActive) statusActive.textContent = on ? 'فعال' : 'غیرفعال';
      if (statusItem) {
        statusItem.classList.toggle('is-ok', on);
        statusItem.classList.toggle('is-off', !on);
      }
    }

    activeInput.addEventListener('change', sync);
    sync();
  }

  function bindImagePreview() {
    var fileInput = $('id_image');
    var previewImg = $('cat-image-preview-img');
    var placeholder = $('cat-image-placeholder');
    var thumbImg = $('cat-preview-thumb-img');
    var thumbIcon = $('cat-preview-thumb-icon');
    if (!fileInput) return;

    fileInput.addEventListener('change', function () {
      var file = fileInput.files && fileInput.files[0];
      if (!file || !file.type.match(/^image\//)) return;

      var reader = new FileReader();
      reader.onload = function () {
        if (previewImg) {
          previewImg.src = reader.result;
          previewImg.classList.remove('d-none');
        }
        if (placeholder) placeholder.classList.add('d-none');
        if (thumbImg) {
          thumbImg.src = reader.result;
          thumbImg.classList.remove('d-none');
        }
        if (thumbIcon) thumbIcon.classList.add('d-none');
      };
      reader.readAsDataURL(file);
    });
  }

  function init() {
    bindSlugAutofill();
    bindActiveToggle();
    bindImagePreview();
    updateNameStatus();
    updateSlugStatus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
