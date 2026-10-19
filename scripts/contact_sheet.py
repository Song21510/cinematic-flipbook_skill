"""生成 4 列联系表（带文件名/序号/标记），供 Agent 看图选片。"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import find_font, load_json, open_image


def make_contact_sheet(analysis_json, input_dir, out_path, cols=4, cell=420):
    data = load_json(analysis_json)
    imgs = data["images"]
    label_h, pad = 54, 14
    rows = (len(imgs) + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = rows * (cell + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), (28, 28, 30))
    d = ImageDraw.Draw(sheet)
    f1, f2 = find_font("sans", 20), find_font("sans", 16)
    for k, it in enumerate(imgs):
        x = pad + (k % cols) * (cell + pad)
        y = pad + (k // cols) * (cell + label_h + pad)
        im = open_image(Path(input_dir) / it["file"])
        im.thumbnail((cell, cell))
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        # 焦点十字，方便核对裁切
        fx, fy = it["focus"]
        cx, cy = x + (cell - im.width) // 2 + fx * im.width, y + (cell - im.height) // 2 + fy * im.height
        d.line([cx - 8, cy, cx + 8, cy], fill=(255, 80, 80), width=2)
        d.line([cx, cy - 8, cx, cy + 8], fill=(255, 80, 80), width=2)
        d.text((x, y + cell + 4), f"#{k + 1:02d} {it['file']}", font=f1, fill=(240, 240, 240))
        flags = ",".join(it["flags"] + (["DUP"] if it["dup_of"] else []))
        d.text((x, y + cell + 30), f"{it['orientation']} {it['width']}x{it['height']} s={it['score']:.2f} {flags}", font=f2, fill=(255, 190, 90) if flags else (150, 150, 150))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=85)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    print(make_contact_sheet(a.analysis, a.input, a.output))
