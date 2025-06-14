#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from enum import Enum

# need to rename the click package so it doesn't clash with
# our click command
import click as cl
import requests


class ScreenshotMode(Enum):
    SAVE = "save"  # saves screenshot to png file
    PRINT = "print"  # prints base64 encoded screenshot to stdout


BASE_URL = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
AUTOSCREENSHOT = os.environ.get("SWEER_AUTOSCREENSHOT", "0") == "1"
SCREENSHOT_MODE = ScreenshotMode(os.environ.get("SWEER_SCREENSHOT_MODE", ScreenshotMode.SAVE.value))


def send_request(endpoint, method="GET", data=None):
    url = f"{BASE_URL}/{endpoint}"
    if method == "GET":
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    if response.status_code != 200:
        print(f"Internal error communicating with backend: {response.text}")
        sys.exit(2)
    data = response.json()
    if data["status"] == "error":
        print(f"Error: {data['message']}")
        sys.exit(1)
    return data


def _handle_screenshot(screenshot_data, screenshot_index, mode=None):
    """Handle screenshot data according to the specified mode or default SCREENSHOT_MODE"""
    if mode is None:
        mode = SCREENSHOT_MODE
    
    if mode == ScreenshotMode.SAVE:
        output = f"screenshot_{screenshot_index:03}.png"
        path = Path(output)
        path.write_bytes(base64.b64decode(screenshot_data))
        link_path = Path("latest_screenshot.png")
        link_path.unlink(missing_ok=True)
        link_path.symlink_to(path)
        print(f"Screenshot saved to {path}")
    elif mode == ScreenshotMode.PRINT:
        print(f"![Screenshot {screenshot_index}](data:image/png;base64,{screenshot_data})")


def _autosave_screenshot_from_response(response, mode=None):
    """Handle screenshot from response data according to the specified mode"""
    if "screenshot" in response and AUTOSCREENSHOT:
        _handle_screenshot(response["screenshot"], response["screenshot_index"], mode)


@cl.group()
def cli():
    pass


