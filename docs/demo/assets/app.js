(function () {
  var A = window.ALBUM, root = document.documentElement;
  Object.keys(A.theme).forEach(function (k) { root.style.setProperty('--' + k, A.theme[k]); });

  // QA 钩子：qa.py 读取这些全局量
  var stats = window.__albumStats = { total: A.pages.length, loaded: 0, failed: [] };
  var loadingN = document.getElementById('loading-n');

  function preload(p) {
    return new Promise(function (res) {
      var im = new Image();
      im.onload = function () { stats.loaded++; loadingN.textContent = stats.loaded; res(); };
      im.onerror = function () { stats.failed.push(p.src); res(); };
      im.src = p.src;
    });
  }

  Promise.all(A.pages.map(preload)).then(init);

  function init() {
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var pf = new St.PageFlip(document.getElementById('book'), {
      width: A.pageWidth, height: A.pageHeight, size: 'stretch',
      minWidth: 340, maxWidth: A.pageWidth, minHeight: 453, maxHeight: A.pageHeight,
      usePortrait: true, showCover: false, drawShadow: true, maxShadowOpacity: 0.45,
      flippingTime: reduce ? 150 : 900, mobileScrollSupport: false, showPageCorners: !reduce
    });
    window.flipbook = pf;
    pf.loadFromImages(A.pages.map(function (p) { return p.src; }));

    var chapter = document.getElementById('chapter'), caption = document.getElementById('caption'),
        count = document.getElementById('count'), prev = document.getElementById('prev'), next = document.getElementById('next');

    function sync() {
      var portrait = pf.getOrientation() === 'portrait', i = pf.getCurrentPageIndex(), n = pf.getPageCount();
      var pages = (portrait ? [i] : [i, i + 1]).map(function (k) { return A.pages[k]; }).filter(Boolean);
      var first = pages[0];
      chapter.textContent = first ? 'Chapter ' + first.chapter + ' · ' + first.chapter_title : A.title;
      var caps = [];
      pages.forEach(function (p) { if (p.caption && caps.indexOf(p.caption) < 0) caps.push(p.caption); });
      caption.textContent = caps.join('  ·  ');
      count.textContent = portrait
        ? (i + 1) + ' / ' + n
        : String(Math.floor(i / 2) + 1).padStart(2, '0') + ' / ' + String(A.spreads).padStart(2, '0');
      prev.disabled = i <= 0;
      next.disabled = (portrait ? i : i + 1) >= n - 1;
    }
    pf.on('flip', sync);
    pf.on('changeOrientation', sync);
    sync();

    prev.addEventListener('click', function () { pf.flipPrev(); });
    next.addEventListener('click', function () { pf.flipNext(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'PageDown') pf.flipNext();
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') pf.flipPrev();
      else if (e.key === 'Home') pf.turnToPage(0);
      else if (e.key === 'End') pf.turnToPage(pf.getPageCount() - 1);
    });
    var raf;
    window.addEventListener('resize', function () {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () { pf.update(); sync(); });
    });
    document.getElementById('loading').classList.add('done');
    window.__albumReady = true;
  }
})();
