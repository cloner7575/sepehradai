(function () {
  'use strict';

  var panel = document.getElementById('campaign-send-progress');
  if (!panel) return;

  var batchUrl = panel.dataset.batchUrl;
  var autostart = panel.dataset.autostart === '1';
  var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
  var csrf = csrfInput ? csrfInput.value : '';
  var running = false;
  var stopped = false;

  var bar = document.getElementById('campaign-send-bar');
  var label = document.getElementById('campaign-send-label');
  var stats = document.getElementById('campaign-send-stats');
  var statusEl = document.getElementById('campaign-send-status');
  var resumeBtn = document.getElementById('campaign-send-resume');
  var errorEl = document.getElementById('campaign-send-error');

  function pct(data) {
    if (!data.total) return 0;
    return Math.min(100, Math.round(((data.sent + data.failed) / data.total) * 100));
  }

  function updateUi(data) {
    var percent = pct(data);
    if (bar) {
      bar.style.width = percent + '%';
      bar.setAttribute('aria-valuenow', String(percent));
    }
    if (label) {
      label.textContent = percent + '٪';
    }
    if (stats) {
      stats.textContent =
        (data.sent || 0) +
        ' ارسال · ' +
        (data.failed || 0) +
        ' خطا · ' +
        (data.pending || 0) +
        ' باقی‌مانده از ' +
        (data.total || 0);
    }
    if (statusEl) {
      if (data.done) {
        statusEl.textContent = 'ارسال کامل شد.';
      } else if (data.waiting) {
        statusEl.textContent = data.message || 'در انتظار زمان‌بندی…';
      } else if (running) {
        statusEl.textContent = 'در حال ارسال دسته‌ای…';
      } else {
        statusEl.textContent = 'آمادهٔ ادامهٔ ارسال';
      }
    }
    if (resumeBtn) {
      resumeBtn.hidden = running || !!data.done || !!data.waiting;
    }
  }

  function showError(message) {
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.hidden = false;
    }
    if (statusEl) {
      statusEl.textContent = 'ارسال متوقف شد.';
    }
    running = false;
    if (resumeBtn) resumeBtn.hidden = false;
  }

  function runBatch() {
    if (stopped || !batchUrl || running) return;
    running = true;
    if (errorEl) errorEl.hidden = true;
    if (resumeBtn) resumeBtn.hidden = true;
    if (statusEl) statusEl.textContent = 'در حال ارسال دسته‌ای…';

    fetch(batchUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrf,
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.error || 'خطا در ارسال');
          return data;
        });
      })
      .then(function (data) {
        updateUi(data);
        running = false;
        if (data.ok && !data.done && !data.waiting) {
          window.setTimeout(runBatch, 120);
          return;
        }
        if (data.done) {
          window.setTimeout(function () {
            window.location.href = window.location.pathname;
          }, 1200);
        }
      })
      .catch(function (err) {
        showError(err.message || 'خطای شبکه');
      });
  }

  if (resumeBtn) {
    resumeBtn.addEventListener('click', function () {
      stopped = false;
      runBatch();
    });
  }

  var queueForm = document.getElementById('campaign-queue-form');
  if (queueForm) {
    queueForm.addEventListener('submit', function () {
      panel.hidden = false;
      if (statusEl) statusEl.textContent = 'در حال آماده‌سازی…';
      if (resumeBtn) resumeBtn.hidden = true;
    });
  }

  updateUi({
    total: parseInt(panel.dataset.total || '0', 10),
    sent: parseInt(panel.dataset.sent || '0', 10),
    failed: parseInt(panel.dataset.failed || '0', 10),
    pending: parseInt(panel.dataset.pending || '0', 10),
    done: panel.dataset.done === '1',
  });

  if (autostart) {
    runBatch();
  }
})();
