(function () {
  function cookie(name) {
    var m = document.cookie.match('(^|;)\s*' + name + '\s*=\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }

  function csrfToken() {
    var t = cookie('csrftoken');
    if (t) return t;
    var inp = document.querySelector('[name=csrfmiddlewaretoken]');
    return inp ? inp.value : '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('campaign-media-widget');
    if (!root) return;

    var ctSel = document.getElementById('id_content_type');
    var submitBtn = document.getElementById('campaign-main-submit');
    var videoPanel = document.getElementById('campaign-media-video-panel');
    var standardPanel = document.getElementById('campaign-media-standard-panel');
    var fileInput = document.getElementById('campaign-video-file-input');
    var uploadBtn = document.getElementById('campaign-video-upload-btn');
    var progressWrap = document.getElementById('campaign-video-progress-wrap');
    var progressBar = document.getElementById('campaign-video-progress-bar');
    var progressText = document.getElementById('campaign-video-progress-text');
    var statusEl = document.getElementById('campaign-video-status');
    var removeRow = document.getElementById('campaign-video-remove-row');
    var removeBtn = document.getElementById('campaign-video-remove-pending');

    var VIDEO = 'video';
    var maxMb = parseInt(root.dataset.maxMb || '120', 10);

    var uploadSucceeded =
      root.dataset.pendingReady === 'true' || root.dataset.uploadOk === 'true';

    function setDisabledInside(container, disabled) {
      if (!container) return;
      container.querySelectorAll('input, select, textarea, button').forEach(function (el) {
        el.disabled = disabled;
      });
    }

    function setSubmitAllowed(ok) {
      if (!submitBtn) return;
      submitBtn.disabled = !ok;
    }

    function updateSubmitGate() {
      if (!ctSel || ctSel.value !== VIDEO) {
        setSubmitAllowed(true);
        return;
      }
      var hasExisting = root.dataset.hasExistingVideo === 'true';
      var ok = uploadSucceeded || hasExisting;
      setSubmitAllowed(ok);
    }

    function togglePanels() {
      var v = ctSel && ctSel.value === VIDEO;
      if (videoPanel) videoPanel.classList.toggle('d-none', !v);
      if (standardPanel) standardPanel.classList.toggle('d-none', !!v);
      setDisabledInside(standardPanel, !!v);
      if (!v && ctSel) {
        fetch(root.dataset.clearUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': csrfToken(),
            Accept: 'application/json',
          },
        }).catch(function () {});
        uploadSucceeded = false;
        root.dataset.uploadOk = 'false';
        resetVideoUi(false);
      }
      updateSubmitGate();
    }

    function resetVideoUi(clearStatus) {
      if (progressWrap) progressWrap.classList.add('d-none');
      if (progressBar) progressBar.style.width = '0%';
      if (progressBar)
        progressBar.classList.remove('bg-danger');
      if (progressText) progressText.textContent = '';
      if (clearStatus && statusEl) statusEl.textContent = '';
      if (removeRow) removeRow.classList.add('d-none');
      if (fileInput) fileInput.value = '';
    }

    function tryParseJSON(txt) {
      try {
        return JSON.parse(txt);
      } catch (e) {
        return null;
      }
    }

    function showUploadError(msg) {
      if (statusEl) {
        statusEl.textContent = msg || 'آپلود ناموفق بود.';
      }
      if (progressBar) progressBar.classList.add('bg-danger');
      uploadSucceeded = false;
      root.dataset.uploadOk = 'false';
      updateSubmitGate();
    }

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener('click', function () {
        var f = fileInput.files && fileInput.files[0];
        if (!f) {
          showUploadError('ابتدا یک فایل ویدیو انتخاب کنید.');
          return;
        }
        if (typeof maxMb === 'number' && f.size > maxMb * 1024 * 1024) {
          showUploadError('حجم فایل از حد مجاز (' + maxMb + ' مگابایت) بیشتر است.');
          return;
        }
        if (statusEl) statusEl.textContent = 'در حال آپلود…';
        if (progressWrap) progressWrap.classList.remove('d-none');
        if (progressBar) {
          progressBar.classList.remove('bg-danger');
          progressBar.style.width = '0%';
        }
        uploadSucceeded = false;
        root.dataset.uploadOk = 'false';
        updateSubmitGate();

        var fd = new FormData();
        fd.append('file', f);
        fd.append('csrfmiddlewaretoken', csrfToken());
        var cid = root.dataset.campaignId || '';
        if (cid) fd.append('campaign_id', cid);

        var xhr = new XMLHttpRequest();
        xhr.open('POST', root.dataset.uploadUrl);
        xhr.setRequestHeader('X-CSRFToken', csrfToken());
        xhr.upload.onprogress = function (ev) {
          if (!ev.lengthComputable || !progressBar || !progressText) return;
          var pct = Math.round((ev.loaded / ev.total) * 100);
          progressBar.style.width = pct + '%';
          progressText.textContent = pct + '٪';
        };
        xhr.onload = function () {
          var data = tryParseJSON(xhr.responseText || '{}');
          if (xhr.status >= 200 && xhr.status < 300 && data && data.ok) {
            uploadSucceeded = true;
            root.dataset.uploadOk = 'true';
            if (statusEl)
              statusEl.textContent =
                'آپلود انجام شد. اکنون می‌توانید کمپین را ذخیره کنید.';
            if (progressWrap) progressWrap.classList.add('d-none');
            if (removeRow) removeRow.classList.remove('d-none');
          } else {
            var msg =
              (data && data.error) ||
              'خطا در آپلود (کد ' + xhr.status + ').';
            showUploadError(msg);
          }
          updateSubmitGate();
        };
        xhr.onerror = function () {
          showUploadError('ارتباط با سرور قطع شد.');
        };
        xhr.send(fd);
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', function () {
        fetch(root.dataset.clearUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': csrfToken(),
            Accept: 'application/json',
          },
        })
          .then(function () {
            uploadSucceeded = false;
            root.dataset.uploadOk = 'false';
            root.dataset.pendingReady = 'false';
            resetVideoUi(true);
            if (statusEl)
              statusEl.textContent =
                'فایل موقت حذف شد. در صورت نیاز دوباره آپلود کنید.';
            updateSubmitGate();
          })
          .catch(function () {
            showUploadError('حذف فایل موقت ناموفق بود.');
          });
      });
    }

    if (removeRow && uploadSucceeded) {
      removeRow.classList.remove('d-none');
    }

    if (ctSel) {
      ctSel.addEventListener('change', togglePanels);
      togglePanels();
    }

    updateSubmitGate();
  });
})();
