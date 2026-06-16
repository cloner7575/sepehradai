(function () {
  function cookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }

  function csrfToken() {
    var t = cookie('csrftoken');
    if (t) return t;
    var inp = document.querySelector('[name=csrfmiddlewaretoken]');
    return inp ? inp.value : '';
  }

  function normalizeDigits(text) {
    if (!text) return '';
    return text
      .replace(/[\u06F0-\u06F9]/g, function (c) {
        return String(c.charCodeAt(0) - 0x06f0);
      })
      .replace(/[\u0660-\u0669]/g, function (c) {
        return String(c.charCodeAt(0) - 0x0660);
      });
  }

  function extractPhones(content) {
    if (!content) return [];
    var normalized = normalizeDigits(content);
    var extracted = new Set();
    var mobilePattern = /(?:\+98|0098|0)?[\s\-.]*9[\s\-.]*(?:\d[\s\-.]*){9}/g;
    var matches = normalized.match(mobilePattern);
    if (matches) {
      matches.forEach(function (match) {
        var digitsOnly = match.replace(/\D/g, '');
        if (digitsOnly.startsWith('0098')) digitsOnly = digitsOnly.substring(4);
        else if (digitsOnly.startsWith('98')) digitsOnly = digitsOnly.substring(2);
        if (digitsOnly.length === 10 && digitsOnly.startsWith('9')) digitsOnly = '0' + digitsOnly;
        if (digitsOnly.length === 11 && digitsOnly.startsWith('09')) extracted.add(digitsOnly);
      });
    }
    return Array.from(extracted);
  }

  function collectShareText(share) {
    if (!share || typeof share !== 'object') return '';
    var parts = [];
    ['share_text', 'link', 'original_content_owner', 'profile_share_username'].forEach(function (key) {
      if (share[key]) parts.push(String(share[key]));
    });
    return parts.join(' ');
  }

  function collectPhonesFromMessage(msg, targetSet) {
    if (!msg || typeof msg !== 'object') return;
    extractPhones(msg.content).forEach(function (p) {
      targetSet.add(p);
    });
    if (msg.share) {
      extractPhones(collectShareText(msg.share)).forEach(function (p) {
        targetSet.add(p);
      });
    }
  }

  function extractFromJsonText(text) {
    var found = new Set();
    try {
      var data = JSON.parse(text);
      if (Array.isArray(data.messages)) {
        data.messages.forEach(function (msg) {
          collectPhonesFromMessage(msg, found);
        });
      }
    } catch (_) {
      /* skip invalid JSON */
    }
    return Array.from(found);
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function formatFileSize(bytes) {
    if (!bytes && bytes !== 0) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('phone-extractor-root');
    if (!root) return;

    var domainSelect = document.getElementById('activity-domain');
    var customWrap = document.getElementById('activity-domain-custom-wrap');
    var customInput = document.getElementById('activity-domain-custom');
    var zipInput = document.getElementById('zip-input');
    var dropzone = document.getElementById('ig-dropzone');
    var startBtn = document.getElementById('start-btn');
    var cancelBtn = document.getElementById('cancel-btn');
    var progressWrap = document.getElementById('extract-progress-wrap');
    var progressBar = document.getElementById('extract-progress-bar');
    var statusEl = document.getElementById('extract-status');
    var counterEl = document.getElementById('phone-counter');
    var errorEl = document.getElementById('extract-error');
    var errorText = errorEl && errorEl.querySelector('.ig-alert-text');
    var successEl = document.getElementById('extract-success');
    var successText = successEl && successEl.querySelector('.ig-alert-text');
    var liveListWrap = document.getElementById('phone-live-list-wrap');
    var liveList = document.getElementById('phone-live-list');

    var startUrl = root.dataset.startUrl;
    var phoneUrl = root.dataset.phoneUrl;
    var finishUrl = root.dataset.finishUrl;

    var cancelled = false;
    var running = false;
    var savedCount = 0;
    var selectedFile = null;

    var dropzoneDefaultHtml =
      '<i class="bi bi-cloud-arrow-up ig-dropzone-icon"></i>' +
      '<p class="ig-dropzone-title">فایل ZIP را اینجا رها کنید</p>' +
      '<p class="ig-dropzone-sub">یا کلیک کنید</p>';

    function hideAlerts() {
      errorEl.classList.add('d-none');
      successEl.classList.add('d-none');
    }

    function showError(msg) {
      if (errorText) errorText.textContent = msg;
      else errorEl.textContent = msg;
      errorEl.classList.remove('d-none');
    }

    function updateCounter(count) {
      counterEl.textContent = String(count);
    }

    function appendToLiveList(phone) {
      liveListWrap.classList.remove('d-none');
      var chip = document.createElement('span');
      chip.className = 'ig-phone-chip';
      chip.textContent = phone;
      liveList.prepend(chip);
      while (liveList.children.length > 40) {
        liveList.removeChild(liveList.lastChild);
      }
    }

    function updateStatus(text, pct) {
      statusEl.textContent = text;
      if (typeof pct === 'number') {
        progressBar.style.width = Math.min(100, Math.max(0, pct)) + '%';
      }
    }

    function domainReady() {
      var val = domainSelect.value;
      if (!val) return false;
      if (val === 'other') {
        return (customInput.value || '').trim().length > 0;
      }
      return true;
    }

    function renderDropzoneEmpty() {
      selectedFile = null;
      zipInput.value = '';
      dropzone.classList.remove('ig-dropzone-has-file');
      dropzone.innerHTML = dropzoneDefaultHtml;
      if (!domainReady() || running) {
        dropzone.classList.add('ig-dropzone-disabled');
        dropzone.querySelector('.ig-dropzone-sub').textContent = running
          ? 'در حال پردازش…'
          : 'ابتدا حوزه فعالیت را انتخاب کنید';
      } else {
        dropzone.classList.remove('ig-dropzone-disabled');
        dropzone.querySelector('.ig-dropzone-sub').textContent = 'یا کلیک کنید';
      }
    }

    function renderDropzoneFile(file) {
      selectedFile = file;
      dropzone.classList.add('ig-dropzone-has-file');
      dropzone.classList.remove('ig-dropzone-disabled', 'ig-dropzone-drag');
      dropzone.innerHTML =
        '<div class="ig-file-chip">' +
        '<span class="ig-file-chip-icon"><i class="bi bi-file-earmark-zip"></i></span>' +
        '<span class="ig-file-chip-meta">' +
        '<span class="ig-file-chip-name"></span>' +
        '<span class="ig-file-chip-size"></span>' +
        '</span>' +
        '<button type="button" class="ig-file-chip-remove" aria-label="حذف فایل"><i class="bi bi-x-lg"></i></button>' +
        '</div>';
      dropzone.querySelector('.ig-file-chip-name').textContent = file.name;
      dropzone.querySelector('.ig-file-chip-size').textContent = formatFileSize(file.size);
      dropzone.querySelector('.ig-file-chip-remove').addEventListener('click', function (e) {
        e.stopPropagation();
        renderDropzoneEmpty();
        refreshFormState();
      });
    }

    function setSelectedFile(file) {
      if (!file) {
        renderDropzoneEmpty();
        refreshFormState();
        return;
      }
      if (!/\.zip$/i.test(file.name)) {
        showError('فقط فایل ZIP مجاز است.');
        return;
      }
      hideAlerts();
      var dt = new DataTransfer();
      dt.items.add(file);
      zipInput.files = dt.files;
      renderDropzoneFile(file);
      refreshFormState();
    }

    function refreshFormState() {
      var ready = domainReady();
      zipInput.disabled = !ready || running;
      if (!selectedFile && !running) {
        if (ready) {
          dropzone.classList.remove('ig-dropzone-disabled');
          if (!dropzone.classList.contains('ig-dropzone-has-file')) {
            var sub = dropzone.querySelector('.ig-dropzone-sub');
            if (sub) sub.textContent = 'یا کلیک کنید';
          }
        } else if (!dropzone.classList.contains('ig-dropzone-has-file')) {
          dropzone.classList.add('ig-dropzone-disabled');
          var subEl = dropzone.querySelector('.ig-dropzone-sub');
          if (subEl) subEl.textContent = 'ابتدا حوزه فعالیت را انتخاب کنید';
        }
      }
      startBtn.disabled = !ready || running || !selectedFile;
    }

    domainSelect.addEventListener('change', function () {
      var isOther = domainSelect.value === 'other';
      customWrap.classList.toggle('d-none', !isOther);
      customInput.required = isOther;
      if (!isOther) customInput.value = '';
      refreshFormState();
    });

    customInput.addEventListener('input', refreshFormState);
    zipInput.addEventListener('change', function () {
      if (zipInput.files && zipInput.files.length) {
        setSelectedFile(zipInput.files[0]);
      }
    });

    dropzone.addEventListener('click', function () {
      if (running || dropzone.classList.contains('ig-dropzone-disabled')) return;
      if (dropzone.classList.contains('ig-dropzone-has-file')) return;
      zipInput.click();
    });

    dropzone.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        dropzone.click();
      }
    });

    ['dragenter', 'dragover'].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (!running && domainReady() && !dropzone.classList.contains('ig-dropzone-has-file')) {
          dropzone.classList.add('ig-dropzone-drag');
        }
      });
    });

    ['dragleave', 'drop'].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('ig-dropzone-drag');
      });
    });

    dropzone.addEventListener('drop', function (e) {
      if (running || !domainReady()) return;
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) setSelectedFile(files[0]);
    });

    cancelBtn.addEventListener('click', function () {
      cancelled = true;
    });

    function postJson(url, payload, retries) {
      retries = retries || 0;
      return fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
        },
        body: JSON.stringify(payload),
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .catch(function (err) {
          if (retries < 3) {
            return sleep(500 * (retries + 1)).then(function () {
              return postJson(url, payload, retries + 1);
            });
          }
          throw err;
        });
    }

    function savePhone(jobId, phone) {
      return postJson(phoneUrl, { job_id: jobId, phone: phone }).then(function (result) {
        if (!result.ok || !result.data.ok) {
          var msg = (result.data && result.data.error) || 'خطا در ذخیره شماره';
          throw new Error(msg);
        }
        if (result.data.saved) {
          savedCount = result.data.phone_count;
          updateCounter(savedCount);
          appendToLiveList(phone);
        }
        return result.data;
      });
    }

    async function runExtraction(file) {
      cancelled = false;
      running = true;
      savedCount = 0;
      hideAlerts();
      liveList.innerHTML = '';
      liveListWrap.classList.add('d-none');
      root.classList.add('ig-is-running');
      progressWrap.classList.remove('d-none');
      cancelBtn.classList.remove('d-none');
      startBtn.disabled = true;
      zipInput.disabled = true;
      domainSelect.disabled = true;
      customInput.disabled = true;
      dropzone.classList.add('ig-dropzone-disabled');
      updateCounter(0);
      updateStatus('در حال آماده‌سازی…', 0);

      var domainId = domainSelect.value;
      var domainCustom = domainId === 'other' ? customInput.value.trim() : '';
      var jobId;

      try {
        updateStatus('ایجاد عملیات…', 2);
        var startResult = await postJson(startUrl, {
          activity_domain_id: domainId === 'other' ? 'other' : domainId,
          activity_domain_custom: domainCustom,
          source_filename: file.name,
        });
        if (!startResult.ok || !startResult.data.ok) {
          throw new Error((startResult.data && startResult.data.error) || 'خطا در شروع عملیات');
        }
        jobId = startResult.data.job_id;

        updateStatus('خواندن ZIP…', 5);
        var zip = await JSZip.loadAsync(file);
        var jsonEntries = Object.keys(zip.files)
          .filter(function (path) {
            var entry = zip.files[path];
            return entry && !entry.dir && path.toLowerCase().endsWith('.json');
          })
          .map(function (path) {
            return zip.files[path];
          });

        var total = jsonEntries.length;
        if (!total) {
          throw new Error('هیچ فایل JSON در ZIP یافت نشد.');
        }

        var seen = new Set();

        for (var i = 0; i < jsonEntries.length; i++) {
          if (cancelled) {
            throw new Error('عملیات لغو شد.');
          }

          var pct = 5 + Math.round(((i + 1) / total) * 90);
          updateStatus('فایل ' + (i + 1) + ' از ' + total, pct);

          var text = await jsonEntries[i].async('string');
          var phones = extractFromJsonText(text);

          for (var j = 0; j < phones.length; j++) {
            if (cancelled) {
              throw new Error('عملیات لغو شد.');
            }
            var phone = phones[j];
            if (seen.has(phone)) continue;
            seen.add(phone);
            await savePhone(jobId, phone);
          }

          await sleep(0);
        }

        updateStatus('نهایی‌سازی…', 98);
        var finishResult = await postJson(finishUrl, {
          job_id: jobId,
          json_files_scanned: total,
        });
        if (!finishResult.ok || !finishResult.data.ok) {
          throw new Error((finishResult.data && finishResult.data.error) || 'خطا در پایان عملیات');
        }

        updateStatus('تمام شد', 100);
        if (successText) {
          successText.innerHTML =
            savedCount +
            ' شماره ذخیره شد — <a href="' +
            finishResult.data.redirect_url +
            '">مشاهده لیست</a>';
        }
        successEl.classList.remove('d-none');
      } catch (err) {
        showError(err.message || 'خطای ناشناخته');
        if (jobId) {
          try {
            await postJson(finishUrl, {
              job_id: jobId,
              json_files_scanned: 0,
              error: err.message || 'خطا',
            });
          } catch (_) {
            /* ignore */
          }
        }
      } finally {
        running = false;
        root.classList.remove('ig-is-running');
        cancelBtn.classList.add('d-none');
        domainSelect.disabled = false;
        customInput.disabled = false;
        refreshFormState();
      }
    }

    startBtn.addEventListener('click', function () {
      if (!selectedFile) return;
      runExtraction(selectedFile);
    });

    renderDropzoneEmpty();
    refreshFormState();
  });
})();
