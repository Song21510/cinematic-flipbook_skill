"""cinematic-flipbook 主入口。

  --stage plan    分析 + 联系表 + 生成 build/story-plan.json（草稿，需 Agent 看图后改写文案）
  --stage render  按 story-plan.json 排版调色，输出 pages/*.webp
  --stage all     (默认) plan(已存在则复用) → render → build_site
"""
import argparse
import io
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze import analyze
from common import (PAGE_H, PAGE_W, STYLES, TEMPLATES, WEBP_QUALITY, list_images, load_json, load_preset,
                    open_image, save_json)
from contact_sheet import make_contact_sheet

MAX_MB = 14.0          # 总输出预算（红线 15MB，留余量给 html/js/vendor）
MAX_SELECT = 8
SPREADS_MIN, SPREADS_MAX = 8, 12

# ------------------------------------------------------------------ 草稿文案库（Agent 会在看图后改写）
CH_TITLES = ["Arrival", "Stillness", "Afterglow", "Weather", "Return"]
CH_SUBS = ["Where the story opens", "Slowing down to look", "Light that lingers", "What the sky decides", "Carrying it home"]
QUOTES = ["Some places are remembered by the light, not the map.",
          "We went looking for distance and found quiet.",
          "The best frames arrive when you stop asking for them.",
          "Everything slows down once you look long enough."]


def tone_word(it):
    m, w = it["exposure"]["mean"], it["warmth"]
    light = "Low" if m < 0.3 else "Soft" if m < 0.55 else "Bright"
    hue = "warm" if w > 0.06 else "cool" if w < -0.06 else "neutral"
    return f"{light} {hue} light"


def draft_alt(it):
    shape = {"landscape": "Wide", "portrait": "Tall", "square": "Square"}[it["orientation"]]
    who = " with a person in frame" if it["faces"] else ""
    return f"{shape} photograph, {tone_word(it).lower()}{who} (draft — replace after viewing)"


def order_photos(sel):
    """有完整 EXIF 时间则按时间；否则按平均色最近邻串联，保证色彩连贯。"""
    def t(i):
        s = i["exif"].get("DateTimeOriginal") or i["exif"].get("DateTime")
        try:
            return datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
        except Exception:
            return None
    ts = [t(i) for i in sel]
    if all(ts):
        return [i for _, i in sorted(zip(ts, sel), key=lambda p: p[0])]
    rest = sorted(sel, key=lambda i: -i["score"])
    chain = [rest.pop(0)]
    while rest:
        last = np.array(chain[-1]["mean_rgb"])
        rest.sort(key=lambda i: np.linalg.norm(np.array(i["mean_rgb"]) - last))
        chain.append(rest.pop(0))
    return chain


def ph_entry(it, caption=None, zoom=1.0, focus=None, detail=False):
    return {"id": it["file"], "focus": focus or it["focus"], "zoom": zoom,
            "caption": caption or tone_word(it),
            "alt": draft_alt(it) if not detail else "Detail crop — " + draft_alt(it)}


