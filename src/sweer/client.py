#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

# Need to rename the click package so it doesn't clash with
# our click command
import click as cl
import requests

BASE_URL = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
AUTOSCREENSHOT = os.environ.get("SWEER_AUTOSCREENSHOT", "0") == "1"


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


@cl.group()
def cli():
    pass


@cli.command(short_help="Open a website URL.")
@cl.argument("url")
def open(url):
    """Open the specified website URL."""
    if Path(url).is_file():
        url = f"file://{Path(url).resolve()}"
    response = send_request("open", "POST", {"url": url})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Close the current window.")
def close():
    """Close the currently open window."""
    response = send_request("close", "POST")
    print(response["message"])


def autoscreenshot():
    if AUTOSCREENSHOT:
        _screenshot()


def _screenshot(output: str = "", with_overlay: bool = False) -> None:
    response = send_request("screenshot", "GET")

    if not output:
        output = f"screenshot_{response['screenshot_index']:03}.png"

    screenshot_data = response["screenshot"]
    screenshot_data_with_overlay = response["screenshot_with_overlay"]
    path = Path(output)
    path.write_bytes(base64.b64decode(screenshot_data))
    path_with_overlay = Path(output.removesuffix(".png") + "_with_overlay.png")
    if with_overlay:
        path_with_overlay.write_bytes(base64.b64decode(screenshot_data_with_overlay))
    link_path = Path("latest_screenshot.png")
    link_path_with_overlay = Path("latest_screenshot_with_overlay.png")
    link_path.unlink(missing_ok=True)
    link_path.symlink_to(path)
    link_path_with_overlay.unlink(missing_ok=True)
    print(f"Screenshot saved to {path}")
    if with_overlay:
        link_path_with_overlay.symlink_to(path_with_overlay)
        print(f"Screenshot with overlay saved to {path_with_overlay}")
        overlay_info = response["overlay_info"]
        if overlay_info:
            print("\nHere is an overview of all clickable elements:")
            print(overlay_info)


def _save_screenshot(with_overlay: bool = False) -> None:
    response = send_request("screenshot", "GET")
    _cleanup_screenshots()
    screenshot_data = response["screenshot"]
    screenshot_data_with_overlay = response["screenshot_with_overlay"]
    link_path = Path("latest_screenshot.png")
    link_path.write_bytes(base64.b64decode(screenshot_data))
    if with_overlay:
        link_path_with_overlay = Path("latest_screenshot_with_overlay.png")
        link_path_with_overlay.write_bytes(base64.b64decode(screenshot_data_with_overlay))
        overlay_info = response["overlay_info"]
        overlay_path = Path("latest_screenshot_overlay.json")
        overlay_path.write_text(overlay_info)


def _cleanup_screenshots() -> None:
    link_path = Path("latest_screenshot.png")
    link_path_with_overlay = Path("latest_screenshot_with_overlay.png")
    overlay_path = Path("latest_screenshot_overlay.json")
    link_path.unlink(missing_ok=True)
    link_path_with_overlay.unlink(missing_ok=True)
    overlay_path.unlink(missing_ok=True)


@cli.command(short_help="Take a screenshot.")
@cl.option("--output", "-o", default=None, help="Output path for the screenshot.")
@cl.option("--with-overlay", "-w", is_flag=True, help="Capture a screenshot with overlay details.")
def screenshot(output, with_overlay):
    """Capture a screenshot and save it to the specified output path."""
    _screenshot(output, with_overlay)


@cli.command(short_help="Save a screenshot.")
@cl.option("--with-overlay", "-w", is_flag=True, help="Capture a screenshot with overlay details.")
def save_screenshot(with_overlay: bool = False) -> None:
    _save_screenshot(with_overlay)


@cli.command(short_help="Save a screenshot.")
def cleanup_screenshots() -> None:
    _cleanup_screenshots()


@cli.command(short_help="Click on object")
@cl.argument("selector")
def click(selector):
    """Click on an element specified by its selector."""
    response = send_request("click", "POST", {"selector": selector})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Type text into an input field.")
@cl.argument("selector")
@cl.argument("text")
def type(selector, text):
    """Type the given text into an element specified by its selector."""
    response = send_request("type", "POST", {"selector": selector, "text": text})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Scroll the page.")
@cl.argument("direction", type=cl.Choice(["up", "down", "left", "right"]))
@cl.argument("amount", type=int)
def scroll(direction, amount):
    """Scroll the page in the specified direction (up or down) by the given amount (px)."""
    response = send_request("scroll", "POST", {"direction": direction, "amount": amount})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Get text from an element.")
@cl.argument("selector")
def get_text(selector):
    """Retrieve the text content from an element specified by its selector."""
    response = send_request("get_text", "POST", {"selector": selector})
    print(response["message"])


@cli.command(short_help="Get an attribute value from an element.")
@cl.argument("selector")
@cl.argument("attribute")
def get_attribute(selector, attribute):
    """Get the value of a specific attribute from an element identified by its selector."""
    response = send_request("get_attribute", "POST", {"selector": selector, "attribute": attribute})
    print(response["message"])


@cli.command(short_help="Execute a custom JavaScript script.")
@cl.argument("script")
def execute_script(script):
    """Execute a custom JavaScript code snippet on the current page."""
    response = send_request("execute_script", "POST", {"script": script})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Get information about the current page.")
def info():
    """Get information about the current page."""
    response = send_request("info", "GET")
    print(response["message"])


@cli.command(short_help="Navigate through the browser history.")
@cl.argument("direction", type=cl.Choice(["back", "forward"]))
def navigate(direction):
    """Navigate using the specified action (e.g., 'back', 'forward')."""
    response = send_request("navigate", "POST", {"direction": direction})
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="Reload the current page.")
def reload():
    """Reload the current webpage."""
    response = send_request("reload", "POST")
    print(response["message"])
    autoscreenshot()


@cli.command(short_help="List elements matching a selector.")
@cl.argument("selector")
def list_elements(selector):
    """List all elements matching the given selector."""
    response = send_request("list_elements", "POST", {"selector": selector})
    elements = response["elements"]
    print(f"Found {len(elements)} elements")
    for element in elements:
        print(element)


def main():
    cli()


if __name__ == "__main__":
    main()
