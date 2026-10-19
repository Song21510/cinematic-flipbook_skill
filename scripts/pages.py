"""5 个跨页模板：每个返回 (左页, 右页) 两张 1200×1600 PIL 图。"""
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import PAGE_H, PAGE_W, find_font, has_cjk
from grade import grade_image

M = 96  # 页边距基准


# ------------------------------------------------------------------ 基础件
class Ctx:
    def __init__(self, preset, plan, photos, seed):
        self.preset, self.plan, self.photos, self.seed = preset, plan, photos, seed
        self.paper = tuple(preset["paper"])
        self.ink, self.muted, self.accent = tuple(preset["ink"]), tuple(preset["muted"]), tuple(preset["accent"])
        self.dark = sum(self.paper) < 300


@lru_cache(maxsize=4)
def _paper_arr(paper, dark, seed):
    rng = np.random.default_rng(seed + 99)
    n = rng.standard_normal((PAGE_H, PAGE_W)).astype(np.float32)
    low = cv2.GaussianBlur(rng.standard_normal((PAGE_H, PAGE_W)).astype(np.float32), (0, 0), 90)
    low = low / (low.std() + 1e-6)
    fine = cv2.GaussianBlur(n, (0, 0), 0.8)
    fine = fine / (fine.std() + 1e-6)
    base = np.array(paper, np.float32)[None, None, :]
    return base + (low * 1.6 + fine * 1.4)[..., None]


def new_page(ctx):
    a = _paper_arr(ctx.paper, ctx.dark, ctx.seed)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def fnt(ctx, role, size, text="", italic=False):
    cjk = has_cjk(text)
    return find_font(ctx.preset["fonts"][role], size, italic and not cjk, cjk)


def wrap(d, text, f, max_w):
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        tokens = list(para) if has_cjk(para) else para.split(" ")
        sep = "" if has_cjk(para) else " "
        for t in tokens:
            trial = t if not cur else cur + sep + t
            if d.textlength(trial, font=f) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = t
        lines.append(cur)
    return lines


def text_block(d, x, y, text, f, fill, max_w, lh, align="left"):
    """绘制自动换行文本，返回末行底部 y。"""
    for ln in wrap(d, text, f, max_w):
        w = d.textlength(ln, font=f)
        xx = x if align == "left" else x + (max_w - w) / 2 if align == "center" else x + max_w - w
        d.text((xx, y), ln, font=f, fill=fill)
        y += lh
    return y


def tracked(d, x, y, text, f, fill, spacing=4, align="left"):
    text = text.upper() if not has_cjk(text) else text
    widths = [d.textlength(c, font=f) + spacing for c in text]
    total = sum(widths) - spacing
    x = x if align == "left" else x - total if align == "right" else x - total / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=f, fill=fill)
        x += w
    return total


def roman(n):
    out = ""
    for v, s in [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out, n = out + s, n - v
    return out


def crop_to(im, w, h, focus, zoom=1.0):
    sw, sh = im.size
    ar = w / h
    if sw / sh > ar:
        ch, cw = sh / zoom, sh / zoom * ar
    else:
        cw, ch = sw / zoom, sw / zoom / ar
    x0 = min(max(focus[0] * sw - cw / 2, 0), sw - cw)
    y0 = min(max(focus[1] * sh - ch / 2, 0), sh - ch)
    return im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h), Image.LANCZOS)


def patch(ctx, ph, w, h, salt=0):
    """按 focus/zoom 裁切并调色。"""
    im = crop_to(ctx.photos[ph["id"]], w, h, ph.get("focus", [.5, .5]), ph.get("zoom", 1.0))
    return grade_image(im, ctx.preset["grade"], ctx.seed + salt)


def scrim(img, y0, y1, strength=0.7):
    a = np.asarray(img, np.float32)
    t = np.clip((np.arange(img.height) - y0) / max(1, y1 - y0), 0, 1)[:, None, None] ** 1.6
    return Image.fromarray(np.clip(a * (1 - strength * t), 0, 255).astype(np.uint8))


def place_photo(ctx, page, im, x, y):
    fr = ctx.preset["frame"]
    pad = 40
    if fr["shadow"]:
        lay = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0)
        ImageDraw.Draw(lay).rectangle([pad, pad + 10, pad + im.width, pad + im.height + 10], fill=150 if ctx.dark else 70)
        lay = lay.filter(ImageFilter.GaussianBlur(fr["shadow"]))
        page.paste((0, 0, 0), (x - pad, y - pad), lay)
    page.paste(im, (x, y))
    if fr["border"]:
        ImageDraw.Draw(page).rectangle([x - 14, y - 14, x + im.width + 14, y + im.height + 14], outline=ctx.ink, width=fr["border"])


