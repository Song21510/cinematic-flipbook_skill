"""扫描图片 → build/analysis.json（EXIF、清晰度、曝光、dHash、人脸、焦点、查重）。"""
import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

sys.path.insert(0, str(Path(__file__).parent))
from common import list_images, open_image, save_json

_FACE = None


def face_cascade():
    global _FACE
    if _FACE is None:
        p = getattr(getattr(cv2, "data", None), "haarcascades", None)
        _FACE = cv2.CascadeClassifier(p + "haarcascade_frontalface_default.xml") if p else False
        if _FACE is not False and _FACE.empty():
            _FACE = False
    return _FACE


def read_exif(path):
    out = {}
    try:
        ex = Image.open(path).getexif()
        sub = ex.get_ifd(0x8769) if hasattr(ex, "get_ifd") else {}
        merged = {**dict(ex), **dict(sub)}
        for k, v in merged.items():
            name = TAGS.get(k)
            if name in ("DateTimeOriginal", "DateTime", "Make", "Model", "LensModel"):
                out[name] = str(v).strip()
            elif name in ("FNumber", "FocalLength", "ExposureTime", "ISOSpeedRatings"):
                try:
                    out[name] = float(v)
                except Exception:
                    out[name] = str(v)
    except Exception:
        pass
    return out


def dhash(gray):
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return "%016x" % int("".join("1" if b else "0" for b in bits), 2)


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def detect_faces(gray):
    fc = face_cascade()
    if not fc:
        return []
    h, w = gray.shape
    s = 640 / max(h, w)
    g = cv2.resize(gray, (int(w * s), int(h * s))) if s < 1 else gray
    gh, gw = g.shape
    found = fc.detectMultiScale(g, 1.1, 9, minSize=(max(40, gw // 10),) * 2)
    return [[round(x / gw, 4), round(y / gh, 4), round(fw / gw, 4), round(fh / gh, 4)] for x, y, fw, fh in found]


def saliency_focus(rgb_small):
    """梯度能量 + 饱和度的加权质心，足够便宜，用作裁切焦点。"""
    g = cv2.cvtColor(rgb_small, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 6)
    sat = cv2.GaussianBlur(cv2.cvtColor(rgb_small, cv2.COLOR_RGB2HSV)[..., 1].astype(np.float32), (0, 0), 6)
    s = mag / (mag.max() + 1e-6) + 0.5 * sat / (sat.max() + 1e-6)
    s = s ** 2
    h, w = s.shape
    ys, xs = np.mgrid[0:h, 0:w]
    # 轻微偏向中心，避免焦点贴边
    s = s * (1 - 0.35 * (((xs / w - .5) ** 2 + (ys / h - .5) ** 2) * 2))
    t = s.sum() + 1e-9
    return [round(float((s * xs).sum() / t / w), 3), round(float((s * ys).sum() / t / h), 3)]


def analyze_one(path):
    im = open_image(path)
    w, h = im.size
    s = 640 / max(w, h)
    small = np.asarray(im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)) if s < 1 else np.asarray(im)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean = float(gray.mean()) / 255
    clip_lo = float((gray < 8).mean())
    clip_hi = float((gray > 247).mean())
    faces = detect_faces(gray)
    if faces:
        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        focus = [round(fx + fw / 2, 3), round(fy + fh / 2, 3)]
    else:
        focus = saliency_focus(small)
    mean_rgb = small.reshape(-1, 3).mean(0)
    flags = []
    if sharp < 40:
        flags.append("soft")
    if mean < 0.18 or clip_lo > 0.35:
        flags.append("underexposed")
    if mean > 0.82 or clip_hi > 0.3:
        flags.append("overexposed")
    # 综合分：清晰度(对数归一) + 曝光接近 0.45 + 人脸加成
    score = 0.6 * min(1, math.log1p(sharp) / math.log1p(500)) + 0.3 * (1 - min(1, abs(mean - 0.45) / 0.45)) + (0.1 if faces else 0)
    return {
        "file": path.name, "width": w, "height": h,
        "orientation": "landscape" if w > h * 1.1 else "portrait" if h > w * 1.1 else "square",
        "exif": read_exif(path), "sharpness": round(sharp, 1),
        "exposure": {"mean": round(mean, 3), "clip_low": round(clip_lo, 3), "clip_high": round(clip_hi, 3)},
        "dhash": dhash(gray), "faces": faces, "focus": focus,
        "mean_rgb": [round(float(c)) for c in mean_rgb],
        "warmth": round(float(mean_rgb[0] - mean_rgb[2]) / 255, 3),
        "flags": flags, "score": round(score, 3), "dup_of": None,
    }


def analyze(input_dir, out_json, dup_threshold=8):
    paths = list_images(input_dir)
    if not paths:
        raise SystemExit(f"no images found in {input_dir}")
    items = [analyze_one(p) for p in paths]
    # 查重：分数高者保留
    order = sorted(range(len(items)), key=lambda i: -items[i]["score"])
    kept = []
    for i in order:
        for j in kept:
            if hamming(items[i]["dhash"], items[j]["dhash"]) <= dup_threshold:
                items[i]["dup_of"] = items[j]["file"]
                break
        else:
            kept.append(i)
    data = {"input": str(Path(input_dir)), "count": len(items), "images": items}
    save_json(out_json, data)
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True, help="analysis.json 路径")
    a = ap.parse_args()
    d = analyze(a.input, a.output)
    for it in d["images"]:
        print(f"{it['file']:24} {it['orientation']:9} score={it['score']:.2f} sharp={it['sharpness']:7.1f} faces={len(it['faces'])} {it['flags']} dup_of={it['dup_of']}")
