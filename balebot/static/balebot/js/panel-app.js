(function () {
  'use strict';

  var body = document.getElementById('app-body') || document.body;
  var backdrop = document.getElementById('app-backdrop');
  var sidebarToggle = document.getElementById('app-sidebar-toggle');
  var sidebarCollapse = document.getElementById('app-sidebar-collapse');
  var themeToggle = document.getElementById('app-theme-toggle');
  var platformForm = document.getElementById('app-platform-form');
  var platformInput = document.getElementById('app-platform-input');

  function isMobileNav() {
    return window.matchMedia('(max-width: 991.98px)').matches;
  }

  function setSidebarOpen(open) {
    body.classList.toggle('app-sidebar-open', open);
    body.style.overflow = open ? 'hidden' : '';
    if (sidebarToggle) {
      sidebarToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function () {
      setSidebarOpen(!body.classList.contains('app-sidebar-open'));
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', function () {
      setSidebarOpen(false);
    });
  }

  if (sidebarCollapse) {
    sidebarCollapse.addEventListener('click', function () {
      body.classList.toggle('app-sidebar-collapsed');
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') setSidebarOpen(false);
  });

  document.querySelectorAll('#panel-sidebar a').forEach(function (link) {
    link.addEventListener('click', function () {
      if (isMobileNav()) setSidebarOpen(false);
    });
  });

  window.addEventListener('resize', function () {
    if (!isMobileNav()) setSidebarOpen(false);
  });

  if (platformForm && platformInput) {
    platformForm.querySelectorAll('.app-platform-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var value = btn.getAttribute('data-platform');
        if (!value || value === platformInput.value) return;
        platformInput.value = value;
        platformForm.submit();
      });
    });
  }

  if (themeToggle) {
    var stored = localStorage.getItem('app-theme');
    if (stored === 'dark') body.classList.add('app-dark');
    themeToggle.addEventListener('click', function () {
      body.classList.toggle('app-dark');
      localStorage.setItem('app-theme', body.classList.contains('app-dark') ? 'dark' : 'light');
      var icon = themeToggle.querySelector('i');
      if (icon) {
        icon.className = body.classList.contains('app-dark') ? 'bi bi-sun' : 'bi bi-moon-stars';
      }
    });
    var icon = themeToggle.querySelector('i');
    if (icon && body.classList.contains('app-dark')) {
      icon.className = 'bi bi-sun';
    }
  }

  var canvasHub = document.getElementById('flow-canvas-hub');
  if (canvasHub) {
    var tabs = canvasHub.querySelectorAll('.flow-canvas-tab');
    var panes = canvasHub.querySelectorAll('.flow-canvas-pane');
    var footMetas = canvasHub.querySelectorAll('.flow-canvas-foot-meta');
    var actions = canvasHub.querySelectorAll('.flow-canvas-action');

    function activateCanvas(name) {
      tabs.forEach(function (tab) {
        var active = tab.getAttribute('data-canvas-target') === name;
        tab.classList.toggle('is-active', active);
        tab.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      panes.forEach(function (pane) {
        var active = pane.getAttribute('data-canvas-pane') === name;
        pane.classList.toggle('is-active', active);
        pane.hidden = !active;
      });
      footMetas.forEach(function (meta) {
        var show = meta.classList.contains('flow-canvas-foot-meta--' + name);
        meta.hidden = !show;
      });
      actions.forEach(function (action) {
        var show = action.classList.contains('flow-canvas-action--' + name);
        action.hidden = !show;
      });
    }

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var target = tab.getAttribute('data-canvas-target');
        if (target) activateCanvas(target);
      });
    });
  }
})();
