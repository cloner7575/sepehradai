(function () {
  const form = document.getElementById('ig-flow-form');
  const stage = document.getElementById('ig-flow-stage');
  const hidden = document.getElementById('flow-definition');
  if (!form || !stage || !hidden) return;

  let state = window.IG_FLOW_INITIAL || { nodes: [], edges: [], entry: '' };
  if (!state.nodes) state.nodes = [];
  if (!state.edges) state.edges = [];
  let dirty = false;
  let selected = null;
  let drag = null;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.classList.add('ig-flow-svg');
  stage.appendChild(svg);

  function uid() {
    return 'n' + Math.random().toString(36).slice(2, 9);
  }

  function syncHidden() {
    hidden.value = JSON.stringify(state);
  }

  function drawEdges() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    state.edges.forEach(function (e) {
      const a = state.nodes.find((n) => n.id === e.source);
      const b = state.nodes.find((n) => n.id === e.target);
      if (!a || !b) return;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', a.x + 90);
      line.setAttribute('y1', a.y + 40);
      line.setAttribute('x2', b.x + 90);
      line.setAttribute('y2', b.y);
      line.setAttribute('stroke', '#6338D9');
      line.setAttribute('stroke-width', '2');
      svg.appendChild(line);
    });
  }

  function render() {
    stage.querySelectorAll('.ig-flow-node').forEach((n) => n.remove());
    state.nodes.forEach(function (n) {
      const el = document.createElement('div');
      el.className = 'ig-flow-node' + (selected === n.id ? ' is-selected' : '');
      el.style.left = (n.x || 40) + 'px';
      el.style.top = (n.y || 40) + 'px';
      el.dataset.id = n.id;
      el.innerHTML =
        '<div class="ig-flow-node__type">' +
        (n.type || '') +
        '</div><div contenteditable="true" class="ig-flow-node__label"></div>';
      el.querySelector('.ig-flow-node__label').textContent =
        (n.config && n.config.text) || n.type || '';
      el.addEventListener('mousedown', function (ev) {
        if (ev.target.classList.contains('ig-flow-node__label')) return;
        selected = n.id;
        drag = { id: n.id, ox: ev.clientX - n.x, oy: ev.clientY - n.y };
        render();
      });
      el.querySelector('.ig-flow-node__label').addEventListener('input', function (ev) {
        n.config = n.config || {};
        n.config.text = ev.target.textContent;
        dirty = true;
        syncHidden();
      });
      stage.appendChild(el);
    });
    drawEdges();
    syncHidden();
  }

  stage.addEventListener('mousemove', function (ev) {
    if (!drag) return;
    const n = state.nodes.find((x) => x.id === drag.id);
    if (!n) return;
    n.x = Math.max(0, ev.clientX - drag.ox);
    n.y = Math.max(0, ev.clientY - drag.oy);
    dirty = true;
    render();
  });
  window.addEventListener('mouseup', function () {
    drag = null;
  });

  document.querySelectorAll('[data-add]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const type = btn.getAttribute('data-add');
      const id = uid();
      const node = {
        id: id,
        type: type,
        x: 40 + state.nodes.length * 30,
        y: 80 + state.nodes.length * 40,
        config: type === 'send_text' ? { text: 'متن پیام' } : {},
      };
      if (!state.nodes.length) state.entry = id;
      if (state.nodes.length) {
        const prev = state.nodes[state.nodes.length - 1];
        state.edges.push({ source: prev.id, target: id });
      }
      state.nodes.push(node);
      dirty = true;
      render();
    });
  });

  form.addEventListener('submit', function () {
    syncHidden();
    dirty = false;
  });

  window.addEventListener('beforeunload', function (e) {
    if (!dirty) return;
    e.preventDefault();
    e.returnValue = '';
  });

  // autosave every 30s via AJAX if editing existing
  setInterval(function () {
    if (!dirty || !form.action) return;
    syncHidden();
    const fd = new FormData(form);
    fetch(form.action || window.location.href, {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    }).then(function (r) {
      return r.json();
    }).then(function (j) {
      if (j && j.ok) dirty = false;
    }).catch(function () {});
  }, 30000);

  render();
})();