def make_plan(analysis, title, style, seed, target_spreads):
    rng = np.random.default_rng(seed)
    sel, rejected = [], []
    for it in sorted(analysis["images"], key=lambda i: -i["score"]):
        bad = ["duplicate of " + it["dup_of"]] if it["dup_of"] else [f for f in it["flags"] if f in ("soft", "underexposed", "overexposed")]
        if bad:
            rejected.append({"file": it["file"], "reason": ", ".join(bad)})
        elif len(sel) < MAX_SELECT:
            sel.append(it)
        else:
            rejected.append({"file": it["file"], "reason": "over limit"})
    if len(sel) < 4:
        raise SystemExit(f"only {len(sel)} usable photos after filtering; need at least 4 (see analysis.json)")
    sel = order_photos(sel)

    n_ch = int(np.clip(round(len(sel) / 3), 3, 5))
    groups = [list(g) for g in np.array_split(np.arange(len(sel)), n_ch)]
    chapters = [{"index": c + 1, "title": CH_TITLES[c], "subtitle": CH_SUBS[c]} for c in range(n_ch)]
    per_ch = [[] for _ in range(n_ch)]   # 每章的 spread 列表
    flip = int(rng.integers(0, 2))
    for c, g in enumerate(groups):
        photos = [sel[i] for i in g]
        per_ch[c].append({"template": "chapter-opener", "chapter": c + 1, "photos": [ph_entry(photos[0])]})
        rest = photos[1:]
        while rest:
            if len(rest) >= 2:
                flip += 1
                tpl = "diptych" if flip % 2 else "asymmetric-pair"
                per_ch[c].append({"template": tpl, "chapter": c + 1, "photos": [ph_entry(rest[0]), ph_entry(rest[1])]})
                rest = rest[2:]
            else:
                p = rest.pop(0)
                tpl = "full-bleed" if p["orientation"] == "landscape" else "quote-page"
                sp = {"template": tpl, "chapter": c + 1, "photos": [ph_entry(p)]}
                if tpl == "quote-page":
                    sp["quote"] = QUOTES[c % len(QUOTES)]
                per_ch[c].append(sp)

    # 补页：用得分最高的照片做细节裁切（zoom），章末依次插入，交替 quote-page / full-bleed
    total = sum(len(x) for x in per_ch)
    pool = sorted(sel, key=lambda i: -i["score"])
    k = 0
    while total < target_spreads and k < len(pool) * 2:
        p, c = pool[k % len(pool)], k % n_ch
        if k % 2 == 0 or p["orientation"] != "landscape":
            sp = {"template": "quote-page", "chapter": c + 1, "quote": QUOTES[(c + k) % len(QUOTES)],
                  "photos": [ph_entry(p, zoom=1.5, detail=True)]}
        else:
            sp = {"template": "full-bleed", "chapter": c + 1, "photos": [ph_entry(p, zoom=1.3, detail=True)]}
        per_ch[c].append(sp)
        total += 1
        k += 1
    spreads = [dict(id=f"s{i + 1:02d}", **sp) for i, sp in enumerate(s for ch in per_ch for s in ch)][:SPREADS_MAX]
    return {
        "title": title, "subtitle": "A photo album", "style": style, "seed": seed,
        "reviewed": False,
        "_note": "草稿文案。Agent 看过 build/contact_sheet.jpg 后改写 title/chapters/caption/quote/alt/focus，并把 reviewed 设为 true。",
        "selected": [i["file"] for i in sel], "rejected": rejected,
        "chapters": chapters, "spreads": spreads,
    }


def validate_plan(plan, photo_files):
    errs = []
    if not 3 <= len(plan.get("chapters", [])) <= 5:
        errs.append("chapters must be 3-5")
    if not SPREADS_MIN <= len(plan.get("spreads", [])) <= SPREADS_MAX:
        errs.append(f"spreads must be {SPREADS_MIN}-{SPREADS_MAX}, got {len(plan.get('spreads', []))}")
    need = {"chapter-opener": 1, "full-bleed": 1, "quote-page": 1, "diptych": 2, "asymmetric-pair": 2}
    for sp in plan.get("spreads", []):
        sid = sp.get("id", "?")
        if sp.get("template") not in TEMPLATES:
            errs.append(f"{sid}: bad template {sp.get('template')}")
            continue
        if len(sp.get("photos", [])) != need[sp["template"]]:
            errs.append(f"{sid}: {sp['template']} needs {need[sp['template']]} photo(s)")
        if sp["template"] == "quote-page" and not sp.get("quote"):
            errs.append(f"{sid}: quote-page needs 'quote'")
        if not 1 <= sp.get("chapter", 0) <= len(plan.get("chapters", [])):
            errs.append(f"{sid}: bad chapter index")
        for ph in sp.get("photos", []):
            if ph.get("id") not in photo_files:
                errs.append(f"{sid}: photo {ph.get('id')} not in input folder")
            if not ph.get("alt"):
                errs.append(f"{sid}: photo missing alt")
            f = ph.get("focus", [.5, .5])
            if not (len(f) == 2 and all(0 <= v <= 1 for v in f)):
                errs.append(f"{sid}: focus must be [x,y] in 0..1")
    if errs:
        raise SystemExit("story-plan.json invalid:\n  - " + "\n  - ".join(errs))


