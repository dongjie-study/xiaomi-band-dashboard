/* ============================================================
   ux-polish.js —— 渐进增强脚本（只加 class，不碰任何业务 JS）
   1) 滚动显现：给卡片/表格/区块加 .ux-in
   2) 失败安全：2.5s 后强制全部可见，JS/IO 出问题也不会藏内容
   3) 尊重 prefers-reduced-motion
   ============================================================ */
(function () {
  'use strict';
  if (window.__UX_POLISH__) return;
  window.__UX_POLISH__ = true;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) return;

  var SELECTOR = '.card, .panel, .kpi-card, .stat-card, .module-card, .room-card, .chart-box, .section, .section-card, table';

  function revealAll() {
    document.querySelectorAll(SELECTOR).forEach(function (el) {
      el.classList.add('ux-in');
    });
  }

  try {
    document.documentElement.classList.add('ux-reveal');

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('ux-in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '40px 0px -8% 0px', threshold: 0.02 });

    var observeAll = function () {
      document.querySelectorAll(SELECTOR).forEach(function (el) {
        if (!el.classList.contains('ux-in')) io.observe(el);
      });
    };
    observeAll();

    /* 动态内容（模块渲染/切 tab 后插入的节点）也纳入 */
    if ('MutationObserver' in window) {
      new MutationObserver(function () {
        observeAll();
      }).observe(document.body, { childList: true, subtree: true });
    }

    /* 失败安全：无论如何 2.5s 后全部显示 */
    setTimeout(revealAll, 2500);
    window.addEventListener('load', function () { setTimeout(observeAll, 100); });
  } catch (e) {
    revealAll();
  }
})();
