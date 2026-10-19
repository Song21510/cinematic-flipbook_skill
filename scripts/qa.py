"""QA：file:// 与 http:// 各开一次（桌面+手机），检查 console error、图片加载、翻页、横向溢出；
http 下桌面/手机各截 1 张图到 build/。依赖 playwright + chromium。"""
import argparse
import functools
import http.server
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import save_json

VIEWPORTS = {
    "desktop": dict(viewport={"width": 1440, "height": 900}),
    "mobile": dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2),
}
MAX_SITE_MB = 15


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def check(pw, url, vp_name, shot_path):
    res = {"url": url, "viewport": vp_name, "errors": [], "checks": {}}
    browser = pw.chromium.launch()
    ctx = browser.new_context(**VIEWPORTS[vp_name])
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and res["errors"].append("console: " + m.text))
    page.on("pageerror", lambda e: res["errors"].append("pageerror: " + str(e)))
    page.on("requestfailed", lambda r: res["errors"].append("requestfailed: " + r.url))
    page.goto(url)
    try:
        page.wait_for_function("window.__albumReady === true", timeout=30000)
    except Exception:
        res["checks"]["ready"] = False
        res["errors"].append("album never became ready")
        browser.close()
        return res
    c = res["checks"]
    st = page.evaluate("window.__albumStats")
    c["images_loaded"] = st["loaded"] == st["total"] and not st["failed"]
    c["images_detail"] = f"{st['loaded']}/{st['total']}" + (f" failed={st['failed']}" if st["failed"] else "")
    page.wait_for_timeout(400)
    c["canvas_rendered"] = page.evaluate("(()=>{const c=document.querySelector('#book canvas');return !!c && c.width>0 && c.height>0})()")
    c["orientation"] = page.evaluate("window.flipbook.getOrientation()")
    c["no_horizontal_overflow"] = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth")

    i0 = page.evaluate("window.flipbook.getCurrentPageIndex()")
    page.click("#next")
    try:
        page.wait_for_function(f"window.flipbook.getCurrentPageIndex() !== {i0}", timeout=5000)
        c["flip_next"] = True
    except Exception:
        c["flip_next"] = False
    page.wait_for_timeout(1200)
    page.click("#prev")
    page.wait_for_timeout(1200)
    c["flip_prev"] = page.evaluate("window.flipbook.getCurrentPageIndex()") == i0
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(1200)
    c["flip_keyboard"] = page.evaluate("window.flipbook.getCurrentPageIndex()") != i0

    if shot_path:
        total = page.evaluate("window.flipbook.getPageCount()")
        page.evaluate(f"window.flipbook.turnToPage({total // 2 if vp_name == 'mobile' else (total // 4) * 2})")
        page.wait_for_timeout(700)
        page.screenshot(path=str(shot_path))
    c["no_console_errors"] = not res["errors"]
    browser.close()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    site = Path(ap.parse_args().site).resolve()
    from playwright.sync_api import sync_playwright

    handler = functools.partial(_Quiet, directory=str(site))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    targets = {"file": (site / "index.html").as_uri(), "http": f"http://127.0.0.1:{srv.server_address[1]}/index.html"}

    results = []
    with sync_playwright() as pw:
        for proto, url in targets.items():
            for vp in VIEWPORTS:
                shot = site / "build" / f"qa-{vp}.png" if proto == "http" else None
                results.append({"proto": proto, **check(pw, url, vp, shot)})
    srv.shutdown()

    size_mb = sum(f.stat().st_size for f in site.rglob("*") if f.is_file() and "build" not in f.relative_to(site).parts) / 1e6
    ok = size_mb < MAX_SITE_MB
    print(f"site size: {size_mb:.2f}MB (limit {MAX_SITE_MB}) {'OK' if ok else 'FAIL'}")
    for r in results:
        bad = [k for k, v in r["checks"].items() if v is False] + (["errors"] if r["errors"] else [])
        ok &= not bad and bool(r["checks"])
        print(f"{r['proto']:5} {r['viewport']:8} {'PASS' if not bad and r['checks'] else 'FAIL'}  {r['checks']}")
        for e in r["errors"]:
            print("      !", e)
    save_json(site / "build" / "qa-report.json", {"site_mb": round(size_mb, 2), "results": results, "pass": bool(ok)})
    print("QA", "PASS" if ok else "FAIL", "— screenshots:", site / "build" / "qa-desktop.png", site / "build" / "qa-mobile.png")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
