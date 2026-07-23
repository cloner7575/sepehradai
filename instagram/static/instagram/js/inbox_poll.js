(function () {
  const root = document.getElementById('ig-chat');
  if (!root) return;
  const url = root.dataset.pollUrl;
  let lastId = 0;
  root.querySelectorAll('[data-id]').forEach(function (el) {
    lastId = Math.max(lastId, parseInt(el.dataset.id, 10) || 0);
  });

  async function poll() {
    try {
      const r = await fetch(url + '?after=' + lastId, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const j = await r.json();
      if (!j.ok) return;
      (j.messages || []).forEach(function (m) {
        lastId = Math.max(lastId, m.id);
        const div = document.createElement('div');
        div.className = 'ig-bubble ig-bubble--' + m.direction;
        div.dataset.id = m.id;
        div.innerHTML =
          '<div class="small text-muted">' +
          m.sender_type +
          '</div><div></div>';
        div.querySelector('div:last-child').textContent = m.text || '';
        root.appendChild(div);
        root.scrollTop = root.scrollHeight;
      });
    } catch (e) {}
  }
  setInterval(poll, 5000);
})();
