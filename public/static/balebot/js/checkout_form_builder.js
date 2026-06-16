(function () {
  var FIELD_TYPES = [
    { id: 'text', label: 'متن' },
    { id: 'tel', label: 'تلفن' },
    { id: 'email', label: 'ایمیل' },
    { id: 'textarea', label: 'متن چندخطی' },
  ];

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function slugify(raw) {
    return String(raw || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_\u0600-\u06FF]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 64);
  }

  function defaultForm() {
    return {
      enabled: true,
      title: 'اطلاعات تحویل',
      fields: [
        { key: 'full_name', label: 'نام و نام خانوادگی', type: 'text', required: true, enabled: true },
        { key: 'phone', label: 'شماره تماس', type: 'tel', required: true, enabled: true },
        { key: 'email', label: 'ایمیل', type: 'email', required: false, enabled: false },
        { key: 'address', label: 'آدرس', type: 'textarea', required: true, enabled: true },
        { key: 'city', label: 'شهر', type: 'text', required: false, enabled: false },
        { key: 'postal_code', label: 'کد پستی', type: 'text', required: false, enabled: false },
        { key: 'note', label: 'توضیحات', type: 'textarea', required: false, enabled: false },
      ],
    };
  }

  function parseInitial() {
    var hidden = document.getElementById('id_checkout_form_json');
    if (!hidden || !hidden.value) return defaultForm();
    try {
      var data = JSON.parse(hidden.value);
      if (!data || !Array.isArray(data.fields)) return defaultForm();
      return data;
    } catch (e) {
      return defaultForm();
    }
  }

  function syncHidden(state) {
    var hidden = document.getElementById('id_checkout_form_json');
    if (hidden) hidden.value = JSON.stringify(state);
  }

  function renderFieldRow(tbody, field, index, onChange, isCustom) {
    var tr = document.createElement('tr');
    tr.dataset.index = String(index);

    var tdEnabled = document.createElement('td');
    var enabled = document.createElement('input');
    enabled.type = 'checkbox';
    enabled.className = 'form-check-input';
    enabled.checked = !!field.enabled;
    enabled.addEventListener('change', function () {
      field.enabled = enabled.checked;
      onChange();
    });
    tdEnabled.appendChild(enabled);

    var tdLabel = document.createElement('td');
    var label = document.createElement('input');
    label.type = 'text';
    label.className = 'form-control form-control-sm panel-input';
    label.value = field.label || '';
    label.addEventListener('input', function () {
      field.label = label.value;
      if (isCustom && !field.key) field.key = slugify(label.value);
      onChange();
    });
    tdLabel.appendChild(label);

    var tdType = document.createElement('td');
    var type = document.createElement('select');
    type.className = 'form-select form-select-sm panel-input';
    FIELD_TYPES.forEach(function (opt) {
      var o = document.createElement('option');
      o.value = opt.id;
      o.textContent = opt.label;
      if (field.type === opt.id) o.selected = true;
      type.appendChild(o);
    });
    type.addEventListener('change', function () {
      field.type = type.value;
      onChange();
    });
    tdType.appendChild(type);

    var tdRequired = document.createElement('td');
    var required = document.createElement('input');
    required.type = 'checkbox';
    required.className = 'form-check-input';
    required.checked = !!field.required;
    required.addEventListener('change', function () {
      field.required = required.checked;
      onChange();
    });
    tdRequired.appendChild(required);

    var tdActions = document.createElement('td');
    if (isCustom) {
      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'btn btn-sm btn-outline-danger';
      removeBtn.innerHTML = '<i class="bi bi-trash"></i>';
      removeBtn.addEventListener('click', function () {
        tr.remove();
        onChange(true);
      });
      tdActions.appendChild(removeBtn);
    }

    tr.appendChild(tdEnabled);
    tr.appendChild(tdLabel);
    tr.appendChild(tdType);
    tr.appendChild(tdRequired);
    tr.appendChild(tdActions);
    tbody.appendChild(tr);
    return field;
  }

  function collectFields(tbody) {
    var rows = tbody.querySelectorAll('tr');
    var fields = [];
    rows.forEach(function (row, idx) {
      var inputs = row.querySelectorAll('input, select');
      if (inputs.length < 4) return;
      var label = inputs[1].value.trim();
      if (!label) return;
      var key = row.dataset.key || slugify(label) || 'field_' + (idx + 1);
      fields.push({
        key: key,
        label: label,
        type: inputs[2].value || 'text',
        required: inputs[3].checked,
        enabled: inputs[0].checked,
      });
    });
    return fields;
  }

  function mount() {
    var hidden = document.getElementById('id_checkout_form_json');
    var tbody = document.getElementById('checkout-form-fields');
    var enabledToggle = document.getElementById('checkout-form-enabled');
    var titleInput = document.getElementById('checkout-form-title');
    var block = document.getElementById('checkout-form-block');
    var addBtn = document.getElementById('checkout-form-add-field');
    if (!hidden || !tbody || !enabledToggle || !titleInput) return;

    var state = parseInitial();
    enabledToggle.checked = !!state.enabled;
    titleInput.value = state.title || 'اطلاعات تحویل';

    function setBlockVisible(show) {
      if (!block) return;
      block.classList.toggle('settings-block-hidden', !show);
      block.setAttribute('aria-hidden', show ? 'false' : 'true');
    }

    function persist(removeRow) {
      if (removeRow) {
        state.fields = collectFields(tbody);
      }
      state.enabled = enabledToggle.checked;
      state.title = titleInput.value.trim() || 'اطلاعات تحویل';
      if (!removeRow) {
        state.fields = collectFields(tbody);
      }
      syncHidden(state);
    }

    function isCustomField(field) {
      var builtins = ['full_name', 'phone', 'email', 'address', 'city', 'postal_code', 'note'];
      return builtins.indexOf(field.key) < 0;
    }

    function renderAll() {
      tbody.innerHTML = '';
      (state.fields || []).forEach(function (field, index) {
        renderFieldRow(tbody, field, index, persist, isCustomField(field));
        var last = tbody.lastElementChild;
        if (last) last.dataset.key = field.key || '';
      });
      syncHidden(state);
    }

    renderAll();

    enabledToggle.addEventListener('change', function () {
      setBlockVisible(enabledToggle.checked);
      persist();
    });
    titleInput.addEventListener('input', persist);
    setBlockVisible(enabledToggle.checked);

    if (addBtn) {
      addBtn.addEventListener('click', function () {
        var field = {
          key: 'custom_' + Date.now(),
          label: 'فیلد جدید',
          type: 'text',
          required: false,
          enabled: true,
        };
        state.fields.push(field);
        var row = renderFieldRow(tbody, field, state.fields.length - 1, persist, true);
        row.key = field.key;
        var last = tbody.lastElementChild;
        if (last) last.dataset.key = field.key;
        persist();
      });
    }

    var form = document.getElementById('catalog-settings-form');
    if (form) {
      form.addEventListener('submit', function () {
        persist();
      });
    }
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
