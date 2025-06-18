#!/usr/bin/env python3
from __future__ import annotations

import base64
import sys
from pathlib import Path

import click as cl
import requests

from sweer.config import ClientConfig
from sweer.utils import ScreenshotMode

config = ClientConfig()


def _format_metadata_info(response):
    """Format metadata information from API response for display."""
    if "metadata" not in response or not response["metadata"]:
        return ""
    return "\n".join(f"{key}: {value}" for key, value in response["metadata"].items())


def send_request(endpoint, method="GET", data=None):
    url = f"http://localhost:{config.port}/{endpoint}"
    if method == "GET":
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    if response.status_code != 200:
        print(f"Internal error communicating with backend: {response.text}")
        sys.exit(2)
    data = response.json()
    if data["status"] == "error":
        metadata_info = _format_metadata_info(data)
        error_message = data['message']
        print(f"ACTION ERROR:\n{error_message}")
        if metadata_info:
            print(f"\nMETADATA:\n{metadata_info}")
        sys.exit(1)
    return data


def _print_response_with_metadata(response):
    """Print response message with formatted metadata information."""
    message = response.get("message", "")
    metadata_info = _format_metadata_info(response)
    print(f"ACTION RESPONSE:\n{message}")
    
    if metadata_info:
        print(f"\nMETADATA:\n{metadata_info}")


def _handle_screenshot(screenshot_data, mode=None):
    """Handle screenshot data according to the specified mode or default config.screenshot_mode"""
    if mode is None:
        mode = config.screenshot_mode
    
    if mode == ScreenshotMode.SAVE:
        path = Path("latest_screenshot.png")
        path.write_bytes(base64.b64decode(screenshot_data))
        print(f"![Screenshot]({path})")
    elif mode == ScreenshotMode.PRINT:
        print(f"![Screenshot](data:image/png;base64,{screenshot_data})")


def _autosave_screenshot_from_response(response, mode=None):
    """Handle screenshot from response data according to the specified mode"""
    if "screenshot" in response and config.autoscreenshot:
        _handle_screenshot(response["screenshot"], mode)


@cl.group()
def cli():
    pass


