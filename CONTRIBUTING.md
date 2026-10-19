# Contributing

Thanks for taking a look. This is a small MVP, so focused changes are easier to review than large rewrites.

## Before you open a PR

1. Build the demo and make sure it still works:

   ```bash
   python scripts/build_album.py \
     --input examples/demo-photos \
     --output out/demo \
     --title "Demo" \
     --style cinematic-oil \
     --seed 1
   ```

2. Run QA if you have Playwright installed:

   ```bash
   python scripts/qa.py --site out/demo
   ```

3. Keep the `SKILL.md` entry short. Put detailed guidance in `README.md` or a new reference file, not in the entry.

## Good first issues

- Make `MAX_SELECT` configurable and support 20–60 photos.
- Add a cover/back-cover spread.
- Add drag/swipe checks to `scripts/qa.py`.
- Add a Chinese UI locale.
- Add a new layout or preset.

## License

By contributing, you agree that your contribution is licensed under the repository's MIT License.