def finish(ctx, page, side, folio, paper_page=True, header=None):
    """装订线阴影 + 页眉 + 页码。side: 'L'|'R'。"""
    a = np.asarray(page, np.float32)
    t = np.clip(1 - (np.arange(PAGE_W) if side == "R" else PAGE_W - 1 - np.arange(PAGE_W)) / 110.0, 0, 1) ** 2
    a = a * (1 - 0.30 * t)[None, :, None]
    page = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(page)
    f = fnt(ctx, "body", 22, header or "")
    if paper_page and header:
        tracked(d, M if side == "L" else PAGE_W - M, 66, header, f, ctx.muted, 5, "left" if side == "L" else "right")
    col = ctx.muted if paper_page else (235, 235, 235)
    tracked(d, M if side == "L" else PAGE_W - M, PAGE_H - 78, f"{folio:02d}", f, col, 4, "left" if side == "L" else "right")
    return page


def caption_block(ctx, d, x, y, text, max_w, size=34, fill=None, kicker=None, kicker_fill=None):
    if kicker:
        tracked(d, x, y, kicker, fnt(ctx, "body", 20), kicker_fill or ctx.accent, 5)
        y += 40
    f = fnt(ctx, "body", size, text, italic=True)
    return text_block(d, x, y, text, f, fill or ctx.ink, max_w, int(size * 1.4))


# ------------------------------------------------------------------ 模板
def chapter_opener(ctx, sp, idx):
    plan = ctx.plan
    ch = plan["chapters"][sp["chapter"] - 1]
    left, right = new_page(ctx), None
    d = ImageDraw.Draw(left)
    inner = PAGE_W - 2 * M
    if idx == 0:
        subtitle = plan.get("subtitle") or "A photo album"
        tracked(d, M, 150, subtitle, fnt(ctx, "body", 24, subtitle), ctx.muted, 7)
        title = plan["title"]
        for size in (230, 190, 160, 130, 108, 88):
            f = fnt(ctx, "display", size, title)
            lines = wrap(d, title, f, inner)
            if len(lines) <= 3 and all(d.textlength(l, font=f) <= inner for l in lines):
                break
        y = 560 - len(lines) * size * 0.55
        y = text_block(d, M, y, title, f, ctx.ink, inner, int(size * 1.08))
        d.line([M, y + 40, M + 140, y + 40], fill=ctx.accent, width=3)
        tracked(d, M, 1290, f"{roman(ch['index'])} — {ch['title']}",
                fnt(ctx, "body", 26, ch["title"]), ctx.accent, 6)
    else:
        label = "CHAPTER" if not has_cjk(ch["title"]) else "章"
        tracked(d, M, 150, label, fnt(ctx, "body", 24, label), ctx.muted, 8)
        d.text((M - 8, 190), roman(ch["index"]), font=fnt(ctx, "display", 360, roman(ch["index"])), fill=ctx.accent)
        d.line([M, 740, M + 120, 740], fill=ctx.accent, width=3)
        y = text_block(d, M, 790, ch["title"], fnt(ctx, "display", 96, ch["title"]), ctx.ink, inner, 112)
        if ch.get("subtitle"):
            text_block(d, M, y + 24, ch["subtitle"], fnt(ctx, "body", 40, ch["subtitle"], italic=True), ctx.muted, inner - 80, 56)
    left = finish(ctx, left, "L", idx * 2 + 1, True)

    ph = sp["photos"][0]
    img = patch(ctx, ph, PAGE_W, PAGE_H, idx * 10 + 1)
    img = scrim(img, int(PAGE_H * .72), PAGE_H, 0.72)
    d = ImageDraw.Draw(img)
    if ph.get("caption"):
        caption_block(ctx, d, M + 30, PAGE_H - 270, ph["caption"], PAGE_W - 2 * M - 60, 38, (246, 242, 234))
    right = finish(ctx, img, "R", idx * 2 + 2, False)
    return left, right


