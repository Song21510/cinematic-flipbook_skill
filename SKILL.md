---
name: cinematic-flipbook
description: 把一组照片编排成电影油画质感的双页 3D 翻页画册网页（Python 预渲染页面图 + StPageFlip，纯静态、零运行时 API/CDN）。用户要"照片画册 / 翻页相册 / flipbook / 摄影集网页"时使用。
---

# cinematic-flipbook v0.1 (MVP)

照片 → `analyze` 选片 → Agent 看联系表写文案 → 预渲染 1200×1600 WebP 页面 → 静态站点（`file://` 可直接打开）。

## 依赖
`pip install -r requirements.txt` + `playwright install chromium`（仅 QA 用）。
注意 OpenCV 必须 `<5`：5.x 移除了 Haar 人脸级联。

## 工作流（Agent 必须按顺序）

```bash
cd <skill-root>   # 本仓库根目录，或 ~/.claude/skills/cinematic-flipbook
# 1) plan：分析 + 联系表 + 草稿 story-plan.json
python scripts/build_album.py --input <photos> --output out/<name> --title "<标题>" --style cinematic-oil --seed 1 --stage plan
# 2) 【必做】用 Read 工具看 out/<name>/build/contact_sheet.jpg，然后改写 build/story-plan.json
# 3) render + site
python scripts/build_album.py --input <photos> --output out/<name> --stage render
python scripts/build_site.py  --output out/<name>
# 4) QA（一次）
python scripts/qa.py --site out/<name>
```
不带 `--stage` 等于 plan(已有则复用)→render→site 一条龙。已存在的 `story-plan.json` 不会被覆盖，除非 `--force-plan`。

### 第 2 步怎么改 story-plan.json
脚本生成的 caption/alt/quote 是**占位草稿**（`reviewed:false`，渲染时会警告）。看完联系表后：
- 改 `title`、3–5 个 `chapters[].title/subtitle`，让章节顺序讲得通。
- 逐张改 `caption`（一句话，有画面感，别写参数）和 `alt`（客观描述画面，给读屏用）。
- 联系表上红色十字是自动焦点；主体不在十字上就改 `focus: [x,y]`（0–1）。`zoom>1` 做细节裁切。
- 换模板只改 `template`，注意张数：`diptych`/`asymmetric-pair` 要 2 张，其余 1 张；`quote-page` 必须有 `quote`。
- 跨页数 8–12，改完设 `reviewed: true`。`render` 会校验并报错。
- 参考：`examples/demo-story-plan.json`。

## 预设（`presets/*.yaml`）
`cinematic-oil` 青橙分离色调+油画笔触+画布肌理（深色纸面）｜`portra-film` 暖褪色+颗粒（奶油纸面）｜`editorial-mono` 高对比黑白+细线框（白纸面，无衬线）。

## 模板
`chapter-opener`（左文字/右整页图）｜`full-bleed`（整跨页出血）｜`diptych`（左右各一图）｜`asymmetric-pair`（左大右小）｜`quote-page`（引语+图，左右交替）。

## 输出
`out/<name>/`：`index.html`、`album-data.js`、`assets/`、`pages/pNN.webp`、`build/`（analysis / story-plan / contact_sheet / render-report / qa-*，**部署时可删**）。
渲染若超 14MB 会自动降 WebP 质量。

## 限制 / 已知事项
- 字体取自系统（Georgia/Segoe UI/Noto SC 等），找不到则退回 Pillow 内置字体，观感会变；跨平台字体未做 vendoring。
- `assets/vendor/page-flip.browser.js` 带 1 行本地补丁（去掉硬编码白色清屏），见 `assets/vendor/README.md`。
- 人脸检测是 Haar，偏保守，漏检时用联系表人工修 `focus`。
- 不做：视频导出、缩略图/全屏/文字版、更多风格、WebGL。
