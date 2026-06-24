(function () {
  'use strict';

  var panel = document.getElementById('campaign-send-progress');
  if (!panel) return;

  var batchUrl = panel.dataset.batchUrl;
  var batchSize = parseInt(panel.dataset.batchSize || '5', 10);
  var autostart = panel.dataset.autostart === '1';
  var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
  var csrf = csrfInput ? csrfInput.value : '';
  var running = false;
  var stopped = false;
  var batchCount = 0;

  var bar = document.getElementById('campaign-send-bar');
  var label = document.getElementById('campaign-send-label');
  var statsMain = document.getElementById('campaign-send-stats-main');
  var statsExtra = document.getElementById('campaign-send-stats-extra');
  var statusEl = document.getElementById('campaign-send-status');
  var batchHint = document.getElementById('campaign-send-batch-hint');
  var resumeBtn = document.getElementById('campaign-send-resume');
  var errorEl = document.getElementById('campaign-send-error');
  var spinner = document.getElementById('campaign-send-spinner');

  var metricSent = document.getElementById('campaign-send-metric-sent');
  var metricFailed = document.getElementById('campaign-send-metric-failed');
  var metricPending = document.getElementById('campaign-send-metric-pending');
  var metricTotal = document.getElementById('campaign-send-metric-total');

  function pct(data) {
    if (!data.total) return 0;
    return Math.min(100, Math.round(((data.sent + data.failed) / data.total) * 100));
  }

  function setSpinner(active) {
    if (!spinner) return;
    spinner.classList.toggle('is-active', !!active);
    panel.classList.toggle('is-live', !!active);
  }

  function setBarAnimated(active) {
    if (!bar) return;
    bar.classList.toggle('progress-bar-animated', !!active);
    bar.classList.toggle('progress-bar-striped', !!active);
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
    if (metricSent) metricSent.textContent = String(data.sent || 0);
    if (metricFailed) metricFailed.textContent = String(data.failed || 0);
    if (metricPending) metricPending.textContent = String(data.pending || 0);
    if (metricTotal) metricTotal.textContent = String(data.total || 0);
    if (statsMain) {
      statsMain.textContent =
        (data.sent || 0) + ' از ' + (data.total || 0) + ' پیام ارسال شد';
    }
    if (statsExtra) {
      var extra = '';
      if (data.failed) extra += ' · ' + data.failed + ' خطا';
      if (data.pending) extra += ' · ' + data.pending + ' باقی‌مانده';
      statsExtra.textContent = extra;
    }
    if (batchHint && !data.done && !data.waiting) {
      batchHint.textContent =
        'هر دسته ' + batchSize + ' پیام — دستهٔ ' + batchCount;
    }
    if (statusEl) {
      if (data.done) {
        statusEl.textContent = 'ارسال کامل شد.';
      } else if (data.waiting) {
        statusEl.textContent = data.message || 'در انتظار زمان‌بندی…';
      } else if (running) {
        var batchNote = '';
        if (typeof data.batch_sent === 'number') {
          batchNote =
            ' — ' + data.batch_sent + ' ارسال';
          if (data.batch_failed) {
            batchNote += '، ' + data.batch_failed + ' خطا';
          }
          batchNote += ' در این دسته';
        }
        statusEl.textContent = 'در حال ارسال…' + batchNote;
      } else {
        statusEl.textContent = 'آمادهٔ ادامهٔ ارسال';
      }
    }
    if (resumeBtn) {
      resumeBtn.hidden = running || !!data.done || !!data.waiting;
    }
    setSpinner(running && !data.done && !data.waiting);
    setBarAnimated(running && !data.done && !data.waiting);
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
    setSpinner(false);
    setBarAnimated(false);
    if (resumeBtn) resumeBtn.hidden = false;
  }

  function runBatch() {
    if (stopped || !batchUrl || running) return;
    running = true;
    batchCount += 1;
    if (errorEl) errorEl.hidden = true;
    if (resumeBtn) resumeBtn.hidden = true;
    setSpinner(true);
    setBarAnimated(true);
    if (statusEl) {
      statusEl.textContent = 'در حال ارسال دستهٔ ' + batchCount + '…';
    }

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
          window.setTimeout(runBatch, 200);
          return;
        }
        setSpinner(false);
        setBarAnimated(false);
        if (data.done) {
          if (statusEl) statusEl.textContent = 'ارسال کامل شد.';
          if (batchHint) batchHint.textContent = 'همهٔ پیام‌ها ارسال شدند.';
          window.setTimeout(function () {
            window.location.href = window.location.pathname;
          }, 1500);
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
      var btn = queueForm.querySelector('button[type=submit]');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>در حال آماده‌سازی…';
      }
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