@cli.command(short_help="Open a website URL.")
@cl.argument("url")
def open(url):
    """Open the specified website URL."""
    if Path(url).is_file():
        url = f"file://{Path(url).resolve()}"
    response = send_request("goto", "POST", {"url": url, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Close the current window.")
def close():
    """Close the currently open window."""
    response = send_request("close", "POST")
    print(response["message"])


@cli.command(short_help="Take a screenshot using default SCREENSHOT_MODE behavior.")
@cl.option("--output", "-o", default=None, help="Output path for the screenshot (only used in save mode).")
def screenshot(output):
    """Capture a screenshot and handle it according to the default SCREENSHOT_MODE."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    screenshot_index = response["screenshot_index"]
    
    if SCREENSHOT_MODE == ScreenshotMode.SAVE:
        if output:
            path = Path(output)
            path.write_bytes(base64.b64decode(screenshot_data))
            print(f"Screenshot saved to {path}")
        else:
            _handle_screenshot(screenshot_data, screenshot_index, ScreenshotMode.SAVE)
    else:
        _handle_screenshot(screenshot_data, screenshot_index, ScreenshotMode.PRINT)


@cli.command(short_help="Take a screenshot and always save it to file.")
@cl.option("--output", "-o", default=None, help="Output path for the screenshot.")
def save_screenshot(output):
    """Capture a screenshot and always save it to file, regardless of SCREENSHOT_MODE."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    screenshot_index = response["screenshot_index"]
    
    if output:
        path = Path(output)
        path.write_bytes(base64.b64decode(screenshot_data))
        print(f"Screenshot saved to {path}")
    else:
        _handle_screenshot(screenshot_data, screenshot_index, ScreenshotMode.SAVE)


@cli.command(short_help="Take a screenshot and always print it as base64.")
def print_screenshot():
    """Capture a screenshot and always print it as base64, regardless of SCREENSHOT_MODE."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    screenshot_index = response["screenshot_index"]
    _handle_screenshot(screenshot_data, screenshot_index, ScreenshotMode.PRINT)


@cli.command(short_help="Click at coordinates")
@cl.argument("x", type=int)
@cl.argument("y", type=int)
@cl.option("--button", "-b", default="left", type=cl.Choice(["left", "right"]), help="Mouse button to click")
def click(x, y, button):
    """Click at the specified coordinates (x, y)."""
    response = send_request(
        "click",
        "POST",
        {"x": x, "y": y, "button": button, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])    
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Double-click at coordinates")
@cl.argument("x", type=int)
@cl.argument("y", type=int)
def double_click(x, y):
    """Double-click at the specified coordinates (x, y)."""
    response = send_request("double_click", "POST", {"x": x, "y": y, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Move mouse to coordinates")
@cl.argument("x", type=int)
@cl.argument("y", type=int)
def move(x, y):
    """Move mouse to the specified coordinates (x, y)."""
    response = send_request("move", "POST", {"x": x, "y": y, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Drag mouse along a path")
@cl.argument("path")
def drag(path):
    """Drag mouse along a path. Path should be a JSON string like '[{"x":100,"y":100},{"x":200,"y":200}]'."""
    import json
    try:
        path_data = json.loads(path)
    except json.JSONDecodeError:
        print("Error: Path must be valid JSON")
        sys.exit(1)
    response = send_request("drag", "POST", {"path": path_data, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Type text.")
@cl.argument("text")
def type(text):
    """Type the given text at the current cursor position."""
    response = send_request("type", "POST", {"text": text, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Scroll the page.")
@cl.argument("x", type=int)
@cl.argument("y", type=int)
@cl.argument("scroll_x", type=int)
@cl.argument("scroll_y", type=int)
def scroll(x, y, scroll_x, scroll_y):
    """Scroll by (scroll_x, scroll_y) pixels at position (x, y)."""
    response = send_request("scroll", "POST", {"x": x, "y": y, "scroll_x": scroll_x, "scroll_y": scroll_y, "return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Get text from an element.")
@cl.argument("selector")
def get_text(selector):
    """Retrieve the text content from an element specified by its selector."""
    response = send_request("get_text", "POST", {"selector": selector, "return_screenshot": False})
    print(response["message"])
    _autosave_screenshot_from_response(response)

@cli.command(short_help="Get an attribute value from an element.")
@cl.argument("selector")
@cl.argument("attribute")
def get_attribute(selector, attribute):
    """Get the value of a specific attribute from an element identified by its selector."""
    response = send_request(
        "get_attribute",
        "POST",
        {"selector": selector, "attribute": attribute, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])
    _autosave_screenshot_from_response(response)

@cli.command(short_help="Execute a custom JavaScript script.")
@cl.argument("script")
def execute_script(script):
    """Execute a custom JavaScript code snippet on the current page."""
    response = send_request(
        "execute_script",
        "POST",
        {"script": script, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Get information about the current page.")
def info():
    """Get information about the current page."""
    response = send_request("info", "GET")
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Navigate back in browser history.")
def back():
    """Navigate back in the browser history."""
    response = send_request("back", "POST", {"return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Navigate forward in browser history.")
def forward():
    """Navigate forward in the browser history."""
    response = send_request("forward", "POST", {"return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Reload the current page.")
def reload():
    """Reload the current webpage."""
    response = send_request("reload", "POST", {"return_screenshot": AUTOSCREENSHOT})
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="List elements matching a selector.")
@cl.argument("selector")
def list_elements(selector):
    """List all elements matching the given selector."""
    response = send_request(
        "list_elements", "POST", {"selector": selector, "return_screenshot": AUTOSCREENSHOT},
    )
    elements = response["elements"]
    print(f"Found {len(elements)} elements")
    for element in elements:
        print(element)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Wait for specified time.")
@cl.argument("ms", type=int)
def wait(ms):
    """Wait for the specified number of milliseconds."""
    response = send_request(
        "wait", "POST", {"ms": ms, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Press keys.")
@cl.argument("keys")
def keypress(keys):
    """Press the specified keys. Keys should be a JSON string like '["ctrl", "c"]'."""
    import json
    try:
        keys_data = json.loads(keys)
    except json.JSONDecodeError:
        print("Error: Keys must be valid JSON")
        sys.exit(1)
    response = send_request(
        "keypress", "POST", {"keys": keys_data, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Set window size.")
@cl.argument("width", type=int)
@cl.argument("height", type=int)
def set_window_size(width, height):
    """Set the browser window size to the specified width and height."""
    response = send_request(
        "set_window_size",
        "POST",
        {"width": width, "height": height, "return_screenshot": AUTOSCREENSHOT},
    )
    print(response["message"])
    _autosave_screenshot_from_response(response)


def main():
    cli()


if __name__ == "__main__":
    main()