def full_bleed(ctx, sp, idx):
    ph = sp["photos"][0]
    img = patch(ctx, ph, PAGE_W * 2, PAGE_H, idx * 10 + 1)
    if ph.get("caption"):
        img = scrim(img, int(PAGE_H * .8), PAGE_H, 0.6)
        d = ImageDraw.Draw(img)
        caption_block(ctx, d, PAGE_W + 130, PAGE_H - 230, ph["caption"], 780, 34, (246, 242, 234))
    l, r = img.crop((0, 0, PAGE_W, PAGE_H)), img.crop((PAGE_W, 0, PAGE_W * 2, PAGE_H))
    return finish(ctx, l, "L", idx * 2 + 1, False), finish(ctx, r, "R", idx * 2 + 2, False)


def _headers(ctx, sp):
    return ctx.plan["title"], ctx.plan["chapters"][sp["chapter"] - 1]["title"]


def diptych(ctx, sp, idx):
    hl, hr = _headers(ctx, sp)
    pages = []
    for k, side in enumerate("LR"):
        page = new_page(ctx)
        ph = sp["photos"][k]
        bw, bh = PAGE_W - 2 * M, 1000
        place_photo(ctx, page, patch(ctx, ph, bw, bh, idx * 10 + k), M, 240)
        d = ImageDraw.Draw(page)
        if ph.get("caption"):
            caption_block(ctx, d, M, 1310, ph["caption"], bw, 34, kicker=f"{roman(sp['chapter'])}.{idx + 1:02d}{'ab'[k]}")
        pages.append(finish(ctx, page, side, idx * 2 + 1 + k, True, hl if k == 0 else hr))
    return pages


def asymmetric_pair(ctx, sp, idx):
    hl, hr = _headers(ctx, sp)
    p1, p2 = sp["photos"][0], sp["photos"][1]
    left = new_page(ctx)
    bw, bh = PAGE_W - 2 * M, 1240
    place_photo(ctx, left, patch(ctx, p1, bw, bh, idx * 10), M, 140)
    if p1.get("caption"):
        caption_block(ctx, ImageDraw.Draw(left), M, 1418, p1["caption"], bw, 28)
    right = new_page(ctx)
    d = ImageDraw.Draw(right)
    pw, ph_ = 600, 800
    px, py = PAGE_W - M - pw, PAGE_H - 230 - ph_
    place_photo(ctx, right, patch(ctx, p2, pw, ph_, idx * 10 + 1), px, py)
    if p2.get("caption"):
        caption_block(ctx, d, px, 160, p2["caption"], pw, 46, kicker=f"{roman(sp['chapter'])}.{idx + 1:02d}")
    return finish(ctx, left, "L", idx * 2 + 1, True, hl), finish(ctx, right, "R", idx * 2 + 2, True, hr)


def quote_page(ctx, sp, idx):
    hl, hr = _headers(ctx, sp)
    ph = sp["photos"][0]
    quote_left = idx % 2 == 0
    qp, pp = new_page(ctx), new_page(ctx)
    d = ImageDraw.Draw(qp)
    inner = PAGE_W - 2 * M - 80
    d.text((M, 200), "“", font=fnt(ctx, "display", 380, sp["quote"]), fill=ctx.accent)
    for size in (64, 56, 48, 42, 36):
        f = fnt(ctx, "display", size, sp["quote"], italic=True)
        lines = wrap(d, sp["quote"], f, inner)
        if len(lines) <= 9:
            break
    y = 640
    text_block(d, M, y, sp["quote"], f, ctx.ink, inner, int(size * 1.4))
    ay = y + len(lines) * int(size * 1.4) + 50
    d.line([M, ay, M + 90, ay], fill=ctx.accent, width=3)
    if ph.get("caption"):
        caption_block(ctx, d, M, ay + 30, ph["caption"], inner, 26, ctx.muted)
    bw, bh = PAGE_W - 2 * M, PAGE_H - 2 * 150
    place_photo(ctx, pp, patch(ctx, ph, bw, bh, idx * 10 + 1), M, 150)
    if quote_left:
        return finish(ctx, qp, "L", idx * 2 + 1, True, hl), finish(ctx, pp, "R", idx * 2 + 2, True, hr)
    return finish(ctx, pp, "L", idx * 2 + 1, True, hl), finish(ctx, qp, "R", idx * 2 + 2, True, hr)


RENDERERS = {
    "chapter-opener": chapter_opener, "full-bleed": full_bleed, "diptych": diptych,
    "asymmetric-pair": asymmetric_pair, "quote-page": quote_page,
}
