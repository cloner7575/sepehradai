(function () {
  var STEPS = ['basics', 'content', 'audience'];
  var STEP_LABELS = ['عنوان و زمان', 'محتوای پیام', 'مخاطبان'];

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function setFormSaving(form, saving) {
    var overlay = document.getElementById('campaign-save-overlay');
    var btnSubmit = document.getElementById('campaign-main-submit');
    var bar = document.getElementById('campaign-wizard-bar');

    if (form) form.classList.toggle('is-saving', saving);
    if (overlay) {
      if (saving) {
        overlay.removeAttribute('hidden');
        overlay.setAttribute('aria-busy', 'true');
      } else {
        overlay.setAttribute('hidden', '');
        overlay.setAttribute('aria-busy', 'false');
      }
    }
    if (btnSubmit) {
      btnSubmit.disabled = saving;
      if (saving) {
        btnSubmit.innerHTML =
          '<span class="campaign-save-btn-spinner" aria-hidden="true"></span>در حال ذخیره…';
      }
    }
    if (bar) {
      bar.querySelectorAll('button, a').forEach(function (el) {
        if (saving) {
          el.setAttribute('data-was-disabled', el.disabled ? '1' : '0');
          if (el.tagName === 'BUTTON') el.disabled = true;
          else el.setAttribute('aria-disabled', 'true');
          el.style.pointerEvents = 'none';
        } else {
          if (el.tagName === 'BUTTON') {
            el.disabled = el.getAttribute('data-was-disabled') === '1';
          }
          el.removeAttribute('aria-disabled');
          el.style.pointerEvents = '';
        }
      });
    }
  }

  function initWizard() {
    var form = document.getElementById('campaign-form-main');
    var nav = document.getElementById('campaign-wizard-nav');
    var stepButtons = document.querySelectorAll('.campaign-wizard-step');
    var panels = document.querySelectorAll('[data-campaign-panel]');
    var btnPrev = document.getElementById('campaign-wizard-prev');
    var btnNext = document.getElementById('campaign-wizard-next');
    var btnSubmit = document.getElementById('campaign-main-submit');
    var progressText = document.getElementById('campaign-wizard-progress');
    if (!form || !panels.length) return;

    var current = 0;
    var maxReached = 0;

    function panelFor(stepId) {
      return document.querySelector('[data-campaign-panel="' + stepId + '"]');
    }

    function showStepError(panel, message) {
      var existing = panel.querySelector('.campaign-wizard-step-error');
      if (existing) existing.remove();
      if (!message) return;
      var el = document.createElement('div');
      el.className = 'alert alert-danger campaign-wizard-step-error mt-3 mb-0';
      el.textContent = message;
      var body = panel.querySelector('.panel-card-body');
      if (body) body.prepend(el);
    }

    function validateStep(stepIndex) {
      var stepId = STEPS[stepIndex];
      var panel = panelFor(stepId);
      if (!panel) return true;

      showStepError(panel, '');

      var fields = panel.querySelectorAll('input, select, textarea');
      for (var i = 0; i < fields.length; i++) {
        var field = fields[i];
        if (field.type === 'hidden' || field.disabled) continue;
        if (field.offsetParent === null && field.type !== 'file') continue;
        if (!field.checkValidity()) {
          field.reportValidity();
          return false;
        }
      }

      if (stepId === 'basics') {
        var kind = document.getElementById('id_schedule_kind');
        if (kind && kind.value === 'scheduled') {
          var date = document.getElementById('id_jalali_scheduled_date');
          var time = document.getElementById('id_jalali_scheduled_time');
          if (date && !(date.value || '').trim()) {
            date.setCustomValidity('تاریخ ارسال را وارد کنید.');
            date.reportValidity();
            date.setCustomValidity('');
            return false;
          }
          if (time && !(time.value || '').trim()) {
            time.setCustomValidity('ساعت ارسال را وارد کنید.');
            time.reportValidity();
            time.setCustomValidity('');
            return false;
          }
        }
      }

      if (stepId === 'audience') {
        var mode = document.querySelector('input[name="audience_mode"]:checked');
        if (mode && mode.value === 'tags') {
          var tags = document.getElementById('id_target_tags');
          if (tags && tags.selectedOptions && tags.selectedOptions.length === 0) {
            showStepError(panel, 'حداقل یک دسته‌بندی انتخاب کنید.');
            return false;
          }
        }
      }

      if (stepId === 'content') {
        var ct = document.getElementById('id_content_type');
        var ctVal = ct ? ct.value : '';
        var mediaTypes = ['photo', 'video', 'document', 'voice'];
        if (mediaTypes.indexOf(ctVal) >= 0) {
          var mediaRoot = document.getElementById('campaign-media-widget');
          var hasExisting =
            mediaRoot && mediaRoot.dataset.hasExistingMedia === 'true';
          if (ctVal === 'video') {
            var uploadOk =
              mediaRoot &&
              (mediaRoot.dataset.pendingReady === 'true' ||
                mediaRoot.dataset.uploadOk === 'true' ||
                hasExisting);
            if (!uploadOk) {
              showStepError(panel, 'فایل ویدیو را انتخاب و آپلود کنید.');
              return false;
            }
          } else {
            var mediaInput = document.getElementById('id_media');
            var hasNewFile =
              mediaInput &&
              mediaInput.files &&
              mediaInput.files.length > 0;
            if (!hasExisting && !hasNewFile) {
              showStepError(panel, 'فایل را انتخاب کنید.');
              return false;
            }
          }
        } else if (ctVal === 'text') {
          var body = document.getElementById('id_body');
          if (body && !(body.value || '').trim()) {
            showStepError(panel, 'متن پیام را وارد کنید.');
            return false;
          }
        }
      }

      return true;
    }

    function goTo(stepIndex, options) {
      options = options || {};
      if (stepIndex < 0 || stepIndex >= STEPS.length) return;
      if (!options.skipValidation && stepIndex > current && !validateStep(current)) return;

      current = stepIndex;
      if (current > maxReached) maxReached = current;

      stepButtons.forEach(function (btn, idx) {
        var isActive = idx === current;
        var isDone = idx < current;
        btn.classList.toggle('is-active', isActive);
        btn.classList.toggle('is-done', isDone);
        btn.setAttribute('aria-current', isActive ? 'step' : 'false');
      });

      panels.forEach(function (panel, idx) {
        var isActive = idx === current;
        panel.classList.toggle('is-active', isActive);
        if (isActive) {
          panel.removeAttribute('hidden');
        } else {
          panel.setAttribute('hidden', '');
        }
      });

      if (btnPrev) btnPrev.hidden = current === 0;
      if (btnNext) btnNext.hidden = current === STEPS.length - 1;
      if (btnSubmit) btnSubmit.hidden = current !== STEPS.length - 1;

      if (progressText) {
        progressText.textContent = 'مرحله ' + (current + 1) + ' از ' + STEPS.length + ' — ' + STEP_LABELS[current];
      }

      var activePanel = panelFor(STEPS[current]);
      if (activePanel) {
        var focusable = activePanel.querySelector('input:not([type="hidden"]), select, textarea, button');
        if (focusable && options.focus !== false) {
          try { focusable.focus({ preventScroll: true }); } catch (e) { focusable.focus(); }
        }
      }

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (nav) {
      nav.addEventListener('click', function (e) {
        var btn = e.target.closest('.campaign-wizard-step');
        if (!btn) return;
        e.preventDefault();
        var idx = parseInt(btn.getAttribute('data-step-index'), 10);
        if (idx <= maxReached) {
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
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA' && current < STEPS.length - 1) {
        if (e.target.closest('#campaign-wizard-bar')) return;
        e.preventDefault();
        goTo(current + 1);
      }
    });

    form.addEventListener('submit', function (e) {
      if (form.classList.contains('is-saving')) {
        e.preventDefault();
        return;
      }
      if (current !== STEPS.length - 1) {
        e.preventDefault();
        goTo(STEPS.length - 1);
        return;
      }
      if (!validateStep(current)) {
        e.preventDefault();
        return;
      }
      setFormSaving(form, true);
    });

    function jumpToFirstError() {
      var hasAnyError = form.querySelector('.text-danger, .alert-danger');
      if (hasAnyError) {
        maxReached = STEPS.length - 1;
      }
      for (var i = 0; i < STEPS.length; i++) {
        var panel = panelFor(STEPS[i]);
        if (panel && panel.querySelector('.text-danger, .alert-danger')) {
          maxReached = Math.max(maxReached, i);
          goTo(i, { skipValidation: true, focus: false });
          return;
        }
      }
    }

    jumpToFirstError();
    if (current === 0 && maxReached === 0) {
      goTo(0, { skipValidation: true, focus: false });
    }
  }

  function initSchedule() {
    var kind = document.getElementById('id_schedule_kind');
    var boxes = document.querySelectorAll('.campaign-jalali-fields');
    var hint = document.getElementById('campaign-hint-schedule');
    if (!kind) return;

    function sync() {
      var scheduled = kind.value === 'scheduled';
      boxes.forEach(function (el) {
        el.style.display = scheduled ? '' : 'none';
        el.setAttribute('aria-hidden', scheduled ? 'false' : 'true');
      });
      if (hint) {
        hint.innerHTML = '<i class="bi bi-clock"></i>' + (scheduled ? 'زمان‌بندی‌شده' : 'ارسال فوری');
      }
    }

    kind.addEventListener('change', sync);
    sync();
  }

  function initAudience() {
    var radios = document.querySelectorAll('input[name="audience_mode"]');
    var tagsWrap = document.getElementById('campaign-target-tags-wrap');
    var hint = document.getElementById('campaign-hint-audience');
    if (!radios.length) return;

    function sync() {
      var mode = document.querySelector('input[name="audience_mode"]:checked');
      var isTags = mode && mode.value === 'tags';
      if (tagsWrap) {
        tagsWrap.style.display = isTags ? '' : 'none';
        tagsWrap.setAttribute('aria-hidden', isTags ? 'false' : 'true');
      }
      if (hint) {
        hint.innerHTML = '<i class="bi bi-people"></i>' + (isTags ? 'دسته‌های انتخابی' : 'همه کاربران');
      }
      document.querySelectorAll('.campaign-audience-option').forEach(function (opt) {
        var input = opt.querySelector('input[type="radio"]');
        opt.classList.toggle('is-selected', !!(input && input.checked));
      });
    }

    radios.forEach(function (radio) {
      radio.addEventListener('change', sync);
    });
    sync();
  }

  function initContentType() {
    var ctSel = document.getElementById('id_content_type');
    var mediaWrap = document.getElementById('campaign-media-wrap');
    var bodyLabel = document.getElementById('campaign-body-label');
    var bodyHint = document.getElementById('campaign-body-hint');
    var mediaLabel = document.getElementById('campaign-media-label');
    var mediaInput = document.getElementById('id_media');
    var videoInput = document.getElementById('campaign-video-file-input');
    if (!ctSel) return;

    var MEDIA_TYPES = ['photo', 'video', 'document', 'voice'];

    function sync() {
      var val = ctSel.value;
      var needsMedia = MEDIA_TYPES.indexOf(val) >= 0;
      if (mediaWrap) {
        if (needsMedia) {
          mediaWrap.removeAttribute('hidden');
        } else {
          mediaWrap.setAttribute('hidden', '');
        }
      }
      if (bodyLabel) {
        bodyLabel.textContent = needsMedia ? 'زیرنویس (اختیاری)' : 'متن پیام';
      }
      if (bodyHint) {
        bodyHint.textContent = needsMedia
          ? 'متن کوتاه زیر عکس، ویدیو یا فایل — اختیاری است.'
          : 'متن پیامی که برای مخاطبان ارسال می‌شود.';
      }
      if (mediaLabel) {
        if (val === 'photo') mediaLabel.textContent = 'فایل عکس';
        else if (val === 'video') mediaLabel.textContent = 'فایل ویدیو';
        else if (val === 'document') mediaLabel.textContent = 'فایل';
        else mediaLabel.textContent = 'فایل';
      }
      if (mediaInput) {
        if (val === 'photo') {
          mediaInput.setAttribute('accept', 'image/*,.jpg,.jpeg,.png,.webp,.gif');
        } else if (val === 'document') {
          mediaInput.setAttribute(
            'accept',
            '.pdf,.doc,.docx,.xls,.xlsx,.zip,.rar,.txt,.mp3,.ogg,.wav',
          );
        } else {
          mediaInput.removeAttribute('accept');
        }
      }
      if (videoInput && val === 'video') {
        videoInput.setAttribute(
          'accept',
          'video/*,.mkv,.mov,.webm,.mpeg,.mpg,.m4v,.avi,.mp4',
        );
      }
    }

    ctSel.addEventListener('change', sync);
    sync();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initWizard();
    initSchedule();
    initAudience();
    initContentType();
  });
})();
