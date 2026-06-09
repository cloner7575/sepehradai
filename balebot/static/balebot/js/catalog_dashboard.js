(function () {
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-copy-target]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-copy-target');
        var el = document.getElementById(id);
        if (!el) return;
        var text = (el.textContent || '').trim();
        copyText(text).then(function () {
          var orig = btn.innerHTML;
          btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>کپی شد';
          setTimeout(function () {
            btn.innerHTML = orig;
          }, 1800);
        });
      });
    });
  });
})();
