"""公共工具：路径、预设、图片读取、字体查找。"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import yaml
from PIL import Image, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PAGE_W, PAGE_H = 1200, 1600
WEBP_QUALITY = 80
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
STYLES = ["cinematic-oil", "portra-film", "editorial-mono"]
TEMPLATES = ["chapter-opener", "full-bleed", "diptych", "asymmetric-pair", "quote-page"]

Image.MAX_IMAGE_PIXELS = 200_000_000  # 防解压炸弹，同时允许大图

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK，中文日志会乱码
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_preset(name):
    p = ROOT / "presets" / f"{name}.yaml"
    if not p.exists():
        raise SystemExit(f"unknown style '{name}', choose from {STYLES}")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def open_image(path):
    """读图并按 EXIF 旋转，统一为 RGB。"""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def list_images(folder):
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMG_EXT)


# ---------------------------------------------------------------- fonts
_FONT_DIRS = [
    Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"), Path.home() / "Library/Fonts",
    Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
]
# (family, italic) -> 候选文件名（小写比较）
_LATIN = {
    ("serif", False): ["georgia.ttf", "cambria.ttc", "times.ttf", "dejavuserif.ttf", "times new roman.ttf", "palatino.ttc"],
    ("serif", True): ["georgiai.ttf", "cambriai.ttf", "timesi.ttf", "dejavuserif-italic.ttf", "times new roman italic.ttf"],
    ("sans", False): ["segoeui.ttf", "arial.ttf", "helvetica.ttc", "dejavusans.ttf", "liberationsans-regular.ttf"],
    ("sans", True): ["segoeuii.ttf", "ariali.ttf", "dejavusans-oblique.ttf", "helvetica.ttc"],
}
_CJK = {
    "serif": ["notoserifsc-vf.ttf", "simsun.ttc", "songti.ttc", "notoserifcjk-regular.ttc"],
    "sans": ["notosanssc-vf.ttf", "msyh.ttc", "pingfang.ttc", "notosanscjk-regular.ttc", "simhei.ttf"],
}
_CJK_RE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")


def has_cjk(text):
    return bool(_CJK_RE.search(text or ""))


@lru_cache(maxsize=None)
def _locate(names):
    for d in _FONT_DIRS:
        if not d.exists():
            continue
        for n in names:
            hit = d / n
            if hit.exists():
                return hit
        low = {p.name.lower(): p for p in d.glob("*") if p.is_file()}
        for n in names:
            if n in low:
                return low[n]
    # Linux 子目录兜底
    for d in _FONT_DIRS[-2:]:
        if d.exists():
            for n in names:
                for p in d.rglob("*"):
                    if p.name.lower() == n:
                        return p
    return None


@lru_cache(maxsize=None)
def find_font(family, size, italic=False, cjk=False):
    """family: serif|sans。找不到时退回 Pillow 内置字体（不会崩）。"""
    names = tuple(_CJK[family] if cjk else _LATIN[(family, italic)])
    p = _locate(names)
    if p is None:
        return ImageFont.load_default(size)
    try:
        f = ImageFont.truetype(str(p), size)
        if cjk and p.name.lower().endswith("-vf.ttf"):
            try:
                f.set_variation_by_axes([500 if family == "serif" else 400])
            except Exception:
                pass
        return f
    except OSError:
        return ImageFont.load_default(size)
