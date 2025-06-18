#!/usr/bin/env python3
"""Sweer server ‒ Flask + Playwright backend.
"""
from __future__ import annotations

import atexit
import base64
import contextlib
import functools
import os
import signal
import sys
import threading
import time
from typing import Any, List, Optional

from flask import Flask, jsonify, request, Response
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from sweer.utils import catch_error, validate_request, normalize_url


class BrowserManager:
    """Manages Playwright browser instance with proper resource cleanup."""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.screenshot_index = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self._lock = threading.RLock()
        self.window_width = int(os.environ.get("SWEER_WINDOW_WIDTH", 1024))
        self.window_height = int(os.environ.get("SWEER_WINDOW_HEIGHT", 768))
        self.headless = os.environ.get("SWEER_HEADLESS", "1") != "0"
        self.screenshot_delay = float(os.environ.get("SWEER_SCREENSHOT_DELAY", 0.2))
        self.crosshair_id = "__sweer_crosshair__"
    
    @contextlib.contextmanager
    def _browser_lock(self):
        """Context manager for thread-safe browser operations."""
        with self._lock:
            yield self._ensure_browser()
    
    def _ensure_browser(self) -> Page:
        """Launch Chromium lazily and move cursor to (0,0) once."""
        if self.page is not None:
            return self.page
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        ctx = self.browser.new_context(
            viewport={"width": self.window_width, "height": self.window_height}
        )
        self.page = ctx.new_page()
        self.page.mouse.move(0, 0)
        self.mouse_x = self.mouse_y = 0
        return self.page
    
    def is_website_open(self) -> bool:
        """Check if a website is currently open."""
        return self.page is not None and self.page.url not in (None, "about:blank", "")
    
    def cleanup(self):
        """Clean up browser resources safely."""
        with self._lock:
            for resource, name in [
                (self.page, "page"),
                (self.browser, "browser"), 
                (self.playwright, "playwright")
            ]:
                if resource is not None:
                    try:
                        if name == "playwright":
                            resource.stop()
                        else:
                            resource.close()
                    except Exception:
                        pass  # Ignore cleanup errors
            
            self.browser = self.page = self.playwright = None
    
    def _inject_crosshair(self, page: Page, x: int, y: int) -> bool:
        """Inject crosshair at given coordinates. Returns True if successful."""
        js_code = """
        ([x, y, id]) => {
            const size = 20;
            const thickness = 3;
            const hId = id + '_h';
            const vId = id + '_v';
            
            const createLine = (elementId, styles) => {
                let line = document.getElementById(elementId);
                if (!line) {
                    line = document.createElement('div');
                    line.id = elementId;
                    Object.assign(line.style, {
                        position: 'fixed',
                        pointerEvents: 'none',
                        zIndex: '2147483647',
                        backgroundColor: 'red',
                        boxSizing: 'border-box',
                        margin: '0',
                        padding: '0',
                        border: 'none',
                        outline: 'none',
                        transform: 'translateZ(0)',
                        ...styles
                    });
                    document.body.appendChild(line);
                }
                return line;
            };
            
            const hLine = createLine(hId, {
                width: `${size}px`,
                height: `${thickness}px`,
                left: `${Math.round(x - size / 2)}px`,
                top: `${Math.round(y - thickness / 2)}px`
            });
            
            const vLine = createLine(vId, {
                width: `${thickness}px`,
                height: `${size}px`,
                left: `${Math.round(x - thickness / 2)}px`,
                top: `${Math.round(y - size / 2)}px`
            });
        }
        """
        try:
            page.evaluate(js_code, [x, y, self.crosshair_id])
            return True
        except Exception:
            return False
    
    def _remove_crosshair(self, page: Page) -> None:
        """Remove crosshair elements from the page."""
        js_code = """
        (id) => {
            const hEl = document.getElementById(id + '_h');
            const vEl = document.getElementById(id + '_v');
            if (hEl) hEl.remove();
            if (vEl) vEl.remove();
        }
        """
        try:
            page.evaluate(js_code, self.crosshair_id)
        except Exception:
            pass
    
    def take_screenshot(self) -> dict[str, Any]:
        """Capture screenshot with crosshair."""
        with self._browser_lock() as page:
            for attempt in range(3):
                if self._inject_crosshair(page, self.mouse_x, self.mouse_y):
                    break
                if attempt < 2:
                    time.sleep(self.screenshot_delay)
            time.sleep(self.screenshot_delay)
            screenshot_data = page.screenshot(type="png")
            self._remove_crosshair(page)
            self.screenshot_index += 1
            return {
                "screenshot": base64.b64encode(screenshot_data).decode(),
                "screenshot_index": self.screenshot_index,
            }
    
    def validate_coordinates(self, x: int, y: int) -> tuple[bool, bool]:
        x_is_valid = 0 <= x < self.window_width
        y_is_valid = 0 <= y < self.window_height
        return (x_is_valid, y_is_valid)
    
    def constrain_mouse_position(self, page: Page) -> bool:
        """Constrain mouse position to window bounds and move if needed.
        """
        if self.window_width <= 0 or self.window_height <= 0:
            return False
        if self.mouse_x >= self.window_width or self.mouse_y >= self.window_height:
            self.mouse_x = min(self.mouse_x, self.window_width - 1)
            self.mouse_y = min(self.mouse_y, self.window_height - 1)
            self.mouse_x = max(0, self.mouse_x)
            self.mouse_y = max(0, self.mouse_y)
            page.mouse.move(self.mouse_x, self.mouse_y)
            return True
        return False


