(function () {
  function parseInitial() {
    var hidden = document.getElementById('id_metadata_json');
    if (!hidden || !(hidden.value || '').trim()) return [];
    try {
      var data = JSON.parse(hidden.value);
      if (Array.isArray(data)) {
        return data.map(function (row) {
          return {
            label: String(row.label || row.key || ''),
            value: String(row.value != null ? row.value : ''),
          };
        });
      }
      if (data && typeof data === 'object') {
        return Object.keys(data).map(function (key) {
          return { label: key, value: String(data[key]) };
        });
      }
    } catch (e) {
      /* ignore */
    }
    return [];
  }

  function syncHidden(rows) {
    var hidden = document.getElementById('id_metadata_json');
    if (!hidden) return;
    var out = {};
    rows.forEach(function (row) {
      var label = (row.label || '').trim();
      var value = (row.value || '').trim();
      if (label && value) out[label] = value;
    });
    hidden.value = JSON.stringify(out);
  }

  function renderRow(container, row, rows, onChange) {
    var wrap = document.createElement('div');
    wrap.className = 'metadata-builder-row';

    var labelInput = document.createElement('input');
    labelInput.type = 'text';
    labelInput.className = 'form-control panel-input metadata-builder-label';
    labelInput.placeholder = 'نام ویژگی (مثلاً وزن)';
    labelInput.value = row.label || '';
    labelInput.addEventListener('input', function () {
      row.label = labelInput.value;
      onChange();
    });

    var valueInput = document.createElement('input');
    valueInput.type = 'text';
    valueInput.className = 'form-control panel-input metadata-builder-value';
    valueInput.placeholder = 'مقدار (مثلاً ۵۰۰ گرم)';
    valueInput.value = row.value || '';
    valueInput.addEventListener('input', function () {
      row.value = valueInput.value;
      onChange();
    });

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn-panel-ghost btn-sm metadata-builder-remove';
    removeBtn.title = 'حذف';
    removeBtn.innerHTML = '<i class="bi bi-trash"></i>';
    removeBtn.addEventListener('click', function () {
      var idx = rows.indexOf(row);
      if (idx >= 0) rows.splice(idx, 1);
      wrap.remove();
      onChange();
      if (!rows.length) {
        rows.push({ label: '', value: '' });
        renderAll();
      }
    });

    wrap.appendChild(labelInput);
    wrap.appendChild(valueInput);
    wrap.appendChild(removeBtn);
    container.appendChild(wrap);
  }

  function mount() {
    var root = document.getElementById('metadata-builder');
    var container = document.getElementById('metadata-builder-rows');
    var addBtn = document.getElementById('metadata-add-row');
    if (!root || !container) return;

    var rows = parseInitial();
    if (!rows.length) rows.push({ label: '', value: '' });

    function persist() {
      syncHidden(rows);
    }

    function renderAll() {
      container.innerHTML = '';
      rows.forEach(function (row) {
        renderRow(container, row, rows, persist);
      });
      persist();
    }

    renderAll();

    if (addBtn) {
      addBtn.addEventListener('click', function () {
        rows.push({ label: '', value: '' });
        renderAll();
        var inputs = container.querySelectorAll('.metadata-builder-label');
        var last = inputs[inputs.length - 1];
        if (last) last.focus();
      });
    }

    var form = document.getElementById('catalog-item-form');
    if (form) {
      form.addEventListener('submit', function () {
        persist();
      });
    }
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
