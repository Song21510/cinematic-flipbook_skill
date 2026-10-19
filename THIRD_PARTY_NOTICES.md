# Third-Party Notices

This repository includes or depends on the following third-party works.

## StPageFlip (page-flip) 2.0.7

- File: `assets/vendor/page-flip.browser.js`
- License: MIT
- Copyright: Copyright (c) 2020 Nodlik
- Source: npm package `page-flip@2.0.7`, `dist/js/page-flip.browser.js`
- Local patch: one line in `CanvasRender.clear()` changed from a hard-coded white fill to `clearRect` so the page edges stay transparent on dark backgrounds. See `assets/vendor/README.md`.

The full MIT text is in `assets/vendor/PAGE-FLIP-LICENSE.txt`.

## Demo photographs

The photographs in `examples/demo-photos/` and `docs/demo/pages/` are demo assets, not part of the software license. They were downloaded via `picsum.photos` and are used under the [Unsplash License](https://unsplash.com/license). They are resized/cropped for the demo.

Credits:

- `lake-canoe.jpg` — Roberto Nickson, https://unsplash.com/photos/7BjmDICVloE
- `fjord.jpg` — Alexey Topolyanskiy, https://unsplash.com/photos/-oWyJoSqBRM
- `green-cliffs.jpg` — Andrew Ridley, https://unsplash.com/photos/Kt5hRENuotI
- `sea-gaze.jpg` — Matthew Wiebe, https://unsplash.com/photos/tBtuxtLvAZs
- `golden-field.jpg` — Alexander Shustov, https://unsplash.com/photos/2FrX56QL7P8
- `portrait.jpg` — Roksolana Zasiadko, https://unsplash.com/photos/LyeduBb2Auk
- `old-door.jpg` — Alexander Shustov, https://unsplash.com/photos/OxzhYtL-00Y
- `storm-sea.jpg` — Patrick Fore, https://unsplash.com/photos/V6s1cmE39XM

If you publish a real album with this tool, you are responsible for the rights to your own photographs.

## Fonts

The renderer uses fonts installed on the host system (for example Georgia, Noto Serif CJK, Source Han Serif, SimSun). No font files are bundled in this repository. Check the license of any font you install or redistribute.

## Generated textures

Paper, canvas, grain and torn-edge textures are generated procedurally by the project's Python code. They are original generated assets and are covered by this repository's MIT license.