browser_manager = BrowserManager()


def cleanup_on_exit():
    """Cleanup function for atexit and signal handlers."""
    browser_manager.cleanup()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\nReceived signal {signum}, shutting down...")
    cleanup_on_exit()
    sys.exit(0)


# register cleanup handlers
atexit.register(cleanup_on_exit)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


app = Flask(__name__)


def require_website_open(func):
    """Decorator to ensure a website is open before executing the route."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not browser_manager.is_website_open():
            return jsonify({"status": "error", "message": "Please open a website first."})
        return func(*args, **kwargs)
    return wrapper


def create_response(data: dict[str, Any], return_screenshot: bool) -> Response:
    """Create a JSON response, optionally including a screenshot."""
    if return_screenshot:
        data.update(browser_manager.take_screenshot())
    return jsonify(data)


@app.route("/info", methods=["GET"])
@catch_error
def info():
    return_screenshot = request.args.get("return_screenshot", "false").lower() == "true"
    if not browser_manager.is_website_open():
        return jsonify({"status": "error", "message": "Please open a website first."})
    with browser_manager._browser_lock() as page:
        data = {
            "status": "success",
            "title": page.title(),
            "url": page.url,
            "message": f"Title: {page.title()} | URL: {page.url}",
        }
        return create_response(data, return_screenshot)


@app.route("/close", methods=["POST"])
@catch_error
def close_browser():
    browser_manager.cleanup()
    return jsonify({"status": "success", "message": "Browser closed"})


@app.route("/set_window_size", methods=["POST"])
@validate_request("width", "height", "return_screenshot")
@require_website_open
@catch_error
def set_window_size():
    width, height = request.json["width"], request.json["height"]
    return_screenshot = request.json["return_screenshot"]
    if width <= 0 or height <= 0:
        return jsonify({
            "status": "error", 
            "message": f"Invalid dimensions ({width},{height}). Must be positive"
        })
    with browser_manager._browser_lock() as page:
        page.set_viewport_size({"width": width, "height": height})
        browser_manager.window_width = width
        browser_manager.window_height = height
        browser_manager.constrain_mouse_position(page)
        data = {"status": "success", "message": f"Viewport {width}×{height}"}
        return create_response(data, return_screenshot)


@app.route("/screenshot", methods=["GET"])
@require_website_open
def screenshot():
    data = {"status": "success", "message": "Screenshot"}
    return create_response(data, True)


@app.route("/click", methods=["POST"])
@validate_request("x", "y", "button", "return_screenshot")
@catch_error
@require_website_open
def click():
    x, y = round(request.json["x"]), round(request.json["y"])
    button = request.json["button"]
    return_screenshot = request.json["return_screenshot"]
    x_valid, y_valid = browser_manager.validate_coordinates(x, y)
    if not x_valid or not y_valid:
        return jsonify({
            "status": "error", 
            "message": f"Invalid coordinates ({x},{y}). Must be within {browser_manager.window_width}x{browser_manager.window_height}"
        })
    with browser_manager._browser_lock() as page:
        page.mouse.click(x, y, button=button)
        browser_manager.mouse_x, browser_manager.mouse_y = x, y
        data = {"status": "success", "message": f"Clicked {button} at ({x},{y})"}
        return create_response(data, return_screenshot)


@app.route("/double_click", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def double_click():
    x, y = request.json["x"], request.json["y"]
    return_screenshot = request.json["return_screenshot"]
    x_valid, y_valid = browser_manager.validate_coordinates(x, y)
    if not x_valid or not y_valid:
        return jsonify({
            "status": "error", 
            "message": f"Invalid coordinates ({x},{y}). Must be within {browser_manager.window_width}x{browser_manager.window_height}"
        })
    with browser_manager._browser_lock() as page:
        page.mouse.dblclick(x, y)
        browser_manager.mouse_x, browser_manager.mouse_y = x, y
        data = {"status": "success", "message": f"Double‑clicked at ({x},{y})"}
        return create_response(data, return_screenshot)


@app.route("/move", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def move():
    x, y = request.json["x"], request.json["y"]
    return_screenshot = request.json["return_screenshot"]
    x_valid, y_valid = browser_manager.validate_coordinates(x, y)
    if not x_valid or not y_valid:
        return jsonify({
            "status": "error", 
            "message": f"Invalid coordinates ({x},{y}). Must be within {browser_manager.window_width}x{browser_manager.window_height}"
        })
    with browser_manager._browser_lock() as page:
        page.mouse.move(x, y)
        browser_manager.mouse_x, browser_manager.mouse_y = x, y
        data = {"status": "success", "message": f"Moved mouse to ({x},{y})"}
        return create_response(data, return_screenshot)


@app.route("/drag", methods=["POST"])
@validate_request("path", "return_screenshot")
@catch_error
@require_website_open
def drag():
    path: List[List[int]] = request.json["path"]
    return_screenshot = request.json["return_screenshot"]
    if not path or len(path) < 2:
        return jsonify({"status": "error", "message": "Path needs at least two points"})
    for ix, point in enumerate(path):
        if len(point) != 2:
            return jsonify({"status": "error", "message": f"Path point {ix} must have exactly 2 coordinates"})
        x, y = point
        x_valid, y_valid = browser_manager.validate_coordinates(x, y)
        if not x_valid or not y_valid:
            return jsonify({
                "status": "error", 
                "message": f"Invalid coordinates ({x},{y}) at path point {ix}. Must be within {browser_manager.window_width}x{browser_manager.window_height}"
            })
    
    with browser_manager._browser_lock() as page:
        page.mouse.move(*path[0])
        page.mouse.down()
        for x, y in path[1:]:
            page.mouse.move(x, y)
        page.mouse.up()
        browser_manager.mouse_x, browser_manager.mouse_y = path[-1]
        data = {"status": "success", "message": f"Dragged {len(path)} points"}
        return create_response(data, return_screenshot)


@app.route("/type", methods=["POST"])
@validate_request("text", "return_screenshot")
@catch_error
@require_website_open
def type_():
    text = request.json["text"]
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        page.keyboard.type(text)
        data = {"status": "success", "message": f"Typed {len(text)} chars"}
        return create_response(data, return_screenshot)


@app.route("/scroll", methods=["POST"])
@validate_request("scroll_x", "scroll_y", "return_screenshot")
@catch_error
@require_website_open
def scroll():
    delta_x, delta_y = request.json["scroll_x"], request.json["scroll_y"]
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        page.mouse.wheel(delta_x, delta_y)
        data = {"status": "success", "message": f"Scrolled ({delta_x},{delta_y})"}
        return create_response(data, return_screenshot)


@app.route("/execute_script", methods=["POST"])
@validate_request("script", "return_screenshot")
@catch_error
@require_website_open
def exec_script():
    script = request.json["script"]
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        result = page.evaluate(script)
        data = {"status": "success", "message": "Script executed", "result": result}
        return create_response(data, return_screenshot)


@app.route("/back", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def back():
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        page.go_back()
        data = {"status": "success", "message": "Back"}
        return create_response(data, return_screenshot)


@app.route("/forward", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def forward():
    return_screenshot = request.json["return_screenshot"]    
    with browser_manager._browser_lock() as page:
        page.go_forward()
        data = {"status": "success", "message": "Forward"}
        return create_response(data, return_screenshot)


@app.route("/reload", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def reload():
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        page.reload()
        data = {"status": "success", "message": "Reloaded"}
        return create_response(data, return_screenshot)


@app.route("/wait", methods=["POST"])
@validate_request("ms", "return_screenshot")
@catch_error
@require_website_open
def wait():
    milliseconds = request.json["ms"]
    return_screenshot = request.json["return_screenshot"]
    time.sleep(milliseconds / 1000.0)
    data = {"status": "success", "message": f"Waited {milliseconds} ms"}
    return create_response(data, return_screenshot)


@app.route("/keypress", methods=["POST"])
@validate_request("keys", "return_screenshot")
@catch_error
@require_website_open
def keypress():
    keys: List[str] = request.json["keys"]
    return_screenshot = request.json["return_screenshot"]
    if not isinstance(keys, list):
        return jsonify({"status": "error", "message": "Keys must be a list"})
    if not keys:
        return jsonify({"status": "error", "message": "Keys list empty"})
    with browser_manager._browser_lock() as page:
        for key in keys[:-1]:
            page.keyboard.down(key)
        page.keyboard.press(keys[-1])
        for key in reversed(keys[:-1]):
            page.keyboard.up(key)
        data = {"status": "success", "message": f"Pressed {keys}"}
        return create_response(data, return_screenshot)


@app.route("/goto", methods=["POST"])
@validate_request("url", "return_screenshot")
@catch_error
def goto():
    url = normalize_url(request.json["url"])
    return_screenshot = request.json["return_screenshot"]
    with browser_manager._browser_lock() as page:
        page.goto(url, wait_until="load")
        data = {"status": "success", "message": f"Navigated to {url}"}
        return create_response(data, return_screenshot)


def main():
    """Run the Flask server with proper cleanup handling."""
    base_url = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
    port = int(base_url.split(":")[-1]) if base_url.split(":")[-1].isdigit() else 8009
    try:
        app.run(host="0.0.0.0", port=port, threaded=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        cleanup_on_exit()


if __name__ == "__main__":
    main()
