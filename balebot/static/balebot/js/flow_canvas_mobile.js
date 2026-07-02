(function (global) {
  'use strict';

  var MOBILE_MQ = '(max-width: 991.98px)';
  var LONG_PRESS_MS = 380;
  var MOVE_TOLERANCE_PX = 12;
  var BODY_CLASS = 'app-body--flow-studio';

  function isMobile() {
    return window.matchMedia(MOBILE_MQ).matches;
  }

  function getParts(root) {
    return {
      add: root.querySelector('.bot-studio-dock') || root.querySelector('.miniapp-editor-sidebar'),
      preview: root.querySelector('.flow-canvas-stage'),
      inspect: root.querySelector('.flow-canvas-inspector'),
      fab: root.querySelector('.flow-studio-fab'),
      backdrop: root.querySelector('.flow-studio-mobile-backdrop'),
      coach: root.querySelector('.flow-studio-mobile-coach'),
    };
  }

  function mount(root) {
    if (!root) return null;

    var openSheetName = null;
    var coachDismissed = false;

    try {
      coachDismissed = localStorage.getItem('flow-studio-coach-dismissed') === '1';
    } catch (storageErr) {
      coachDismissed = false;
    }

    function setBodyClass(on) {
      document.body.classList.toggle(BODY_CLASS, on);
    }

    function updateSheetClasses() {
      root.classList.toggle('flow-sheet-open', !!openSheetName);
      root.classList.toggle('flow-sheet-open--add', openSheetName === 'add');
      root.classList.toggle('flow-sheet-open--inspect', openSheetName === 'inspect');
      var parts = getParts(root);
      if (parts.backdrop) parts.backdrop.hidden = !openSheetName;
      if (parts.fab) {
        parts.fab.classList.toggle('is-active', openSheetName === 'add');
        parts.fab.setAttribute('aria-expanded', openSheetName === 'add' ? 'true' : 'false');
      }
      if (isMobile()) {
        document.body.style.overflow = openSheetName ? 'hidden' : '';
      }
    }

    function openSheet(name) {
      if (!isMobile() || !name) return;
      openSheetName = name;
      root.setAttribute('data-mobile-panel', 'preview');
      updateSheetClasses();
      if (name === 'inspect') {
        var parts = getParts(root);
        if (parts.inspect) {
          window.requestAnimationFrame(function () {
            var body = parts.inspect.querySelector('.flow-canvas-inspector-body');
            if (body) body.scrollTop = 0;
          });
        }
      }
    }

    function closeSheet() {
      openSheetName = null;
      root.setAttribute('data-mobile-panel', 'preview');
      updateSheetClasses();
    }

    function toggleAddSheet() {
      if (openSheetName === 'add') closeSheet();
      else openSheet('add');
    }

    function dismissCoach() {
      coachDismissed = true;
      try {
        localStorage.setItem('flow-studio-coach-dismissed', '1');
      } catch (storageErr) {
        /* ignore */
      }
      var parts = getParts(root);
      if (parts.coach) parts.coach.hidden = true;
    }

    function updateCoach() {
      var parts = getParts(root);
      if (!parts.coach) return;
      parts.coach.hidden = !isMobile() || coachDismissed;
    }

    function updateMode() {
      var mobile = isMobile();
      root.classList.toggle('flow-canvas-editor--mobile', mobile);
      setBodyClass(mobile);

      var parts = getParts(root);
      if (parts.fab) parts.fab.hidden = !mobile;
      if (!mobile) {
        closeSheet();
        document.body.style.overflow = '';
        root.removeAttribute('data-mobile-panel');
      } else {
        root.setAttribute('data-mobile-panel', 'preview');
        updateCoach();
      }
      updateSheetClasses();
    }

    var parts = getParts(root);

    if (parts.fab) {
      parts.fab.addEventListener('click', function (e) {
        e.preventDefault();
        toggleAddSheet();
      });
    }

    if (parts.backdrop) {
      parts.backdrop.addEventListener('click', closeSheet);
    }

    root.querySelectorAll('[data-flow-sheet-close]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        closeSheet();
      });
    });

    var coachDismiss = root.querySelector('[data-flow-coach-dismiss]');
    if (coachDismiss) {
      coachDismiss.addEventListener('click', function (e) {
        e.preventDefault();
        dismissCoach();
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && openSheetName) closeSheet();
    });

    if (window.matchMedia(MOBILE_MQ).addEventListener) {
      window.matchMedia(MOBILE_MQ).addEventListener('change', updateMode);
    } else {
      window.matchMedia(MOBILE_MQ).addListener(updateMode);
    }

    updateMode();

    return {
      onSelection: function () {
        if (isMobile()) openSheet('inspect');
      },
      onClearSelection: function () {
        if (isMobile() && openSheetName === 'inspect') closeSheet();
      },
      onItemAdded: function () {
        if (isMobile() && openSheetName === 'add') closeSheet();
      },
      openAdd: function () {
        if (isMobile()) openSheet('add');
      },
      closeSheet: closeSheet,
      openSheet: openSheet,
      setPanel: function () {
        /* legacy no-op: canvas always visible */
      },
      isMobile: isMobile,
      suggestAddIfEmpty: function (count) {
        if (!isMobile() || coachDismissed) return;
        if (count === 0) openSheet('add');
      },
    };
  }

  function attachTouchSelectOrDrag(el, options) {
    if (!el || !options) return;

    var onTap = options.onTap;
    var onStartDrag = options.onStartDrag;
    var ignoreSelector = options.ignoreSelector || '';
    var touchState = null;

    function shouldIgnore(target) {
      if (!target) return true;
      if (ignoreSelector && target.closest(ignoreSelector)) return true;
      return false;
    }

    function clearTouchState() {
      if (!touchState) return;
      if (touchState.timer) clearTimeout(touchState.timer);
      touchState.el.classList.remove('is-long-press-pending', 'is-long-press-drag');
      touchState = null;
    }

    el.addEventListener(
      'touchstart',
      function (e) {
        if (!isMobile() || !e.touches.length) return;
        if (shouldIgnore(e.target)) return;

        var t = e.touches[0];
        clearTouchState();

        var node = el;
        touchState = {
          el: node,
          x: t.clientX,
          y: t.clientY,
          dragStarted: false,
          timer: setTimeout(function () {
            if (!touchState || touchState.el !== node) return;
            touchState.dragStarted = true;
            touchState.timer = null;
            node.classList.remove('is-long-press-pending');
            node.classList.add('is-long-press-drag');
            try {
              if (navigator.vibrate) navigator.vibrate(12);
            } catch (vibrateErr) {
              /* ignore */
            }
            if (onStartDrag) onStartDrag(touchState.x, touchState.y);
          }, LONG_PRESS_MS),
        };
        node.classList.add('is-long-press-pending');
      },
      { passive: true }
    );

    el.addEventListener(
      'touchmove',
      function (e) {
        if (!touchState || touchState.dragStarted || !e.touches.length) return;
        var t = e.touches[0];
        var dx = Math.abs(t.clientX - touchState.x);
        var dy = Math.abs(t.clientY - touchState.y);
        if (dx > MOVE_TOLERANCE_PX || dy > MOVE_TOLERANCE_PX) {
          clearTouchState();
        }
      },
      { passive: true }
    );

    el.addEventListener('touchend', function () {
      if (!touchState) return;
      var wasDrag = touchState.dragStarted;
      var node = touchState.el;
      clearTouchState();
      if (wasDrag) return;
      if (onTap) {
        node._flowSkipClick = true;
        onTap();
      }
    });

    el.addEventListener('touchcancel', clearTouchState);
  }

  function shouldSkipClick(el) {
    if (!el || !el._flowSkipClick) return false;
    el._flowSkipClick = false;
    return true;
  }

  global.FlowCanvasMobile = {
    mount: mount,
    isMobile: isMobile,
    attachTouchSelectOrDrag: attachTouchSelectOrDrag,
    shouldSkipClick: shouldSkipClick,
  };
})(window);
