(function () {
  var A = window.ALBUM, root = document.documentElement;
  Object.keys(A.theme).forEach(function (k) { root.style.setProperty('--' + k, A.theme[k]); });

  // QA hooks: qa.py reads these globals.
  var stats = window.__albumStats = { total: A.pages.length, loaded: 0, failed: [] };
  var loadingN = document.getElementById('loading-n');
  var cover = document.getElementById('cover');
  var openBtn = document.getElementById('open-book');
  var bookOpen = !cover;
  var bgm = document.getElementById('bgm');
  var musicToggle = document.getElementById('music-toggle');
  var musicOn = false, musicFade = null;

  function updateMusicButton() {
    if (!musicToggle) return;
    musicToggle.textContent = musicOn ? '音乐 开' : '音乐 关';
    musicToggle.setAttribute('aria-pressed', musicOn ? 'true' : 'false');
    document.body.classList.toggle('music-on', musicOn);
  }

  function fadeMusic(target, duration, done) {
    if (!bgm) return;
    if (musicFade) cancelAnimationFrame(musicFade);
    var from = bgm.volume, started = performance.now();
    function step(now) {
      var k = Math.min(1, (now - started) / duration);
      bgm.volume = Math.max(0, Math.min(1, from + (target - from) * k));
      if (k < 1) musicFade = requestAnimationFrame(step);
      else { musicFade = null; if (done) done(); }
    }
    musicFade = requestAnimationFrame(step);
  }

  function setMusic(on) {
    if (!bgm) return;
    if (on) {
      if (musicOn) return;
      musicOn = true;
      updateMusicButton();
      bgm.volume = 0;
      var playing = bgm.play();
      if (playing && playing.then) {
        playing.then(function () { fadeMusic(0.72, 1500); }).catch(function () {
          musicOn = false;
          updateMusicButton();
        });
      } else {
        fadeMusic(0.72, 1500);
      }
    } else {
      musicOn = false;
      updateMusicButton();
      fadeMusic(0, 500, function () { bgm.pause(); });
    }
  }
  updateMusicButton();

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
    var orbitLayer = document.getElementById('orbit-layer');
    var modeToggle = document.getElementById('mode-toggle');
    var orbit = { x: 9, y: -10 };
    var dragging = false, last = null;

    function applyOrbit() {
      root.style.setProperty('--orbit-x', orbit.x.toFixed(2) + 'deg');
      root.style.setProperty('--orbit-y', orbit.y.toFixed(2) + 'deg');
    }
    applyOrbit();

    if (orbitLayer) {
      orbitLayer.addEventListener('pointerdown', function (e) {
        if (!document.body.classList.contains('orbit-mode')) return;
        dragging = true;
        last = { x: e.clientX, y: e.clientY };
        orbitLayer.setPointerCapture(e.pointerId);
      });
      orbitLayer.addEventListener('pointermove', function (e) {
        if (!dragging || !last) return;
        orbit.y += (e.clientX - last.x) * 0.28;
        orbit.x = Math.max(-55, Math.min(55, orbit.x - (e.clientY - last.y) * 0.18));
        last = { x: e.clientX, y: e.clientY };
        applyOrbit();
      });
      function endDrag() { dragging = false; last = null; }
      orbitLayer.addEventListener('pointerup', endDrag);
      orbitLayer.addEventListener('pointercancel', endDrag);
      orbitLayer.addEventListener('dblclick', function () {
        orbit = { x: 9, y: -10 };
        applyOrbit();
      });
    }

    if (modeToggle) {
      modeToggle.addEventListener('click', function () {
        var on = document.body.classList.toggle('orbit-mode');
        modeToggle.textContent = on ? '翻页' : '旋转';
        modeToggle.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }

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
      if (!bookOpen) {
        chapter.textContent = 'A PHOTO BOOK';
        caption.textContent = A.subtitle || A.title;
        count.textContent = '封面';
        prev.disabled = true;
        next.disabled = true;
        return;
      }
      var portrait = pf.getOrientation() === 'portrait', i = pf.getCurrentPageIndex(), n = pf.getPageCount();
      var pages = (portrait ? [i] : [i, i + 1]).map(function (k) { return A.pages[k]; }).filter(Boolean);
      var first = pages[0];
      chapter.textContent = first ? 'Chapter ' + first.chapter + ' \u00b7 ' + first.chapter_title : A.title;
      var caps = [], seen = {};
      pages.forEach(function (p) {
        if (!p.caption) return;
        var key = p.caption.replace(/[\s。．.!！?？,，·]/g, '');
        if (key && !seen[key]) { seen[key] = 1; caps.push(p.caption); }
      });
      caption.textContent = caps.join('  \u00b7  ');
      count.textContent = portrait
        ? (i + 1) + ' / ' + n
        : String(Math.floor(i / 2) + 1).padStart(2, '0') + ' / ' + String(A.spreads).padStart(2, '0');
      prev.disabled = i <= 0;
      next.disabled = (portrait ? i : i + 1) >= n - 1;
    }
    pf.on('flip', sync);
    pf.on('changeOrientation', sync);
    sync();

    prev.addEventListener('click', function () { if (bookOpen) pf.flipPrev(); });
    next.addEventListener('click', function () { if (bookOpen) pf.flipNext(); });
    document.addEventListener('keydown', function (e) {
      if (!bookOpen) return;
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

    function openBook() {
      if (bookOpen) return;
      bookOpen = true;
      setMusic(true);
      document.body.classList.add('book-open');
      if (cover) cover.classList.add('opened');
      setTimeout(function () {
        if (cover) cover.style.display = 'none';
        pf.update();
        sync();
      }, reduce ? 60 : 1150);
    }
    if (openBtn) openBtn.addEventListener('click', openBook);
    if (musicToggle) musicToggle.addEventListener('click', function () { setMusic(!musicOn); });
    if (cover) cover.addEventListener('click', function (e) {
      if (e.target === cover || (e.target.closest && e.target.closest('.cover-book'))) openBook();
    });

    document.getElementById('loading').classList.add('done');
    window.__albumReady = true;
  }
})();
