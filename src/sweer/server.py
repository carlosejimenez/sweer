#!/usr/bin/env python3
"""Sweer server ‒ Flask + Playwright backend.
"""
from __future__ import annotations

import base64
import functools
import os
import threading
import time
from typing import Any, List

from flask import Flask, jsonify, request, Response
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from sweer.utils import catch_error, validate_request, normalize_url


app = Flask(__name__)


WINDOW_WIDTH = int(os.environ.get("SWEER_WINDOW_WIDTH", 1024))
WINDOW_HEIGHT = int(os.environ.get("SWEER_WINDOW_HEIGHT", 768))
HEADLESS = os.environ.get("SWEER_HEADLESS", "1") != "0"
SCREENSHOT_DELAY = float(os.environ.get("SWEER_SCREENSHOT_DELAY", 0.2))
CROSSHAIR_ID = "__sweer_crosshair__"


_playwright: Playwright | None = None
_browser: Browser | None = None
_page: Page | None = None
_screenshot_index = 0
_mouse_x = 0
_mouse_y = 0
_lock = threading.RLock()


def _ensure_browser() -> Page:
    """Launch Chromium lazily and move cursor to (0,0) once."""
    global _playwright, _browser, _page, _mouse_x, _mouse_y
    if _page is not None:
        return _page
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=HEADLESS)
    ctx = _browser.new_context(viewport={"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT})
    _page = ctx.new_page()
    _page.mouse.move(0, 0)
    _mouse_x = _mouse_y = 0
    return _page


def _no_website_open() -> bool:
    return _page is None or _page.url in (None, "about:blank", "")


def _inject_crosshair(page: Page, x: int, y: int) -> bool:
    """Inject crosshair at given coordinates. Returns True if successful, False otherwise."""
    js = (
        "([x, y, id]) => {\n"
        "  const size = 20;\n"
        "  const thickness = 3;\n"
        "  const hId = id + '_h';\n"
        "  const vId = id + '_v';\n"
        "  \n"
        "  let hLine = document.getElementById(hId);\n"
        "  if (!hLine) {\n"
        "    hLine = document.createElement('div');\n"
        "    hLine.id = hId;\n"
        "    hLine.style.position = 'fixed';\n"
        "    hLine.style.pointerEvents = 'none';\n"
        "    hLine.style.zIndex = '2147483647';\n"
        "    hLine.style.backgroundColor = 'red';\n"
        "    hLine.style.boxSizing = 'border-box';\n"
        "    hLine.style.margin = '0';\n"
        "    hLine.style.padding = '0';\n"
        "    hLine.style.border = 'none';\n"
        "    hLine.style.outline = 'none';\n"
        "    hLine.style.transform = 'translateZ(0)';\n"
        "    document.body.appendChild(hLine);\n"
        "  }\n"
        "  \n"
        "  let vLine = document.getElementById(vId);\n"
        "  if (!vLine) {\n"
        "    vLine = document.createElement('div');\n"
        "    vLine.id = vId;\n"
        "    vLine.style.position = 'fixed';\n"
        "    vLine.style.pointerEvents = 'none';\n"
        "    vLine.style.zIndex = '2147483647';\n"
        "    vLine.style.backgroundColor = 'red';\n"
        "    vLine.style.boxSizing = 'border-box';\n"
        "    vLine.style.margin = '0';\n"
        "    vLine.style.padding = '0';\n"
        "    vLine.style.border = 'none';\n"
        "    vLine.style.outline = 'none';\n"
        "    vLine.style.transform = 'translateZ(0)';\n"
        "    document.body.appendChild(vLine);\n"
        "  }\n"
        "  \n"
        "  hLine.style.width = `${size}px`;\n"
        "  hLine.style.height = `${thickness}px`;\n"
        "  hLine.style.left = `${Math.round(x - size / 2)}px`;\n"
        "  hLine.style.top = `${Math.round(y - thickness / 2)}px`;\n"
        "  \n"
        "  vLine.style.width = `${thickness}px`;\n"
        "  vLine.style.height = `${size}px`;\n"
        "  vLine.style.left = `${Math.round(x - thickness / 2)}px`;\n"
        "  vLine.style.top = `${Math.round(y - size / 2)}px`;\n"
        "}"
    )
    try:
        page.evaluate(js, [x, y, CROSSHAIR_ID])
        return True
    except Exception:
        # execution context might be destroyed due to navigation
        return False


def _remove_crosshair(page: Page) -> None:
    js = (
        "(id) => {\n"
        "  const hEl = document.getElementById(id + '_h');\n"
        "  const vEl = document.getElementById(id + '_v');\n"
        "  if (hEl) hEl.remove();\n"
        "  if (vEl) vEl.remove();\n"
        "}"
    )
    try:
        page.evaluate(js, CROSSHAIR_ID)
    except Exception:
        # execution context might be destroyed due to navigation, skip crosshair removal
        pass


def _get_screenshot() -> dict[str, Any]:
    """Capture screenshot with crosshair (callers hold _lock)."""
    global _screenshot_index
    pg = _ensure_browser()
    # try to inject crosshair, with retry for navigation scenarios
    crosshair_injected = _inject_crosshair(pg, _mouse_x, _mouse_y)
    if not crosshair_injected:
        # page might be navigating, wait a bit and retry
        time.sleep(SCREENSHOT_DELAY)
        crosshair_injected = _inject_crosshair(pg, _mouse_x, _mouse_y)
        if not crosshair_injected:
            # try once more
            time.sleep(SCREENSHOT_DELAY)
            _inject_crosshair(pg, _mouse_x, _mouse_y)
    time.sleep(SCREENSHOT_DELAY)
    buf = pg.screenshot(type="png")
    _remove_crosshair(pg)
    _screenshot_index += 1
    return {
        "screenshot": base64.b64encode(buf).decode(),
        "screenshot_index": _screenshot_index,
    }


def _create_response(data: dict[str, Any], return_screenshot: bool) -> Response:
    if return_screenshot:
        data.update(_get_screenshot())
    return jsonify(data)


def require_website_open(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore[override]
        with _lock:
            if _no_website_open():
                return jsonify({"status": "error", "message": "Please open a website first."})
        return func(*args, **kwargs)
    return wrapper


@app.route("/info", methods=["GET"])
@catch_error
def info():
    rs = request.args.get("return_screenshot", "false").lower() == "true"
    with _lock:
        if _no_website_open():
            return jsonify({"status": "error", "message": "Please open a website first."})
        pg = _ensure_browser()
        data = {
            "status": "success",
            "title": pg.title(),
            "url": pg.url,
            "message": f"Title: {pg.title()} | URL: {pg.url}",
        }
        return _create_response(data, rs)


@app.route("/close", methods=["POST"])
@catch_error
def close_browser():
    global _playwright, _browser, _page
    with _lock:
        if _browser is not None:
            _browser.close()
        if _playwright is not None:
            _playwright.stop()
        _browser = _page = _playwright = None  # type: ignore[assignment]
    return jsonify({"status": "success", "message": "Browser closed"})


@app.route("/set_window_size", methods=["POST"])
@validate_request("width", "height", "return_screenshot")
@require_website_open
@catch_error
def set_window_size():  # type: ignore[override]
    w, h = request.json["width"], request.json["height"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().set_viewport_size({"width": w, "height": h})
        return _create_response({"status": "success", "message": f"Viewport {w}×{h}"}, rs)


@app.route("/screenshot", methods=["GET"])
@require_website_open
def screenshot():
    with _lock:
        return _create_response({"status": "success", "message": "Screenshot"}, True)


@app.route("/click", methods=["POST"])
@validate_request("x", "y", "button", "return_screenshot")
@catch_error
@require_website_open
def click():  # type: ignore[override]
    global _mouse_x, _mouse_y
    x, y = request.json["x"], request.json["y"]
    button = request.json["button"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().mouse.click(x, y, button=button)
        _mouse_x, _mouse_y = x, y
        return _create_response({"status": "success", "message": f"Clicked {button} at ({x},{y})"}, rs)


@app.route("/double_click", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def double_click():  # type: ignore[override]
    global _mouse_x, _mouse_y
    x, y = request.json["x"], request.json["y"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().mouse.dblclick(x, y)
        _mouse_x, _mouse_y = x, y
        return _create_response({"status": "success", "message": f"Double‑clicked at ({x},{y})"}, rs)


@app.route("/move", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def move():  # type: ignore[override]
    global _mouse_x, _mouse_y
    x, y = request.json["x"], request.json["y"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().mouse.move(x, y)
        _mouse_x, _mouse_y = x, y
        return _create_response({"status": "success", "message": f"Moved mouse to ({x},{y})"}, rs)


@app.route("/drag", methods=["POST"])
@validate_request("path", "return_screenshot")
@catch_error
@require_website_open
def drag():  # type: ignore[override]
    global _mouse_x, _mouse_y
    path: List[List[int]] = request.json["path"]
    rs = request.json["return_screenshot"]
    if not path or len(path) < 2:
        return jsonify({"status": "error", "message": "Path needs at least two points"})
    with _lock:
        pg = _ensure_browser()
        pg.mouse.move(*path[0])
        pg.mouse.down()
        for x, y in path[1:]:
            pg.mouse.move(x, y)
        pg.mouse.up()
        _mouse_x, _mouse_y = path[-1]
        return _create_response({"status": "success", "message": f"Dragged {len(path)} points"}, rs)


@app.route("/type", methods=["POST"])
@validate_request("text", "return_screenshot")
@catch_error
@require_website_open
def type_():  # type: ignore[override]
    txt = request.json["text"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().keyboard.type(txt)
        return _create_response({"status": "success", "message": f"Typed {len(txt)} chars"}, rs)


@app.route("/scroll", methods=["POST"])
@validate_request("scroll_x", "scroll_y", "return_screenshot")
@catch_error
@require_website_open
def scroll():  # type: ignore[override]
    dx, dy = request.json["scroll_x"], request.json["scroll_y"]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().mouse.wheel(dx, dy)
        return _create_response({"status": "success", "message": f"Scrolled ({dx},{dy})"}, rs)


@app.route("/execute_script", methods=["POST"])
@validate_request("script", "return_screenshot")
@catch_error
@require_website_open
def exec_script():  # type: ignore[override]
    script = request.json["script"]
    rs = request.json["return_screenshot"]
    with _lock:
        result = _ensure_browser().evaluate(script)
        return _create_response({"status": "success", "message": "Script executed", "result": result}, rs)


@app.route("/back", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def back():  # type: ignore[override]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().go_back()
        return _create_response({"status": "success", "message": "Back"}, rs)


@app.route("/forward", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def forward():  # type: ignore[override]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().go_forward()
        return _create_response({"status": "success", "message": "Forward"}, rs)


@app.route("/reload", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def reload():  # type: ignore[override]
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().reload()
        return _create_response({"status": "success", "message": "Reloaded"}, rs)


@app.route("/wait", methods=["POST"])
@validate_request("ms", "return_screenshot")
@catch_error
@require_website_open
def wait():
    ms = request.json["ms"]
    rs = request.json["return_screenshot"]
    time.sleep(ms / 1000.0)
    with _lock:
        return _create_response({"status": "success", "message": f"Waited {ms} ms"}, rs)


@app.route("/keypress", methods=["POST"])
@validate_request("keys", "return_screenshot")
@catch_error
@require_website_open
def keypress():  # type: ignore[override]
    keys: List[str] = request.json["keys"]
    rs = request.json["return_screenshot"]
    if not keys:
        return jsonify({"status": "error", "message": "Keys list empty"})
    with _lock:
        pg = _ensure_browser()
        for k in keys[:-1]:
            pg.keyboard.down(k)
        pg.keyboard.press(keys[-1])
        for k in reversed(keys[:-1]):
            pg.keyboard.up(k)
        return _create_response({"status": "success", "message": f"Pressed {keys}"}, rs)


@app.route("/goto", methods=["POST"])
@validate_request("url", "return_screenshot")
@catch_error
def goto():  # type: ignore[override]
    url = normalize_url(request.json["url"])
    rs = request.json["return_screenshot"]
    with _lock:
        _ensure_browser().goto(url, wait_until="load")
        return _create_response({"status": "success", "message": f"Navigated to {url}"}, rs)


def main():
    base = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
    port = int(base.split(":")[-1]) if base.split(":")[-1].isdigit() else 8009
    app.run(host="0.0.0.0", port=port, threaded=False, use_reloader=False)


if __name__ == "__main__":
    main()
