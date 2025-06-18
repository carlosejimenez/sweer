from __future__ import annotations

import base64
import contextlib
import threading
import time
from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from sweer.config import Config

config = Config()


CROSSHAIR_JS = """
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


REMOVE_CROSSHAIR_JS = """
(id) => {
    const hEl = document.getElementById(id + '_h');
    const vEl = document.getElementById(id + '_v');
    if (hEl) hEl.remove();
    if (vEl) vEl.remove();
}
"""


class BrowserManager:
    """Manages Playwright browser instance with proper resource cleanup."""
    
    def __init__(self):
        self.headless = config.headless
        self.page: Page | None = None
        self.screenshot_index = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self._lock = threading.RLock()
        self.window_width = config.window_width
        self.window_height = config.window_height
        self.screenshot_delay = config.screenshot_delay
        self.crosshair_id = config.crosshair_id
        self._init_browser()
    
    def _init_browser(self):
        self.playwright: Playwright = sync_playwright().start()
        self.browser: Browser = self.playwright.chromium.launch(headless=self.headless)
    
    @property
    def browser_name(self) -> str:
        """Get the name of the browser."""
        return self.browser.browser_type.name
    
    @contextlib.contextmanager
    def _browser_lock(self):
        """Context manager for thread-safe browser operations."""
        with self._lock:
            yield self._ensure_browser()
    
    def _ensure_browser(self) -> Page:
        """Launch Chromium lazily and move cursor to (0,0) once."""
        if self.page is not None:
            return self.page
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
        try:
            page.evaluate(CROSSHAIR_JS, [x, y, self.crosshair_id])
            return True
        except Exception:
            return False
    
    def _remove_crosshair(self, page: Page) -> None:
        """Remove crosshair elements from the page."""
        try:
            page.evaluate(REMOVE_CROSSHAIR_JS, self.crosshair_id)
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
        x_is_valid = 0 <= x <= self.window_width
        y_is_valid = 0 <= y <= self.window_height
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
