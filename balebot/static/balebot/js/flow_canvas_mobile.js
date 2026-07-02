(function (global) {
  'use strict';

  var MOBILE_MQ = '(max-width: 991.98px)';

  function isMobile() {
    return window.matchMedia(MOBILE_MQ).matches;
  }

  function getPanelEls(root) {
    return {
      add: root.querySelector('.bot-studio-dock') || root.querySelector('.miniapp-editor-sidebar'),
      preview: root.querySelector('.flow-canvas-stage'),
      inspect: root.querySelector('.flow-canvas-inspector'),
      nav: root.querySelector('.flow-studio-mobile-nav'),
    };
  }

  function setPanel(root, panel) {
    if (!panel) return;
    root.setAttribute('data-mobile-panel', panel);
    var parts = getPanelEls(root);
    if (parts.nav) {
      parts.nav.querySelectorAll('[data-mobile-tab]').forEach(function (btn) {
        var active = btn.getAttribute('data-mobile-tab') === panel;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
      });
    }
    if (panel === 'inspect' && parts.inspect && isMobile()) {
      window.requestAnimationFrame(function () {
        parts.inspect.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  }

  function mount(root) {
    if (!root) return null;
    var nav = root.querySelector('.flow-studio-mobile-nav');
    if (!nav) return null;

    function updateMode() {
      var mobile = isMobile();
      nav.hidden = !mobile;
      root.classList.toggle('flow-canvas-editor--mobile', mobile);
      if (mobile) {
        if (!root.getAttribute('data-mobile-panel')) {
          setPanel(root, 'preview');
        }
      } else {
        root.removeAttribute('data-mobile-panel');
      }
    }

    nav.querySelectorAll('[data-mobile-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tab = btn.getAttribute('data-mobile-tab');
        if (tab) setPanel(root, tab);
      });
    });

    if (window.matchMedia(MOBILE_MQ).addEventListener) {
      window.matchMedia(MOBILE_MQ).addEventListener('change', updateMode);
    } else {
      window.matchMedia(MOBILE_MQ).addListener(updateMode);
    }
    updateMode();

    return {
      onSelection: function () {
        if (isMobile()) setPanel(root, 'inspect');
      },
      setPanel: function (panel) {
        setPanel(root, panel);
      },
      isMobile: isMobile,
    };
  }

  global.FlowCanvasMobile = { mount: mount, isMobile: isMobile };

  var LONG_PRESS_MS = 450;
  var MOVE_TOLERANCE_PX = 12;

  /**
   * Mobile: short tap → onTap (select / inspector)
   *         hold → onStartDrag (reorder)
   */
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
              if (navigator.vibrate) navigator.vibrate(15);
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

  global.FlowCanvasMobile.attachTouchSelectOrDrag = attachTouchSelectOrDrag;
  global.FlowCanvasMobile.shouldSkipClick = shouldSkipClick;
})(window);
