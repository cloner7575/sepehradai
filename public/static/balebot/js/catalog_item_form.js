(function () {
  var DOWNLOAD_TYPE = 'download';

  function syncItemTypeFields() {
    var select = document.getElementById('id_item_type');
    var downloadBlock = document.getElementById('download-fields-block');
    var mediaBlock = document.getElementById('media-upload-block');
    var commerceFields = document.querySelectorAll('[data-commerce-field]');
    if (!select) return;

    var isDownload = select.value === DOWNLOAD_TYPE;

    if (downloadBlock) {
      downloadBlock.classList.toggle('settings-block-hidden', !isDownload);
      downloadBlock.setAttribute('aria-hidden', isDownload ? 'false' : 'true');
    }
    if (mediaBlock) {
      mediaBlock.classList.toggle('settings-block-hidden', isDownload);
      mediaBlock.setAttribute('aria-hidden', isDownload ? 'true' : 'false');
    }
    commerceFields.forEach(function (el) {
      el.classList.toggle('settings-block-hidden', isDownload);
      el.setAttribute('aria-hidden', isDownload ? 'true' : 'false');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var select = document.getElementById('id_item_type');
    if (select) {
      select.addEventListener('change', syncItemTypeFields);
      syncItemTypeFields();
    }
  });
})();
