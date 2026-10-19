"""story-plan.json + pages/*.webp → index.html + album-data.js + assets/（纯静态，file:// 可开）。"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).parent))
from common import PAGE_H, PAGE_W, ROOT, load_json, load_preset


def page_photos(sp, idx):
    """每个模板里 (左页, 右页) 各放的是哪张照片；None 表示纯文字页。须与 pages.py 保持一致。"""
    p = sp["photos"]
    t = sp["template"]
    if t == "chapter-opener":
        return None, p[0]
    if t == "full-bleed":
        return p[0], p[0]
    if t in ("diptych", "asymmetric-pair"):
        return p[0], p[1]
    return (None, p[0]) if idx % 2 == 0 else (p[0], None)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(c) for c in rgb)


def _theme(preset):
    p = preset["paper"]
    dark = sum(p) < 300
    return {"bg": _hex([c * (0.45 if dark else 0.22) for c in p]),
            "fg": _hex(preset["ink"] if dark else p),
            "accent": _hex(preset["accent"] if sum(preset["accent"]) > 150 else p)}


def build_album_data(out, plan, preset):
    pages = []
    for i, sp in enumerate(plan["spreads"]):
        ch = plan["chapters"][sp["chapter"] - 1]
        for ph in page_photos(sp, i):
            n = len(pages) + 1
            if ph:
                cap, alt = ph.get("caption", ""), ph["alt"]
            elif sp["template"] == "chapter-opener":
                cap, alt = ch.get("subtitle", ""), f"Chapter {ch['index']}: {ch['title']}. {ch.get('subtitle', '')}"
            else:
                cap, alt = "", f"Quote page: {sp.get('quote', '')}"
            if not (out / "pages" / f"p{n:02d}.webp").exists():
                raise SystemExit(f"missing pages/p{n:02d}.webp — run --stage render first")
            pages.append({"src": f"pages/p{n:02d}.webp", "spread": i, "chapter": ch["index"],
                          "chapter_title": ch["title"], "caption": cap, "alt": alt})
    return {"title": plan["title"], "subtitle": plan.get("subtitle", ""), "style": plan["style"],
            "pageWidth": PAGE_W, "pageHeight": PAGE_H, "spreads": len(plan["spreads"]),
            "theme": _theme(preset), "chapters": plan["chapters"], "pages": pages}


def build_site(out):
    out = Path(out)
    plan = load_json(out / "build" / "story-plan.json")
    preset = load_preset(plan["style"])
    data = build_album_data(out, plan, preset)
    (out / "album-data.js").write_text("window.ALBUM = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    # assets：运行时静态文件（vendor 里是 StPageFlip 2.0.7，MIT）
    dst = out / "assets"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ROOT / "assets", dst)
    env = Environment(loader=FileSystemLoader(ROOT / "site"), autoescape=select_autoescape(["html", "j2"]))
    (out / "index.html").write_text(env.get_template("index.html.j2").render(album=data), encoding="utf-8")
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file() and "build" not in f.relative_to(out).parts) / 1e6
    print(f"[site] {out / 'index.html'}  ({len(data['pages'])} pages, site total {total:.2f}MB excl. build/)")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    build_site(ap.parse_args().output)
