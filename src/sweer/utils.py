from __future__ import annotations

import functools
from enum import Enum
from pathlib import Path

from flask import jsonify, request


class ScreenshotMode(Enum):
    SAVE = "save"  # saves screenshot to png file
    PRINT = "print"  # prints base64 encoded screenshot to stdout


def normalize_url(url: str) -> str:
    # if starts with http:// or https://, return as is
    # if starts with file://, return as is
    # elif local file path exists, return as file://
    # else: return as https://
    if any(url.startswith(prefix) for prefix in ["http://", "https://", "file://"]):
        return url
    elif Path(url).exists():
        return f"file://{Path(url).resolve()}"
    else:
        return "https://" + url


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


def catch_error(func):
    """Decorator to catch exceptions and return them as JSON."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return wrapper
