/**
 * انتخابگر تاریخ/زمان شمسی — vanilla JS
 * window.SepJalaliPicker.initAll(root)
 * window.SepJalaliPicker.jalaliToIso(dateStr, timeStr)
 */
(function (global) {
  'use strict';

  var FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
  var EN_DIGITS = '0123456789';

  function toEn(s) {
    return String(s || '')
      .split('')
      .map(function (ch) {
        var i = FA_DIGITS.indexOf(ch);
        return i >= 0 ? EN_DIGITS[i] : ch;
      })
      .join('')
      .trim();
  }

  function toFa(n) {
    return String(n).replace(/\d/g, function (d) {
      return FA_DIGITS[parseInt(d, 10)];
    });
  }

  function jalCal(jy) {
    var breaks = [
      -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192,
      2262, 2324, 2394, 2456, 3178,
    ];
    var bl = breaks.length;
    var gy = jy + 621;
    var leapJ = -14;
    var jp = breaks[0];
    var jm;
    var jump;
    var leap;
    var n;
    var i;
    if (jy < breaks[0] || jy >= breaks[bl - 1]) {
      return [0, 0];
    }
    for (i = 1; i < bl; i += 1) {
      jm = breaks[i];
      jump = jm - jp;
      if (jy < jm) break;
      leapJ += Math.floor(jump / 33) * 8 + Math.floor((jump % 33) / 4);
      jp = jm;
    }
    n = jy - jp;
    leapJ += Math.floor(n / 33) * 8 + Math.floor(((n % 33) + 3) / 4);
    if ((jump % 33) === 4 && jump - n === 4) leapJ += 1;
    leap = ((leapJ + 1) % 33) - 1;
    if (leap === -1) leap = 4;
    return [leap, gy];
  }

  function j2d(jy, jm, jd) {
    var r = jalCal(jy);
    var gy = jy <= 979 ? r[1] - 1 : r[1];
    var days =
      365 * (jy - 1) +
      Math.floor((jy - 1) / 33) * 8 +
      Math.floor((((jy - 1) % 33) + 3) / 4) +
      78 +
      jd +
      (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
    gy = 1600 + 400 * Math.floor(days / 146097);
    days %= 146097;
    if (days > 36524) {
      gy += 100 * Math.floor(--days / 36524);
      days %= 36524;
      if (days >= 365) days += 1;
    }
    gy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) {
      gy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    var gd = days + 1;
    var salA = [
      0, 31, (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31,
      31, 30, 31, 30, 31,
    ];
    var gm = 0;
    for (gm = 1; gm <= 12 && gd > salA[gm]; gm += 1) gd -= salA[gm];
    return [gy, gm, gd];
  }

  function d2j(gy, gm, gd) {
    var gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    var jy = gy <= 1600 ? 0 : 979;
    gy -= gy <= 1600 ? 621 : 1600;
    var gy2 = gm > 2 ? gy + 1 : gy;
    var days =
      365 * gy +
      Math.floor((gy2 + 3) / 4) -
      Math.floor((gy2 + 99) / 100) +
      Math.floor((gy2 + 399) / 400) -
      80 +
      gd +
      gdm[gm - 1];
    jy += 33 * Math.floor(days / 12053);
    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    var jm = days < 186 ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
    var jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);
    return [jy, jm, jd];
  }

  function todayJalali() {
    var n = new Date();
    return d2j(n.getFullYear(), n.getMonth() + 1, n.getDate());
  }

  function pad2(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function jalaliToIso(dateStr, timeStr) {
    var ds = toEn(dateStr).replace(/-/g, '/');
    var parts = ds.split('/').filter(Boolean);
    if (parts.length !== 3) return '';
    var jy = parseInt(parts[0], 10);
    var jm = parseInt(parts[1], 10);
    var jd = parseInt(parts[2], 10);
    var g = j2d(jy, jm, jd);
    var ts = toEn(timeStr || '00:00');
    var tm = ts.match(/^(\d{1,2}):(\d{2})/);
    var hh = tm ? parseInt(tm[1], 10) : 0;
    var mm = tm ? parseInt(tm[2], 10) : 0;
    return (
      g[0] +
      '-' +
      pad2(g[1]) +
      '-' +
      pad2(g[2]) +
      'T' +
      pad2(hh) +
      ':' +
      pad2(mm) +
      ':00'
    );
  }

  function isoToJalaliParts(iso) {
    if (!iso) return { date: '', time: '' };
    var m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})/);
    if (!m) return { date: '', time: '' };
    var j = d2j(parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10));
    return {
      date: j[0] + '/' + pad2(j[1]) + '/' + pad2(j[2]),
      time: m[4] + ':' + m[5],
    };
  }

  var MONTH_NAMES = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
  ];

  var activePopup = null;

  function closePopup() {
    if (activePopup && activePopup.parentNode) {
      activePopup.parentNode.removeChild(activePopup);
    }
    activePopup = null;
  }

  function monthLength(jy, jm) {
    if (jm <= 6) return 31;
    if (jm <= 11) return 30;
    return jalCal(jy)[0] === 0 ? 30 : 29;
  }

  function openDatePicker(input) {
    closePopup();
    var t = todayJalali();
    var cur = toEn(input.value).split('/');
    var jy = parseInt(cur[0], 10) || t[0];
    var jm = parseInt(cur[1], 10) || t[1];
    var jd = parseInt(cur[2], 10) || t[2];

    var popup = document.createElement('div');
    popup.className = 'sep-jalali-popup';
    activePopup = popup;

    function render() {
      popup.innerHTML = '';
      var head = document.createElement('div');
      head.className = 'sep-jalali-popup-head';
      var prev = document.createElement('button');
      prev.type = 'button';
      prev.className = 'sep-jalali-nav';
      prev.textContent = '‹';
      prev.addEventListener('click', function () {
        jm -= 1;
        if (jm < 1) {
          jm = 12;
          jy -= 1;
        }
        render();
      });
      var title = document.createElement('span');
      title.className = 'sep-jalali-popup-title';
      title.textContent = MONTH_NAMES[jm - 1] + ' ' + toFa(jy);
      var next = document.createElement('button');
      next.type = 'button';
      next.className = 'sep-jalali-nav';
      next.textContent = '›';
      next.addEventListener('click', function () {
        jm += 1;
        if (jm > 12) {
          jm = 1;
          jy += 1;
        }
        render();
      });
      head.appendChild(prev);
      head.appendChild(title);
      head.appendChild(next);
      popup.appendChild(head);

      var grid = document.createElement('div');
      grid.className = 'sep-jalali-grid';
      var len = monthLength(jy, jm);
      for (var d = 1; d <= len; d += 1) {
        (function (day) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'sep-jalali-day';
          if (day === jd && toEn(input.value)) btn.classList.add('is-selected');
          btn.textContent = toFa(day);
          btn.addEventListener('click', function () {
            input.value = jy + '/' + pad2(jm) + '/' + pad2(day);
            input.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
          });
          grid.appendChild(btn);
        })(d);
      }
      popup.appendChild(grid);
    }

    render();
    document.body.appendChild(popup);
    var rect = input.getBoundingClientRect();
    popup.style.top = rect.bottom + window.scrollY + 4 + 'px';
    popup.style.right = window.innerWidth - rect.right + 'px';
    popup.style.left = 'auto';
  }

  function initDateInput(input) {
    if (!input || input.dataset.sepJalaliInit) return;
    input.dataset.sepJalaliInit = '1';
    input.addEventListener('click', function () {
      openDatePicker(input);
    });
    input.addEventListener('focus', function () {
      openDatePicker(input);
    });
  }

  function initTimeInput(input) {
    if (!input || input.dataset.sepJalaliInit) return;
    input.dataset.sepJalaliInit = '1';
    input.setAttribute('inputmode', 'numeric');
    input.addEventListener('blur', function () {
      var v = toEn(input.value);
      var m = v.match(/^(\d{1,2}):(\d{2})$/);
      if (m) {
        var h = Math.min(23, parseInt(m[1], 10));
        var min = Math.min(59, parseInt(m[2], 10));
        input.value = pad2(h) + ':' + pad2(min);
      }
    });
  }

  function initAll(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-jalali-date]').forEach(initDateInput);
    scope.querySelectorAll('[data-jalali-time]').forEach(initTimeInput);
  }

  document.addEventListener('click', function (e) {
    if (!activePopup) return;
    if (e.target.closest('.sep-jalali-popup') || e.target.closest('[data-jalali-date]')) return;
    closePopup();
  });

  global.SepJalaliPicker = {
    initAll: initAll,
    initDate: initDateInput,
    initTime: initTimeInput,
    jalaliToIso: jalaliToIso,
    isoToJalaliParts: isoToJalaliParts,
    toEn: toEn,
  };
})(window);
