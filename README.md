# cinematic-flipbook

把一组照片自动编排成**电影油画质感的双页 3D 翻页画册**。Python 预渲染页面图，StPageFlip 负责翻页；输出是纯静态网站，`file://` 双击就能看，运行时零 API、零 CDN、零上传。

这是一个 [Claude Code](https://claude.com/claude-code) / Agent Skill，也是一套可以独立运行的 Python 工具。

![桌面端 demo](docs/screenshots/desktop.png)

## Demo

- 本地直接打开：[`docs/demo/index.html`](docs/demo/index.html)（不需要服务器）
- 在线 Demo：启用 GitHub Pages 后，把仓库 Pages 源设为 `/docs`，访问
  `https://<your-username>.github.io/cinematic-flipbook/demo/`
- 全部跨页总览：[`docs/screenshots/spreads.jpg`](docs/screenshots/spreads.jpg)
- 手机端截图：[`docs/screenshots/mobile.png`](docs/screenshots/mobile.png)

Demo 使用 8 张 Unsplash 图片，生成 3 章、10 个跨页、20 页；体积约 1.8MB。`file://` 与本地 HTTP、桌面 1440×900 与手机 390×844 都通过了现有 QA。

---

## 1. 项目主要解决什么问题

手机和相机里有很多照片，但“做成一本画册”通常卡在四件事：

- **选片难**：几十上百张照片，不知道留哪些、怎么排顺序。
- **排版难**：PPT、Canva、H5 模板要么费时间，要么一眼就是模板；跨页、留白、图注、页码很难统一。
- **质感难**：想要电影/油画/胶片的统一色调，但自己调色容易一张一个样，或者把脸磨糊。
- **交付难**：做出来的东西要能直接发给别人看，最好离线也能打开，不依赖服务器和账号。

`cinematic-flipbook` 把这条链路做成可重复执行的流水线：**分析照片 → 生成联系表 → 生成叙事草稿 → 排版 → 调色 → 预渲染页面 → 翻页网站 → QA 截图**。它不生成假照片，也不替代你的照片，只负责把真实照片编成一本有节奏的书。

当前版本是 **v0.1 MVP**：优先保证“能跑通、能看、能离线”，不是完整商业产品。真实限制见[已知限制](#已知限制v01-mvp)。

---

## 2. 主要功能

### 2.1 照片分析

- 读取 EXIF：拍摄时间、相机、镜头、焦段、ISO 等
- 计算清晰度（Laplacian 方差）、曝光（均值/高低光裁切）、平均色与冷暖
- 用 dHash 找近重复照片
- 用 OpenCV Haar cascade 检测人脸，辅助裁切焦点
- 输出 `build/analysis.json`，为选片和排序提供依据

### 2.2 联系表与叙事草稿

- 生成带编号、文件名、尺寸、方向、评分和标记的 4 列联系表 `build/contact_sheet.jpg`
- 自动生成 3–5 章、8–12 个跨页的 `story-plan.json` 草稿
- 草稿包含标题、章节名、图注、引语、alt、`focus`、`zoom`
- 草稿是**占位文案**，需要 Agent 或人工看过联系表后改写；`reviewed:false` 时渲染会给出警告

### 2.3 版式

5 个跨页模板，按 1200×1600 单页输出；`full-bleed` 会先在 2400×1600 上合成再切分：

| 模板 | 说明 | 照片数 |
|---|---|---|
| `chapter-opener` | 左页章节号/标题，右页整页图 | 1 |
| `full-bleed` | 整跨页出血，主体避开中缝 | 1 |
| `diptych` | 左右各一张，适合并置 | 2 |
| `asymmetric-pair` | 左大右小，制造主次 | 2 |
| `quote-page` | 引语 + 一张图，左右交替 | 1 |

### 2.4 电影感调色

3 个内置 preset：

| preset | 气质 | 纸张 | 适合 |
|---|---|---|---|
| `cinematic-oil` | 青橙分离色调、油画笔触、画布肌理 | 深色 | 旅行、夜景、情绪片 |
| `portra-film` | 暖褪色、颗粒、轻 halation | 奶油色 | 人像、家庭、日常 |
| `editorial-mono` | 高对比黑白、细线框、大留白 | 白色 | 纪实、建筑、编辑风 |

调色管线包括：胶片曲线、分离色调、轻油画层、画布纹理、颗粒、暗角。preset 定义在 `presets/*.yaml`，可以直接改参数或复制新增。

### 2.5 3D 翻页网站

- 使用 [StPageFlip (page-flip)](https://github.com/Nodlik/StPageFlip) 2.0.7，vendored 在 `assets/vendor/`
- 支持按钮、键盘方向键、移动端单页布局；StPageFlip 自身提供拖动翻页
- 桌面双页、手机单页；书页有阴影和中缝
- 纯静态：`index.html` + `album-data.js` + `assets/` + `pages/*.webp`
- `file://` 可直接打开，不需要服务器
- 运行时零 API、零 CDN、零上传

### 2.6 QA

`scripts/qa.py` 会用 Playwright 检查：

- `file://` 和本地 HTTP 两种方式
- 桌面 1440×900、手机 390×844
- 图片是否全部加载、canvas 是否渲染
- 按钮和键盘翻页
- 横向溢出、控制台错误
- 输出 `build/qa-report.json` 和桌面/手机截图

注意：当前 QA **没有自动化拖动/手机滑动**，只覆盖按钮和键盘；拖动能力来自 StPageFlip 本身。

---

## 3. 安装方法

### 3.1 环境要求

- Python 3.10+
- Windows / macOS / Linux
- 中文字体（可选但推荐）：Noto Serif CJK、Source Han Serif、SimSun、Songti 等
- QA 需要 Playwright + Chromium

### 3.2 安装

```bash
git clone https://github.com/<your-username>/cinematic-flipbook.git
cd cinematic-flipbook

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# 仅运行 QA 时需要
playwright install chromium
```

`requirements.txt` 里锁定了 `opencv-python-headless<5`：OpenCV 5.x 移除了 Haar 人脸级联，当前 `analyze.py` 仍在使用它。

如果系统没有中文字体，渲染不会崩溃，但会退回 Pillow 内置字体，中文观感会明显变差。

---

## 4. 使用方法

### 4.1 一键构建

准备一个照片文件夹，然后：

```bash
python scripts/build_album.py \
  --input "D:\photos\seaside" \
  --output "out\seaside" \
  --title "潮线" \
  --style cinematic-oil \
  --seed 7 \
  --spreads 10
```

打开 `out/seaside/index.html` 即可。

参数说明：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--input` | 是 | 照片文件夹；当前只扫描该目录一层，不递归子目录 |
| `--output` | 是 | 输出目录，不存在会自动创建 |
| `--title` | 否 | 画册标题，默认 `Untitled` |
| `--style` | 否 | `cinematic-oil` / `portra-film` / `editorial-mono`，默认 `cinematic-oil` |
| `--seed` | 否 | 随机种子，默认 1；影响模板变化和纹理 |
| `--spreads` | 否 | 目标跨页数，范围 8–12，默认 10 |
| `--stage` | 否 | `plan` / `render` / `all`，默认 `all` |
| `--force-plan` | 否 | 覆盖已有的 `story-plan.json` |

注意：当前选片上限是 **8 张唯一照片**（`MAX_SELECT = 8`），这是 MVP 的硬限制，不是参数。照片更多时，脚本只会选评分最高的 8 张，再用裁切/引语页补足跨页。

### 4.2 分阶段构建（推荐给 Agent 用）

```bash
# 1) 分析 + 联系表 + 草稿 story-plan
python scripts/build_album.py \
  --input "D:\photos\seaside" \
  --output "out\seaside" \
  --title "潮线" \
  --style cinematic-oil \
  --seed 7 \
  --stage plan

# 2) 看联系表，改写 out/seaside/build/story-plan.json
#    把 reviewed 设为 true

# 3) 排版 + 调色 + 页面
python scripts/build_album.py \
  --input "D:\photos\seaside" \
  --output "out\seaside" \
  --stage render

# 4) 生成网站
python scripts/build_site.py --output "out\seaside"

# 5) QA（需要 playwright + chromium）
python scripts/qa.py --site "out\seaside"
```

`--stage plan` 生成的 `story-plan.json` 不会被后续 `render` 覆盖；需要重新生成时加 `--force-plan`。

### 4.3 本地预览

直接双击 `out/seaside/index.html`，或者起一个本地服务器：

```bash
python -m http.server 8000 --directory out/seaside
```

然后打开 `http://127.0.0.1:8000/`。

### 4.4 作为 Claude Code Skill 使用

把整个仓库放到下面任一位置：

```text
# 个人级（所有项目可用）
~/.claude/skills/cinematic-flipbook/

# 或项目级
<your-project>/.claude/skills/cinematic-flipbook/
```

然后对 Claude Code 说：

> 用 cinematic-flipbook 把 `D:\photos` 做成画册，标题《潮线》，风格 cinematic-oil，8 个跨页，中文文案。

`SKILL.md` 是 Agent 入口。它会按“plan → 看联系表 → 改 story-plan → render → QA”的顺序执行；细节和已知限制也写在 `SKILL.md` 里。

### 4.5 换风格 / 换标题 / 重跑

- 换风格：改 `--style`，或直接改 `story-plan.json` 的 `style` 后重跑 `render` + `build_site`
- 换标题：改 `--title` 并加 `--force-plan` 重新生成，或直接改 `story-plan.json` 的 `title` 后重跑 `render` + `build_site`
- 改文案：编辑 `build/story-plan.json` 的 `caption` / `alt` / `quote` / `chapters`
- 改裁切：编辑 `focus: [x, y]`（0–1）和 `zoom`（≥1）
- 换模板：编辑 `template`，注意照片数量必须匹配
- 重跑：`--force-plan` 重新生成计划；不加重跑会复用已有计划

---

## 5. 输入输出示例

### 5.1 输入示例

```text
D:\photos\seaside\
├── IMG_001.jpg
├── IMG_002.jpg
├── IMG_003.jpg
├── IMG_004.jpg
├── IMG_005.jpg
├── IMG_006.jpg
├── IMG_007.jpg
└── IMG_008.jpg
```

要求：

- 支持格式：`.jpg` / `.jpeg` / `.png` / `.webp` / `.bmp` / `.tif` / `.tiff`
- 当前不支持 HEIC，请先转成 JPG/PNG
- 当前只扫描 `--input` 目录一层，不递归子目录
- 至少需要 4 张可用照片；当前最多选 8 张唯一照片
- 照片建议长边 ≥ 1200px；太小的图会显得糊

### 5.2 命令示例

```bash
python scripts/build_album.py \
  --input "D:\photos\seaside" \
  --output "out\seaside" \
  --title "潮线" \
  --style cinematic-oil \
  --seed 7 \
  --spreads 10
```

### 5.3 控制台输出示例

数字会随照片数量、评分和跨页数变化：

```text
[plan] 8 photos -> 3 chapters, 10 spreads
[plan] 请先看 out\seaside\build\contact_sheet.jpg，再改写 out\seaside\build\story-plan.json（reviewed:true）
[render] WARNING: story-plan.json reviewed=false，文案仍是草稿
[render] s01 chapter-opener
[render] s02 diptych
[render] s03 quote-page
...
[render] 20 pages, q80, 1.97MB
[site] out\seaside\index.html  (20 pages, site total 2.03MB excl. build/)
```

如果总页面体积超过 14MB，渲染会自动降低 WebP 质量（80 → 74 → 68 → 62 → 56）。

### 5.4 输出目录示例

```text
out\seaside\
├── index.html              # 入口，双击可看
├── album-data.js           # 页面顺序、章节、caption、alt
├── assets\
│   ├── app.js              # StPageFlip 初始化 + UI
│   ├── style.css           # 舞台、按钮、响应式
│   └── vendor\
│       └── page-flip.browser.js
├── pages\
│   ├── p01.webp
│   ├── p02.webp
│   └── ...
└── build\                  # 调试/交付用，部署时可删
    ├── analysis.json       # 每张照片的分析结果
    ├── contact_sheet.jpg   # 联系表
    ├── story-plan.json     # 叙事/版式计划
    ├── render-report.json  # 页数、质量、体积
    ├── qa-report.json      # QA 结果
    └── qa-desktop.png / qa-mobile.png
```

### 5.5 `story-plan.json` 示例

这是实际使用的数据结构，不是嵌套的 `chapters[].spreads`。下面只展示前两个跨页，省略了其余跨页；完整文件必须满足 8–12 个 `spreads`，否则 `validate_plan` 会报错。

```json
{
  "title": "潮线",
  "subtitle": "A Weekend by the Sea",
  "style": "cinematic-oil",
  "seed": 7,
  "reviewed": true,
  "chapters": [
    {
      "index": 1,
      "title": "抵达",
      "subtitle": "Where the road runs out of map"
    },
    {
      "index": 2,
      "title": "停留",
      "subtitle": "Slowing down enough to look"
    },
    {
      "index": 3,
      "title": "离岸",
      "subtitle": "Light on the way out"
    }
  ],
  "spreads": [
    {
      "id": "s01",
      "template": "chapter-opener",
      "chapter": 1,
      "photos": [
        {
          "id": "IMG_001.jpg",
          "focus": [0.55, 0.5],
          "zoom": 1.0,
          "caption": "潮水退到礁石下面。",
          "alt": "退潮后的礁石与远处的海面"
        }
      ]
    },
    {
      "id": "s02",
      "template": "diptych",
      "chapter": 1,
      "photos": [
        {
          "id": "IMG_002.jpg",
          "focus": [0.5, 0.5],
          "zoom": 1.0,
          "caption": "风把盐吹到窗上。",
          "alt": "窗边有一层盐霜"
        },
        {
          "id": "IMG_003.jpg",
          "focus": [0.48, 0.55],
          "zoom": 1.0,
          "caption": "下午四点，潮水退到礁石下面。",
          "alt": "退潮后的礁石"
        }
      ]
    }
  ]
}
```

约束：

- `chapters` 3–5 章；`spreads` 8–12 个
- `photos[].id` 必须是输入目录里的文件名
- `chapter` 是 1-based，必须对应 `chapters` 的位置
- `focus` 是 0–1 归一化坐标；`zoom` ≥ 1
- `diptych` / `asymmetric-pair` 必须 2 张；其余模板 1 张
- `quote-page` 必须有 `quote`
- 每个 photo 必须有 `alt`
- 改完文案后把 `reviewed` 设为 `true`，否则渲染会提示草稿

---

## 视觉预设

预设定义在 `presets/*.yaml`，可以直接改参数，也可以复制一份新增：

```yaml
name: cinematic-oil
paper: [24, 22, 21]
ink: [232, 224, 210]
muted: [150, 140, 128]
accent: [196, 150, 96]
fonts: {display: serif, body: serif}
grade:
  mono: false
  saturation: 0.92
  contrast: 1.18
  lift: 0.02
  shadow_tint: [-0.035, 0.0, 0.05]
  highlight_tint: [0.06, 0.02, -0.05]
  vignette: 0.38
  grain: 0.012
  oil: 0.65
  canvas: 0.22
frame: {margin: 96, border: 0, shadow: 28}
```

---

## 项目结构

```text
.
├── SKILL.md                 # Agent 入口
├── scripts/
│   ├── analyze.py           # 图像分析、dHash、人脸
│   ├── contact_sheet.py     # 联系表
│   ├── build_album.py       # plan / render 主流程
│   ├── pages.py             # 5 个版式渲染
│   ├── grade.py             # 调色 / 油画 / 纹理
│   ├── build_site.py        # 静态站生成
│   ├── common.py            # 路径、preset、字体、图片读取
│   └── qa.py                # Playwright QA
├── presets/                 # 3 个视觉预设
├── site/index.html.j2       # 页面模板
├── assets/                  # CSS/JS + vendored StPageFlip
├── examples/                # demo 照片 + story-plan
├── docs/                    # demo 站点 + 截图
├── THIRD_PARTY_NOTICES.md
├── CONTRIBUTING.md
└── requirements.txt
```

---

## 已知限制（v0.1 MVP）

这些是当前版本真实存在的限制：

- **最多只选 8 张唯一照片**：`build_album.py` 里 `MAX_SELECT = 8`。demo 正好 8 张；真实相册需要把这个值和选片逻辑一起改大。
- **没有封面/封底**：`app.js` 使用 `showCover: false`，从章节页直接开始。
- **QA 没有自动化拖动/滑动**：只验证按钮、键盘、图片加载和渲染；StPageFlip 本身支持拖动，但没有回归测试。
- **UI 是英文**：`index.html` 的 `lang="en"`，底部按钮/章节标签是英文；中文文案本身支持。
- **字体依赖系统**：没有 vendoring 中文字体，换机器可能观感不同。
- **`reviewed: false` 时仍是草稿文案**：脚本不会自动写出好文案，需要 Agent 看图后改写。
- **不做视频导出、缩略图、全屏、文字版抽屉**：这些在 Roadmap 里，不在当前版本。
- **不递归子目录、不支持 HEIC**：当前只扫描一层目录，HEIC 需要先转格式。

---

## Roadmap

- [ ] 把 `MAX_SELECT` 改成可配置，支持 20–60 张照片
- [ ] 增加封面、封底、硬页打开动画
- [ ] QA 增加拖动 / 手机滑动测试
- [ ] UI 中文化 + `lang` 跟随 album locale
- [ ] 增加 `torn-collage`、`polaroid-cluster` 模板
- [ ] 增加 `dusk-noir`、`sunlit-paper`、`vintage-postcard` 预设
- [ ] 支持 HEIC 和递归子目录
- [ ] 可选 MP4 导出（Playwright 录屏 + ffmpeg）

---

## Credits

- 翻页：[StPageFlip (page-flip)](https://github.com/Nodlik/StPageFlip) 2.0.7，MIT，vendored 到 `assets/vendor/`，带一行透明清屏补丁。
- Demo 照片：Unsplash License，作者与链接见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
- 纸张/画布/颗粒纹理：项目代码程序生成。

## License

代码以 [MIT License](LICENSE) 开源。Demo 照片不属于 MIT 授权范围，见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues and PRs are welcome.
