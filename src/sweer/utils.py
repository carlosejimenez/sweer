import functools
import os

from flask import jsonify, request
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver


KEY_MAP = {
    'CTRL': Keys.CONTROL,
    'CONTROL': Keys.CONTROL,
    'SHIFT': Keys.SHIFT,
    'ALT': Keys.ALT,
    'CMD': Keys.COMMAND,
    'COMMAND': Keys.COMMAND,
    'META': Keys.META,
    'ENTER': Keys.ENTER,
    'RETURN': Keys.RETURN,
    'SPACE': Keys.SPACE,
    'TAB': Keys.TAB,
    'ESCAPE': Keys.ESCAPE,
    'ESC': Keys.ESCAPE,
    'BACKSPACE': Keys.BACKSPACE,
    'DELETE': Keys.DELETE,
    'HOME': Keys.HOME,
    'END': Keys.END,
    'PAGEUP': Keys.PAGE_UP,
    'PAGEDOWN': Keys.PAGE_DOWN,
    'UP': Keys.ARROW_UP,
    'DOWN': Keys.ARROW_DOWN,
    'LEFT': Keys.ARROW_LEFT,
    'RIGHT': Keys.ARROW_RIGHT,
    'F1': Keys.F1, 'F2': Keys.F2, 'F3': Keys.F3, 'F4': Keys.F4,
    'F5': Keys.F5, 'F6': Keys.F6, 'F7': Keys.F7, 'F8': Keys.F8,
    'F9': Keys.F9, 'F10': Keys.F10, 'F11': Keys.F11, 'F12': Keys.F12,
}


def no_website_open(browser: WebDriver):
    return browser.current_url == "data:,"


def validate_request(*required_keys):
    """Decorator to validate that all required keys are present in request JSON."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({"status": "error", "message": "Request must be JSON"})
            
            request_data = request.get_json()
            if not request_data:
                return jsonify({"status": "error", "message": "Request body cannot be empty"})
            
            missing_keys = [key for key in required_keys if key not in request_data]
            if missing_keys:
                return jsonify({
                    "status": "error", 
                    "message": f"Missing required fields: {', '.join(missing_keys)}"
                })
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_website_open(func):
    """Decorator to ensure that a website is open before executing a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from .server import get_browser
        if no_website_open(get_browser()):
            return jsonify({"status": "error", "message": "Please open a website first."})
        return func(*args, **kwargs)
    return wrapper


def catch_error(func):
    """Decorator to catch exceptions and return them as JSON."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return wrapper
