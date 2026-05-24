(function () {
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function setBlockVisible(block, show) {
    if (!block) return;
    block.classList.toggle('settings-block-hidden', !show);
    block.setAttribute('aria-hidden', show ? 'false' : 'true');
  }

  function bindToggle(checkboxId, blockId) {
    var cb = document.getElementById(checkboxId);
    var block = document.getElementById(blockId);
    if (!cb || !block) return;
    function sync() {
      setBlockVisible(block, cb.checked);
    }
    cb.addEventListener('change', sync);
    sync();
  }

  function initNav() {
    var links = $all('.settings-nav-link');
    var sections = $all('.settings-section');
    if (!links.length) return;

    function setActive(id) {
      links.forEach(function (a) {
        a.classList.toggle('active', a.getAttribute('data-settings-nav') === id);
      });
    }

    links.forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var id = a.getAttribute('data-settings-nav');
        var el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setActive(id);
        }
      });
    });

    if ('IntersectionObserver' in window && sections.length) {
      var obs = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting && entry.intersectionRatio > 0.2) {
              setActive(entry.target.id);
            }
          });
        },
        { rootMargin: '-20% 0px -55% 0px', threshold: [0, 0.2, 0.5] }
      );
      sections.forEach(function (sec) {
        obs.observe(sec);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindToggle('id_collect_contact_on_start', 'contact-fields-block');
    bindToggle('id_enable_support', 'support-fields-block');
    initNav();
  });
})();
