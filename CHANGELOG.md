# Changelog

All notable changes to this project are documented here.

## v0.1.1 — 2026-10-20

黑金魔法书版本：在不改变 StPageFlip 翻页稳定性的前提下，增加 3D 书籍外壳、360° 旋转和可选背景音乐。

### 新增

- 3D 透视书籍外壳：悬浮浮动、封面/封底、书脊、弧形页边、金色页块厚度
- 360° 旋转模式：右上角“旋转”，拖动旋转，双击复位
- 黑金魔法书封面：金色条纹、魔法阵、烫金标题
- 可选背景音乐：原创 64 秒《Shoreline Nocturne》，进入内页淡入，可开关
- `docs/shoreline` 在线示例：7 张尼康 Z30 海岸照片

### 修复

- 中文章节标签、running head 和标题的字体回退问题

## v0.1.0 — 2026-10-20

首个公开 MVP：把一组照片自动编排成电影油画质感的双页 3D 翻页画册。

### 新增

- 照片分析：EXIF、清晰度、曝光、dHash 近重复检测、OpenCV 人脸焦点
- 联系表 `contact_sheet.jpg` 与 3–5 章、8–12 跨页的 `story-plan.json` 草稿
- 3 个视觉预设：`cinematic-oil`、`portra-film`、`editorial-mono`
- 5 个跨页模板：`chapter-opener`、`full-bleed`、`diptych`、`asymmetric-pair`、`quote-page`
- Python 预渲染 1200×1600 WebP 页面，StPageFlip 2.0.7 负责翻页
- 电影感调色：胶片曲线、分离色调、轻油画层、画布纹理、颗粒、暗角
- 纯静态站点，`file://` 可直接打开；运行时零 API、零 CDN、零上传
- Playwright QA：`file://` / HTTP、桌面 / 手机、图片加载、按钮和键盘翻页、横向溢出、控制台错误
- 中文 running head、章节标签和标题的字体渲染修复
- MIT License、第三方许可证说明、Contribution 指南和 CI

### 已知限制

- 当前最多只选 **8 张唯一照片**（`MAX_SELECT = 8`）
- 没有封面/封底，从章节页开始
- QA 没有自动化拖动/手机滑动检查
- 页面 UI 目前是英文，`lang="en"`
- 字体依赖系统，未 vendoring 中文字体
- 不递归子目录，不支持 HEIC
- 不做视频导出、缩略图、全屏、文字版抽屉

### 快速开始

```bash
pip install -r requirements.txt
python scripts/build_album.py \
  --input examples/demo-photos \
  --output out/demo \
  --title "Demo" \
  --style cinematic-oil \
  --seed 1
```

打开 `out/demo/index.html`。

### 许可证

代码以 MIT License 开源。Demo 照片使用 Unsplash License，详见 `THIRD_PARTY_NOTICES.md`。
