#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
from pathlib import Path

# Need to rename the click package so it doesn't clash with
# our click command
import click as cl
import requests

BASE_URL = os.environ.get("SWEER_BASEURL", "http://localhost:8009")


def send_request(endpoint, method="GET", data=None):
    url = f"{BASE_URL}/{endpoint}"
    if method == "GET":
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    return response.json()


@cl.group()
def cli():
    pass


@cli.command(short_help="Open a website URL.")
@cl.argument("url")
def open(url):
    """Open the specified website URL."""
    response = send_request("open", "POST", {"url": url})
    print(response["message"])


@cli.command(short_help="Close the current window.")
def close():
    """Close the currently open window."""
    response = send_request("close", "POST")
    print(response["message"])


@cli.command(short_help="Take a screenshot.")
def screenshot():
    """Capture a screenshot and save it as 'screenshot.png'."""
    response = requests.get(f"{BASE_URL}/screenshot")
    if response.status_code == 200:
        screenshot_data = response.json()["screenshot"]
        path = Path("screenshot.png")
        path.write_bytes(base64.b64decode(screenshot_data))
        print("Screenshot saved to screenshot.png")


@cli.command(short_help="Simulate a click action.")
@cl.argument("selector")
def click(selector):
    """Click on an element specified by its selector."""
    response = send_request("click", "POST", {"selector": selector})
    print(response["message"])


@cli.command(short_help="Type text into an input field.")
@cl.argument("selector")
@cl.argument("text")
def type(selector, text):
    """Type the given text into an element specified by its selector."""
    response = send_request("type", "POST", {"selector": selector, "text": text})
    print(response["message"])


@cli.command(short_help="Scroll the page.")
@cl.argument("direction")
@cl.argument("amount", type=int)
def scroll(direction, amount):
    """Scroll the page in the specified direction (up or down) by the given amount."""
    response = send_request("scroll", "POST", {"direction": direction, "amount": amount})
    print(response["message"])


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


@cli.command(short_help="Navigate through the browser history.")
@cl.argument("action")
def navigate(action):
    """Navigate using the specified action (e.g., 'back', 'forward')."""
    response = send_request(action, "POST")
    print(response["message"])


@cli.command(short_help="Reload the current page.")
def reload():
    """Reload the current webpage."""
    response = send_request("reload", "POST")
    print(response["message"])


@cli.command(short_help="List elements matching a selector.")
@cl.argument("selector")
def list_elements(selector):
    """List all elements matching the given selector."""
    response = send_request("list_elements", "POST", {"selector": selector})
    elements = response["elements"]
    print(f"Found {len(elements)} elements")
    for element in elements:
        print(element)


if __name__ == "__main__":
    cli()
