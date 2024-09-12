#!/usr/bin/env python3

from __future__ import annotations

import functools
import os
from pathlib import Path
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException

app = Flask(__name__)

# Global variable to store the browser instance
BROWSER: None|WebDriver = None
OVERLAY_INFO = None
MAX_OVERLAY_INFO_TEXT_LENGTH = int(os.environ.get("SWEER_MAX_OVERLAY_INFO_TEXT_LENGTH", 50))
LOCATE_ELEMENT_TIMEOUT = int(os.environ.get("SWEER_LOCATE_ELEMENT_TIMEOUT", 1))
SCREENSHOT_INDEX = 0
OVERLAY_SCRIPT_PATH = Path(__file__).parent / "overlay.js"


def get_browser():
    global BROWSER
    if BROWSER is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        BROWSER = webdriver.Chrome(options=options)
    return BROWSER


def no_website_open(browser: WebDriver):
    return browser.current_url == "data:,"


def require_website_open(func):
    """Decorator to ensure that a website is open before executing a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
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


@app.route("/open", methods=["POST"])
@catch_error
def open_website():
    url = request.json["url"]
    if "://" not in url:
        url = "https://" + url
    browser = get_browser()
    try:
        browser.get(url)
    except WebDriverException as e:
        if "net::ERR_NAME_NOT_RESOLVED" in str(e):
            return jsonify({"status": "error", "message": f"Could not resolve {url}"})
    return jsonify({"status": "success", "message": f"Opened {url}"})


@app.route("/close", methods=["POST"])
def close_browser():
    global BROWSER
    if BROWSER:
        BROWSER.quit()
        BROWSER = None
        return jsonify({"status": "success", "message": "Closed browser"})
    return jsonify({"status": "error", "message": "No open windows"})


def _activate_vimium_style_overlay(browser: WebDriver) -> None:
    script = OVERLAY_SCRIPT_PATH.read_text()
    browser.execute_script(script)
    global OVERLAY_INFO
    OVERLAY_INFO = browser.execute_script("return overlays.drawAllShortcutOverlays();")


def _deactivate_vimium_style_overlay(browser: WebDriver) -> None:
    browser.execute_script("overlays.removeShortcutOverlays();")


def format_clickable_elements(overlays: list[dict[str, str]], max_text_length=MAX_OVERLAY_INFO_TEXT_LENGTH) -> str:
    def clean_text(text: str) -> str:
        # replace newlines with backslash variants etc.
        # also puts quotes around the text
        text = repr(text)
        if len(text) > max_text_length:
            return text[:max_text_length] + "..."
        return text

    out = ""
    for overlay in overlays:
        out += f"{overlay['label'].rjust(3)} - "
        if not overlay["id"].startswith("RANDOM_ID"):
            out += f"ID={overlay['id']!r} "
        for key in ['type', 'class', 'text', 'ariaLabel']:
            if isinstance(overlay[key], str) and overlay[key].strip():
                value_fmted = clean_text(overlay[key])
                out += f"{key}={value_fmted} "
        out += "\n"
    return out


@app.route("/screenshot", methods=["GET"])
@require_website_open
def take_screenshot():
    browser = get_browser()
    _activate_vimium_style_overlay(browser)
    screenshot = browser.get_screenshot_as_base64()
    _deactivate_vimium_style_overlay(browser)
    global OVERLAY_INFO
    assert OVERLAY_INFO is not None
    global SCREENSHOT_INDEX
    SCREENSHOT_INDEX += 1
    return jsonify({"status": "success", "screenshot": screenshot, "overlay_info": format_clickable_elements(OVERLAY_INFO), "screenshot_index": SCREENSHOT_INDEX})


def _click_selector(selector: str, *, confirmation_text=""):
    browser = get_browser()
    try:
        element = WebDriverWait(browser, LOCATE_ELEMENT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        message = f"Element specified by the CSS selector {selector!r} not found or not clickable"
        return jsonify({"status": "error", "message": message})
    element.click()
    confirmation_text = confirmation_text or f"Clicked element {selector}"
    return jsonify({"status": "success", "message": confirmation_text})


def _click_overlay(label: str):
    if not OVERLAY_INFO:
        return jsonify({"status": "error", "message": "Overlay info not found"})
    print(f"Searching for overlay with label {label}")
    for overlay in OVERLAY_INFO:
        if label == overlay["label"]:
            selector = f"#{overlay['id']}"
            return _click_selector(selector, confirmation_text=f"Clicked on element with label {label}")
    message = (
        f"Overlay with label {label} not found. Here are the elements that can be clicked:\n\n" +
        format_clickable_elements(OVERLAY_INFO) + 
        "\nThe first column is the label."
    )
    return jsonify({"status": "error", "message": message})


@app.route("/click", methods=["POST"])
@catch_error
@require_website_open
def click_element():
    selector = request.json["selector"]
    if len(selector) >= 4 or not selector.isnumeric():
        return _click_selector(selector)
    return _click_overlay(selector)


@app.route("/type", methods=["POST"])
@require_website_open
@catch_error
def type_text():
    browser = get_browser()
    selector = request.json["selector"]
    text = request.json["text"]
    element = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    element.send_keys(text)
    return jsonify({"status": "success", "message": f"Typed '{text}' into {selector}"})


@app.route("/scroll", methods=["POST"])
@require_website_open
@catch_error
def scroll_page():
    browser = get_browser()
    direction = request.json["direction"]
    amount = request.json["amount"]
    if direction == "up":
        browser.execute_script(f"window.scrollBy(0, -{amount});")
    elif direction == "down":
        browser.execute_script(f"window.scrollBy(0, {amount});")
    elif direction == "left":
        browser.execute_script(f"window.scrollBy(-{amount}, 0);")
    elif direction == "right":
        browser.execute_script(f"window.scrollBy({amount}, 0);")
    return jsonify({"status": "success", "message": f"Scrolled {direction} by {amount}"})


@app.route("/get_text", methods=["POST"])
@require_website_open
@catch_error
def get_text():
    selector = request.json["selector"]
    browser = get_browser()
    try:
        element = WebDriverWait(browser, LOCATE_ELEMENT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        return jsonify({"status": "error", "message": f"Element specified by the CSS selector {selector!r} not found"})
    text = element.text
    return jsonify({"status": "success", "message": f"Text of element selected by {selector!r}: {text!r}"})


@app.route("/get_attribute", methods=["POST"])
@require_website_open
@catch_error
def get_attribute():
    selector = request.json["selector"]
    attribute = request.json["attribute"]
    browser = get_browser()
    try:
        element = WebDriverWait(browser, LOCATE_ELEMENT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        return jsonify({"status": "error", "message": f"Element specified by the CSS selector {selector!r} not found."})
    value = element.get_attribute(attribute)
    return jsonify({"status": "success", "message": f"Attribute {attribute} for the element specified by the CSS selector {selector!r}: {value!r}"})


@app.route("/execute_script", methods=["POST"])
@require_website_open
@catch_error
def execute_script():
    browser = get_browser()
    script = request.json["script"]
    browser.execute_script(script)
    return jsonify({"status": "success", "message": "Script executed successfully"})


@app.route("/navigate", methods=["POST"])
@catch_error
@require_website_open
def navigate():
    browser = get_browser()
    direction = request.json["direction"]
    if direction == "back":
        browser.back()
        if no_website_open(browser):
            browser.forward()
            return jsonify({"status": "error", "message": f"No more pages in history, still at {browser.current_url}."})
    elif direction == "forward":
        previous_url = browser.current_url
        browser.forward()
        if browser.current_url == previous_url:
            return jsonify({"status": "error", "message": f"Already at the most recent page ({browser.current_url})."})
    else:
        return jsonify({"status": "error", "message": f"Invalid direction {direction}. Use 'back' or 'forward'."})
    return jsonify({"status": "success", "message": f"Navigated {direction}"})


@app.route("/reload", methods=["POST"])
@catch_error
@require_website_open
def reload_page():
    browser = get_browser()
    browser.refresh()
    return jsonify({"status": "success", "message": "Page reloaded"})


@app.route("/list_elements", methods=["POST"])
@catch_error
@require_website_open
def list_elements():
    selector = request.json["selector"]
    browser = get_browser()
    elements = browser.find_elements(By.CSS_SELECTOR, selector)
    element_list = [element.get_attribute("outerHTML") for element in elements]
    return jsonify({"status": "success", "elements": element_list})


def main():
    base_url = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
    port = int(base_url.split(":")[-1])
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
