# vendored: StPageFlip (page-flip) 2.0.7 — MIT, see PAGE-FLIP-LICENSE.txt
Source: npm `page-flip@2.0.7`, `dist/js/page-flip.browser.js`.

Local patch (1 line): `CanvasRender.clear()` filled the canvas with hard-coded white each frame,
which shows as white bars beside the book on a dark page. Changed to `clearRect` (transparent).
Re-apply if you upgrade the library.
