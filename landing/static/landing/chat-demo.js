(function () {
  'use strict';

  /* ── Editable demo messages ── */
  var MESSAGES = [
    { from: 'user', text: 'سلام، می\u200cخوام فروشگاهم رو راه بندازم' },
    { from: 'bot', text: 'سلام \uD83D\uDC4B خوش اومدی! چند ثانیه\u200cای فروشگاهتو می\u200cسازیم.' },
    { from: 'bot', type: 'image', imageKey: 'demo', caption: 'این نمونه\u200cی ویترین فروشگاه ریحانی\u200cشاپه \uD83D\uDECD' },
    { from: 'bot', type: 'buttons', buttons: ['\uD83D\uDECD ورود به فروشگاه', '\uD83D\uDCE6 وضعیت سفارش', '\uD83D\uDCAC پشتیبانی'] },
    { from: 'user', text: 'پرداختش چطوریه؟' },
    { from: 'bot', text: 'کارت\u200cبه\u200cکارت، همون روشی که الان تو اینستاگرام هم داری. مشتری رسید می\u200cفرسته، سفارش ثبت می\u200cشه \u2705' },
  ];

  var root = document.querySelector('.chat-demo');
  if (!root) return;

  var thread = root.querySelector('.chat-demo-thread');
  var typingEl = root.querySelector('.chat-demo-typing');
  var demoImage = root.getAttribute('data-demo-image') || '';
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var timers = [];
  var running = true;

  function schedule(fn, ms) {
    var id = window.setTimeout(fn, ms);
    timers.push(id);
    return id;
  }

  function clearTimers() {
    timers.forEach(function (id) { window.clearTimeout(id); });
    timers = [];
  }

  function scrollToBottom() {
    if (!thread) return;
    thread.scrollTo({
      top: thread.scrollHeight,
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
    });
  }

  function showTyping() {
    if (!typingEl) return;
    typingEl.hidden = false;
    scrollToBottom();
  }

  function hideTyping() {
    if (!typingEl) return;
    typingEl.hidden = true;
  }

  function createBubble(msg) {
    var row = document.createElement('div');
    row.className = 'chat-msg-row chat-msg-row--' + msg.from;

    if (msg.type === 'buttons') {
      row.className = 'chat-msg-row chat-msg-row--bot chat-msg-row--buttons';
      var wrap = document.createElement('div');
      wrap.className = 'chat-bubble-buttons';
      msg.buttons.forEach(function (label) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chat-inline-btn';
        btn.textContent = label;
        btn.tabIndex = -1;
        wrap.appendChild(btn);
      });
      row.appendChild(wrap);
      return row;
    }

    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble--' + msg.from;

    if (msg.type === 'image') {
      bubble.classList.add('chat-bubble--image');
      var img = document.createElement('img');
      img.src = demoImage;
      img.alt = 'ویترین فروشگاه ریحانی\u200cشاپ';
      img.loading = 'lazy';
      img.width = 220;
      img.height = 140;
      bubble.appendChild(img);
      if (msg.caption) {
        var cap = document.createElement('p');
        cap.className = 'chat-bubble-caption';
        cap.textContent = msg.caption;
        bubble.appendChild(cap);
      }
    } else {
      bubble.textContent = msg.text;
    }

    row.appendChild(bubble);
    return row;
  }

  function appendMessage(msg, animate) {
    var el = createBubble(msg);
    if (animate && !prefersReducedMotion) {
      el.classList.add('chat-msg-enter');
    }
    thread.appendChild(el);
    if (animate && !prefersReducedMotion) {
      requestAnimationFrame(function () {
        el.classList.add('chat-msg-enter--visible');
      });
    }
    scrollToBottom();
  }

  function clearChat(cb) {
    if (prefersReducedMotion) {
      thread.innerHTML = '';
      if (cb) cb();
      return;
    }
    thread.classList.add('is-fading');
    schedule(function () {
      thread.innerHTML = '';
      thread.classList.remove('is-fading');
      if (cb) cb();
    }, 320);
  }

  function showAllInstant() {
    MESSAGES.forEach(function (msg) {
      appendMessage(msg, false);
    });
  }

  function runLoop() {
    if (!running) return;
    var i = 0;

    function next() {
      if (!running) return;
      if (i >= MESSAGES.length) {
        schedule(function () {
          clearChat(function () {
            i = 0;
            next();
          });
        }, 2500);
        return;
      }

      var msg = MESSAGES[i];

      if (msg.from === 'bot') {
        showTyping();
        schedule(function () {
          hideTyping();
          appendMessage(msg, true);
          i++;
          schedule(next, 600);
        }, 900);
      } else {
        appendMessage(msg, true);
        i++;
        schedule(next, 900);
      }
    }

    next();
  }

  if (prefersReducedMotion) {
    showAllInstant();
  } else {
    runLoop();
  }

  window.addEventListener('pagehide', function () {
    running = false;
    clearTimers();
  });
})();
