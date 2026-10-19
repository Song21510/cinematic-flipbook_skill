"""调色：对比曲线 / 褪色 / 分离色调 / 油画笔触 / 画布肌理 / 暗角 / 颗粒。全部 numpy+OpenCV，无 ML。"""
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def _sigmoid_curve(x, k=6.0):
    s = 1 / (1 + np.exp(-k * (x - 0.5)))
    s0, s1 = 1 / (1 + np.exp(k / 2)), 1 / (1 + np.exp(-k / 2))
    return (s - s0) / (s1 - s0)


@lru_cache(maxsize=8)
def _brush_texture(h, w, seed):
    """各向异性噪声 → 笔触方向的明暗起伏，范围约 [-1,1]。"""
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((h, w)).astype(np.float32)
    k = np.zeros((25, 25), np.float32)
    cv2.line(k, (2, 22), (22, 2), 1.0, 1)  # 约 45° 的短笔触
    k = cv2.GaussianBlur(k, (0, 0), 1.2)
    k /= k.sum()
    t = cv2.filter2D(n, -1, k)
    t2 = cv2.GaussianBlur(n, (0, 0), 3)  # 低频团块
    t = t / (t.std() + 1e-6) * 0.7 + t2 / (t2.std() + 1e-6) * 0.3
    return t


@lru_cache(maxsize=8)
def _canvas_weave(h, w, seed):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    weave = np.sin(xs * 2 * np.pi / 5.0) * np.sin(ys * 2 * np.pi / 5.0) * 0.5 \
        + np.sin(xs * 2 * np.pi / 11.0 + 1.3) * np.sin(ys * 2 * np.pi / 13.0) * 0.3
    n = np.random.default_rng(seed).standard_normal((h, w)).astype(np.float32)
    return weave + 0.35 * cv2.GaussianBlur(n, (0, 0), 1.0) / 0.3


def oil_paint(arr, strength, seed):
    """双边滤波抹平细节保边缘 + 笔触明暗，模拟油画。arr: float32 0-1 RGB。"""
    u8 = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    sm = cv2.bilateralFilter(u8, 9, 38, 7)
    sm = cv2.bilateralFilter(sm, 9, 30, 7)
    sm = sm.astype(np.float32) / 255
    # 在抹平的基础上回收少量边缘，保持"画得出形"
    blur = cv2.GaussianBlur(sm, (0, 0), 2.0)
    sm = np.clip(sm + 0.7 * (sm - blur), 0, 1)
    out = arr * (1 - strength) + sm * strength
    h, w = arr.shape[:2]
    tex = _brush_texture(h, w, seed)[..., None]
    lum = (out @ LUMA)[..., None]
    # 笔触在中暗部保留，亮部（天空等大面积平滑区）衰减，避免出现刮擦感
    return out * (1 + 0.032 * strength * tex * (1.0 - 0.75 * np.clip(lum, 0, 1) ** 1.5))


def grade_image(img, g, seed=0, vignette=True):
    """img: PIL RGB（已裁到目标尺寸）。g: preset['grade']。返回 PIL RGB。"""
    x = np.asarray(img, np.float32) / 255
    h, w = x.shape[:2]
    lum = (x @ LUMA)[..., None]
    if g.get("mono"):
        gray = (x @ np.array([0.30, 0.55, 0.15], np.float32))[..., None]
        x = np.repeat(gray, 3, axis=2)
    else:
        x = lum + (x - lum) * g["saturation"]

    a = g["contrast"] - 1
    if a >= 0:
        x = x * (1 - min(1, a * 2.5)) + _sigmoid_curve(x) * min(1, a * 2.5)
    else:
        x = 0.5 + (x - 0.5) * (1 + a)
    x = np.clip(x, 0, 1)

    if g.get("oil", 0) > 0:
        x = np.clip(oil_paint(x, g["oil"], seed), 0, 1)

    lift = g.get("lift", 0)
    x = lift + x * (1 - lift)

    lum = (x @ LUMA)[..., None]
    st, ht = np.array(g["shadow_tint"], np.float32), np.array(g["highlight_tint"], np.float32)
    x = x + st * (1 - lum) ** 2 + ht * lum ** 2

    if g.get("canvas", 0) > 0:
        x = x * (1 + 0.05 * g["canvas"] * 4 * _canvas_weave(h, w, seed + 7)[..., None] * (0.4 + 0.6 * (1 - lum)))

    if vignette and g.get("vignette", 0) > 0:
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xs / w - .5) * 2) ** 2 + ((ys / h - .5) * 2) ** 2) / np.sqrt(2)
        x = x * (1 - g["vignette"] * r[..., None] ** 2.2)

    if g.get("grain", 0) > 0:
        n = np.random.default_rng(seed + 31).standard_normal((h, w)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.7)[..., None]
        lum = (x @ LUMA)[..., None]
        x = x + n * g["grain"] * (0.5 + 2 * lum * (1 - lum))

    return Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8))