# ------------------------------------------------------------------ stages
def stage_plan(args, out, force):
    build = out / "build"
    plan_path = build / "story-plan.json"
    if plan_path.exists() and not force:
        print(f"[plan] {plan_path} exists, keep it (use --force-plan to regenerate)")
        return
    analysis = analyze(args.input, build / "analysis.json")
    make_contact_sheet(build / "analysis.json", args.input, build / "contact_sheet.jpg")
    plan = make_plan(analysis, args.title, args.style or "cinematic-oil", args.seed, int(np.clip(args.spreads, SPREADS_MIN, SPREADS_MAX)))
    save_json(plan_path, plan)
    print(f"[plan] {len(plan['selected'])} photos -> {len(plan['chapters'])} chapters, {len(plan['spreads'])} spreads")
    print(f"[plan] 请先看 {build / 'contact_sheet.jpg'}，再改写 {plan_path}（reviewed:true）")


def stage_render(args, out):
    from pages import RENDERERS, Ctx
    plan = load_json(out / "build" / "story-plan.json")
    style = args.style or plan["style"]
    files = {p.name for p in list_images(args.input)}
    validate_plan(plan, files)
    if not plan.get("reviewed"):
        print("[render] WARNING: story-plan.json reviewed=false，文案仍是草稿")
    preset = load_preset(style)
    photos = {}
    for sp in plan["spreads"]:
        for ph in sp["photos"]:
            if ph["id"] not in photos:
                im = open_image(Path(args.input) / ph["id"])
                im.thumbnail((2800, 2800))
                photos[ph["id"]] = im
    ctx = Ctx(preset, plan, photos, plan.get("seed", args.seed))
    pages = []
    for i, sp in enumerate(plan["spreads"]):
        l, r = RENDERERS[sp["template"]](ctx, sp, i)
        assert l.size == r.size == (PAGE_W, PAGE_H), (sp["id"], l.size, r.size)
        pages += [l, r]
        print(f"[render] {sp['id']} {sp['template']}")
    # 编码；超预算则逐级降质量（在内存里重编码，不重新渲染）
    pdir = out / "pages"
    pdir.mkdir(parents=True, exist_ok=True)
    for old in pdir.glob("*.webp"):
        old.unlink()
    for q in (WEBP_QUALITY, 74, 68, 62, 56):
        blobs = []
        for im in pages:
            b = io.BytesIO()
            im.save(b, "WEBP", quality=q, method=4)
            blobs.append(b.getvalue())
        total = sum(map(len, blobs)) / 1e6
        if total <= MAX_MB:
            break
        print(f"[render] q{q}: {total:.1f}MB > {MAX_MB}MB, lowering quality")
    for n, b in enumerate(blobs, 1):
        (pdir / f"p{n:02d}.webp").write_bytes(b)
    save_json(out / "build" / "render-report.json", {"pages": len(blobs), "quality": q, "total_mb": round(total, 2), "style": style})
    print(f"[render] {len(blobs)} pages, q{q}, {total:.2f}MB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--title", default="Untitled")
    ap.add_argument("--style", default=None, choices=STYLES, help="默认读 story-plan.json，新建时为 cinematic-oil")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--spreads", type=int, default=10, help="目标跨页数 8-12")
    ap.add_argument("--stage", choices=["plan", "render", "all"], default="all")
    ap.add_argument("--force-plan", action="store_true", help="覆盖已有 story-plan.json")
    args = ap.parse_args()
    out = Path(args.output)
    if args.stage in ("plan", "all"):
        stage_plan(args, out, args.force_plan)
    if args.stage in ("render", "all"):
        stage_render(args, out)
    if args.stage == "all":
        from build_site import build_site
        build_site(out)


if __name__ == "__main__":
    main()
