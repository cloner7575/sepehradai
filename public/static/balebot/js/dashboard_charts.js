(function () {
  'use strict';

  var dataEl = document.getElementById('dashboard-chart-data');
  if (!dataEl || typeof Chart === 'undefined') return;

  var charts;
  try {
    charts = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }

  function cssVar(name, fallback) {
    var val = getComputedStyle(document.body).getPropertyValue(name).trim();
    return val || fallback;
  }

  function isDark() {
    return document.body.classList.contains('app-dark');
  }

  function theme() {
    var dark = isDark();
    return {
      text: cssVar('--app-text', dark ? '#e8e8ea' : '#1a1a1e'),
      muted: cssVar('--app-muted', dark ? '#9898a0' : '#6b6b76'),
      border: cssVar('--app-border', dark ? '#2a2a30' : '#e4e4ea'),
      primary: cssVar('--app-primary', '#2563eb'),
      success: cssVar('--app-success', '#16a34a'),
      warning: cssVar('--app-warning', '#d97706'),
      info: cssVar('--app-info', '#0284c7'),
      danger: cssVar('--app-danger', '#dc2626'),
      grid: dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      surface: cssVar('--app-surface', dark ? '#111113' : '#ffffff'),
    };
  }

  function primaryFill() {
    var rgb = cssVar('--app-primary-rgb', '37, 99, 235');
    return 'rgba(' + rgb + ', 0.14)';
  }

  function palette() {
    var t = theme();
        return [t.primary, t.success, t.warning, t.info, t.danger, '#8b5cf6', '#ec4899', '#14b8a6'];
  }

  function baseOptions(extra) {
    var t = theme();
    var opts = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: t.muted,
            font: { family: 'inherit', size: 12 },
            padding: 14,
          },
        },
        tooltip: {
          rtl: true,
          textDirection: 'rtl',
          titleFont: { family: 'inherit' },
          bodyFont: { family: 'inherit' },
          backgroundColor: t.surface,
          titleColor: t.text,
          bodyColor: t.text,
          borderColor: t.border,
          borderWidth: 1,
        },
      },
      scales: extra && extra.scales ? extra.scales : undefined,
    };
    return opts;
  }

  function axisScales() {
    var t = theme();
    return {
      x: {
        ticks: { color: t.muted, font: { family: 'inherit', size: 11 } },
        grid: { color: t.grid },
        border: { color: t.border },
      },
      y: {
        ticks: { color: t.muted, font: { family: 'inherit', size: 11 } },
        grid: { color: t.grid },
        border: { color: t.border },
        beginAtZero: true,
      },
    };
  }

  function formatToman(n) {
    return Number(n || 0).toLocaleString('fa-IR') + ' ت';
  }

  var instances = [];

  function destroyAll() {
    instances.forEach(function (c) { c.destroy(); });
    instances = [];
  }

  function render() {
    destroyAll();
    var t = theme();
    var colors = palette();

    var revenueEl = document.getElementById('chart-revenue');
    if (revenueEl && charts.daily_labels) {
      instances.push(new Chart(revenueEl, {
        type: 'line',
        data: {
          labels: charts.daily_labels,
          datasets: [
            {
              label: 'درآمد (تومان)',
              data: charts.daily_revenue_toman,
              borderColor: t.primary,
              backgroundColor: primaryFill(),
              fill: true,
              tension: 0.35,
              pointRadius: 2,
              pointHoverRadius: 5,
              borderWidth: 2,
              yAxisID: 'y',
            },
            {
              label: 'سفارش پرداخت‌شده',
              data: charts.daily_paid_count,
              borderColor: t.success,
              backgroundColor: 'transparent',
              tension: 0.35,
              pointRadius: 2,
              borderWidth: 2,
              yAxisID: 'y1',
            },
          ],
        },
        options: Object.assign(baseOptions(), {
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: baseOptions().plugins.legend,
            tooltip: Object.assign({}, baseOptions().plugins.tooltip, {
              callbacks: {
                label: function (ctx) {
                  if (ctx.datasetIndex === 0) return 'درآمد: ' + formatToman(ctx.raw);
                  return 'پرداخت‌شده: ' + Number(ctx.raw).toLocaleString('fa-IR');
                },
              },
            }),
          },
          scales: {
            x: axisScales().x,
            y: Object.assign({}, axisScales().y, {
              position: 'right',
              ticks: {
                color: t.muted,
                font: { family: 'inherit', size: 11 },
                callback: function (v) { return formatToman(v); },
              },
            }),
            y1: {
              position: 'left',
              ticks: { color: t.muted, font: { family: 'inherit', size: 11 }, stepSize: 1 },
              grid: { drawOnChartArea: false },
              border: { color: t.border },
              beginAtZero: true,
            },
          },
        }),
      }));
    }

    var ordersEl = document.getElementById('chart-orders');
    if (ordersEl && charts.daily_labels) {
      instances.push(new Chart(ordersEl, {
        type: 'bar',
        data: {
          labels: charts.daily_labels,
          datasets: [{
            label: 'سفارش جدید',
            data: charts.daily_order_count,
            backgroundColor: colors.map(function (c) { return c; }),
            borderRadius: 6,
            maxBarThickness: 28,
          }],
        },
        options: Object.assign(baseOptions(), { scales: axisScales() }),
      }));
    }

    var statusEl = document.getElementById('chart-status');
    if (statusEl && charts.status_labels && charts.status_labels.length) {
      instances.push(new Chart(statusEl, {
        type: 'doughnut',
        data: {
          labels: charts.status_labels,
          datasets: [{
            data: charts.status_values,
            backgroundColor: colors.slice(0, charts.status_labels.length),
            borderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: Object.assign(baseOptions(), {
          cutout: '62%',
          plugins: Object.assign({}, baseOptions().plugins, {
            legend: { position: 'bottom', labels: baseOptions().plugins.legend.labels },
          }),
        }),
      }));
    }

    var fulfillmentEl = document.getElementById('chart-fulfillment');
    if (fulfillmentEl && charts.fulfillment_labels && charts.fulfillment_labels.length) {
      instances.push(new Chart(fulfillmentEl, {
        type: 'doughnut',
        data: {
          labels: charts.fulfillment_labels,
          datasets: [{
            data: charts.fulfillment_values,
            backgroundColor: [t.warning, t.info, t.success, t.primary, t.muted, t.danger],
            borderWidth: 0,
            hoverOffset: 6,
          }],
        },
        options: Object.assign(baseOptions(), {
          cutout: '62%',
          plugins: Object.assign({}, baseOptions().plugins, {
            legend: { position: 'bottom', labels: baseOptions().plugins.legend.labels },
          }),
        }),
      }));
    }

    var topEl = document.getElementById('chart-top-items');
    if (topEl && charts.top_item_labels && charts.top_item_labels.length) {
      instances.push(new Chart(topEl, {
        type: 'bar',
        data: {
          labels: charts.top_item_labels,
          datasets: [{
            label: 'تعداد فروش',
            data: charts.top_item_qty,
            backgroundColor: t.primary,
            borderRadius: 6,
            maxBarThickness: 22,
          }],
        },
        options: Object.assign(baseOptions(), {
          indexAxis: 'y',
          scales: {
            x: axisScales().y,
            y: Object.assign({}, axisScales().x, { grid: { display: false } }),
          },
          plugins: Object.assign({}, baseOptions().plugins, {
            legend: { display: false },
          }),
        }),
      }));
    }

    var funnelEl = document.getElementById('chart-funnel');
    if (funnelEl && charts.funnel_labels) {
      instances.push(new Chart(funnelEl, {
        type: 'bar',
        data: {
          labels: charts.funnel_labels,
          datasets: [{
            label: 'تعداد',
            data: charts.funnel_values,
            backgroundColor: [t.info, t.warning, t.success],
            borderRadius: 8,
            maxBarThickness: 48,
          }],
        },
        options: Object.assign(baseOptions(), {
          scales: axisScales(),
          plugins: Object.assign({}, baseOptions().plugins, {
            legend: { display: false },
          }),
        }),
      }));
    }
  }

  render();

  var themeToggle = document.getElementById('app-theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      setTimeout(render, 50);
    });
  }
})();
