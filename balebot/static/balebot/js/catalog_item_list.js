(function () {
  'use strict';

  var searchInput = document.querySelector('.catalog-shop-search input[type="search"]');
  if (searchInput) {
    var form = searchInput.closest('form');
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        form.requestSubmit();
      }
    });
  }

  document.querySelectorAll('.catalog-shop-type-select').forEach(function (sel) {
    sel.addEventListener('change', function () {
      if (sel.value) {
        window.location.href = sel.value;
      }
    });
  });
})();