@cli.command(short_help="Open a website URL.", context_settings=config.cli_context_settings)
@cl.argument("url")
def open(url):
    """Open the specified website URL."""
    if Path(url).is_file():
        url = f"file://{Path(url).resolve()}"
    response = send_request("goto", "POST", {"url": url, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Close the current window.", context_settings=config.cli_context_settings)
def close():
    """Close the currently open window."""
    response = send_request("close", "POST")
    _print_response_with_metadata(response)


@cli.command(short_help="Take a screenshot using default config.screenshot_mode behavior.", context_settings=config.cli_context_settings)
@cl.option("--output", "-o", default=None, help="Output path for the screenshot (only used in save mode).")
def screenshot(output):
    """Capture a screenshot and handle it according to the default config.screenshot_mode."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    _print_response_with_metadata(response)
    if config.screenshot_mode == ScreenshotMode.SAVE:
        if output:
            path = Path(output)
            path.write_bytes(base64.b64decode(screenshot_data))
            print(f"Screenshot saved to {path}")
        else:
            _handle_screenshot(screenshot_data, ScreenshotMode.SAVE)
    else:
        _handle_screenshot(screenshot_data, ScreenshotMode.PRINT)


@cli.command(short_help="Take a screenshot and always save it to file.", context_settings=config.cli_context_settings)
@cl.option("--output", "-o", default=None, help="Output path for the screenshot.")
def save_screenshot(output):
    """Capture a screenshot and always save it to file, regardless of config.screenshot_mode."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    _print_response_with_metadata(response)
    if output:
        path = Path(output)
        path.write_bytes(base64.b64decode(screenshot_data))
        print(f"Screenshot saved to {path}")
    else:
        _handle_screenshot(screenshot_data, ScreenshotMode.SAVE)


@cli.command(short_help="Take a screenshot and always print it as base64.", context_settings=config.cli_context_settings)
def print_screenshot():
    """Capture a screenshot and always print it as base64, regardless of config.screenshot_mode."""
    response = send_request("screenshot", "GET")
    screenshot_data = response["screenshot"]
    _print_response_with_metadata(response)
    _handle_screenshot(screenshot_data, ScreenshotMode.PRINT)


@cli.command(short_help="Click at coordinates", context_settings=config.cli_context_settings)
@cl.argument("x", type=int)
@cl.argument("y", type=int)
@cl.option("--button", "-b", default="left", type=cl.Choice(["left", "right"]), help="Mouse button to click")
def click(x, y, button):
    """Click at the specified coordinates (x, y)."""
    response = send_request(
        "click",
        "POST",
        {"x": x, "y": y, "button": button, "return_screenshot": config.autoscreenshot},
    )
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Double-click at coordinates", context_settings=config.cli_context_settings)
@cl.argument("x", type=int)
@cl.argument("y", type=int)
def double_click(x, y):
    """Double-click at the specified coordinates (x, y)."""
    response = send_request("double_click", "POST", {"x": x, "y": y, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Move mouse to coordinates", context_settings=config.cli_context_settings)
@cl.argument("x", type=int)
@cl.argument("y", type=int)
def move(x, y):
    """Move mouse to the specified coordinates (x, y)."""
    response = send_request("move", "POST", {"x": x, "y": y, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Drag mouse along a path", context_settings=config.cli_context_settings)
@cl.argument("path")
def drag(path):
    """Drag mouse along a path. Path should be a JSON list of x, y lists: '[[0, 0], [100, 100]]'."""
    import json
    try:
        path_data = json.loads(path)
    except json.JSONDecodeError:
        print("Error: Path must be valid JSON")
        sys.exit(1)
    response = send_request("drag", "POST", {"path": path_data, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Type text.", context_settings=config.cli_context_settings)
@cl.argument("text")
def type(text):
    """Type the given text at the current cursor position."""
    response = send_request("type", "POST", {"text": text, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Scroll the page.", context_settings=config.cli_context_settings)
@cl.argument("scroll_x", type=int)
@cl.argument("scroll_y", type=int)
def scroll(scroll_x, scroll_y):
    """Scroll by (scroll_x, scroll_y) pixels at current mouse position."""
    response = send_request("scroll", "POST", {"scroll_x": scroll_x, "scroll_y": scroll_y, "return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Execute a custom JavaScript script.", context_settings=config.cli_context_settings)
@cl.argument("script")
def execute_script(script):
    """Execute a custom JavaScript code snippet on the current page."""
    response = send_request(
        "execute_script",
        "POST",
        {"script": script, "return_screenshot": config.autoscreenshot},
    )
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Get information about the current page.", context_settings=config.cli_context_settings)
def info():
    """Get information about the current page."""
    response = send_request("info", "GET")
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Navigate back in browser history.", context_settings=config.cli_context_settings)
def back():
    """Navigate back in the browser history."""
    response = send_request("back", "POST", {"return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Navigate forward in browser history.", context_settings=config.cli_context_settings)
def forward():
    """Navigate forward in the browser history."""
    response = send_request("forward", "POST", {"return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Reload the current page.", context_settings=config.cli_context_settings)
def reload():
    """Reload the current webpage."""
    response = send_request("reload", "POST", {"return_screenshot": config.autoscreenshot})
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Wait for specified time.", context_settings=config.cli_context_settings)
@cl.argument("ms", type=int)
def wait(ms):
    """Wait for the specified number of milliseconds."""
    response = send_request(
        "wait", "POST", {"ms": ms, "return_screenshot": config.autoscreenshot},
    )
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Press keys.", context_settings=config.cli_context_settings)
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
        "keypress", "POST", {"keys": keys_data, "return_screenshot": config.autoscreenshot},
    )
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


@cli.command(short_help="Set window size.", context_settings=config.cli_context_settings)
@cl.argument("width", type=int)
@cl.argument("height", type=int)
def set_window_size(width, height):
    """Set the browser window size to the specified width and height."""
    response = send_request(
        "set_window_size",
        "POST",
        {"width": width, "height": height, "return_screenshot": config.autoscreenshot},
    )
    _print_response_with_metadata(response)
    _autosave_screenshot_from_response(response)


def main():
    cli()


if __name__ == "__main__":
    main()
