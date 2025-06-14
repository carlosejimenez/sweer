#!/usr/bin/env python3

from __future__ import annotations

import os
import threading
import time
from typing import Any

from flask import Flask, jsonify, request, Response
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .utils import (
    no_website_open,
    require_website_open,
    catch_error,
    KEY_MAP,
    validate_request,
)

app = Flask(__name__)

# Configuration constants
LOCATE_ELEMENT_TIMEOUT = int(os.environ.get("SWEER_LOCATE_ELEMENT_TIMEOUT", 1))
WINDOW_WIDTH = int(os.environ.get("SWEER_WINDOW_WIDTH", 1024))
WINDOW_HEIGHT = int(os.environ.get("SWEER_WINDOW_HEIGHT", 768))

# Global variable to store the browser instance
BROWSER: None | WebDriver = None
SCREENSHOT_INDEX = 0
SCREENSHOT_LOCK = threading.Lock()


def get_browser():
    global BROWSER
    if BROWSER is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        BROWSER = webdriver.Chrome(options=options)
        BROWSER.set_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
    return BROWSER


def get_screenshot() -> dict[str, Any]:
    browser = get_browser()
    screenshot = browser.get_screenshot_as_base64()
    global SCREENSHOT_INDEX
    with SCREENSHOT_LOCK:
        SCREENSHOT_INDEX += 1
        screenshot_index = SCREENSHOT_INDEX
    return {
        "screenshot": screenshot,
        "screenshot_index": screenshot_index,
    }


def create_response(
    response_data: dict[str, Any], return_screenshot: bool,
) -> Response:
    if return_screenshot:
        screenshot_data = get_screenshot()
        response_data.update(screenshot_data)
    return jsonify(response_data)


@app.route("/info", methods=["GET"])
def info():
    browser = get_browser()
    return_screenshot = request.args.get("return_screenshot", "false") == "true"
    
    if no_website_open(browser):
        response_data = {"status": "success", "message": "No website open"}
    else:
        width = browser.get_window_size().get("width")
        height = browser.get_window_size().get("height")
        response_data = {
            "status": "success",
            "message": (
                f"Current URL: {browser.current_url}, "
                f"Window dimensions: {width}x{height}"
            )
        }
    return create_response(response_data, return_screenshot and not no_website_open(browser))


@app.route("/close", methods=["POST"])
def close_browser():
    global BROWSER
    if BROWSER:
        BROWSER.quit()
        BROWSER = None
        return create_response({"status": "success", "message": "Closed browser"}, False)
    return create_response({"status": "error", "message": "No open windows"}, False)


@app.route("/set_window_size", methods=["POST"])
@validate_request("width", "height", "return_screenshot")
@require_website_open
@catch_error
def set_window_size():
    width = request.json["width"]
    height = request.json["height"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    browser.set_window_size(width, height)
    response_data = {"status": "success", "message": f"Set window size to {width}x{height}"}
    return create_response(response_data, return_screenshot)


@app.route("/screenshot", methods=["GET"])
@require_website_open
def take_screenshot():
    return create_response({"status": "success"}, True)


@app.route("/click", methods=["POST"])
@validate_request("x", "y", "button", "return_screenshot")
@catch_error
@require_website_open
def click_element():
    x = request.json["x"]
    y = request.json["y"]
    button = request.json["button"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    if button.lower() == "right":
        action = ActionChains(browser)
        action.move_by_offset(x, y).context_click().perform()
    else:
        assert button.lower() == "left", f"Invalid button: {button}"
        action = ActionChains(browser)
        action.move_by_offset(x, y).click().perform()
    response_data = {"status": "success", "message": f"Clicked {button} button at coordinates ({x}, {y})"}
    return create_response(response_data, return_screenshot)


@app.route("/double_click", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def double_click_element():
    x = request.json["x"]
    y = request.json["y"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    action = ActionChains(browser)
    action.move_by_offset(x, y).double_click().perform()
    response_data = {"status": "success", "message": f"Double-clicked at coordinates ({x}, {y})"}
    return create_response(response_data, return_screenshot)


@app.route("/move", methods=["POST"])
@validate_request("x", "y", "return_screenshot")
@catch_error
@require_website_open
def move_mouse():
    x = request.json["x"]
    y = request.json["y"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    action = ActionChains(browser)
    action.move_by_offset(x, y).perform()
    response_data = {"status": "success", "message": f"Moved mouse to coordinates ({x}, {y})"}
    return create_response(response_data, return_screenshot)


@app.route("/drag", methods=["POST"])
@validate_request("path", "return_screenshot")
@catch_error
@require_website_open
def drag_mouse():
    path = request.json["path"]
    return_screenshot = request.json["return_screenshot"]
    if len(path) < 2:
        return create_response(
            {
                "status": "error",
                "message": "Path must contain at least 2 points",
            },
            False,
        )
    browser = get_browser()
    action = ActionChains(browser)
    start_point = path[0]
    action.move_by_offset(start_point["x"], start_point["y"])
    action.click_and_hold()
    for i in range(1, len(path)):
        current_point = path[i]
        prev_point = path[i-1]
        delta_x = current_point["x"] - prev_point["x"]
        delta_y = current_point["y"] - prev_point["y"]
        action.move_by_offset(delta_x, delta_y)
    action.release()
    action.perform()
    response_data = {
        "status": "success",
        "message": f"Dragged along path with {len(path)} points",
    }
    return create_response(response_data, return_screenshot)


@app.route("/type", methods=["POST"])
@validate_request("text", "return_screenshot")
@require_website_open
@catch_error
def type_text():
    browser = get_browser()
    text = request.json["text"]
    return_screenshot = request.json["return_screenshot"]
    action = ActionChains(browser)
    action.send_keys(text).perform()
    response_data = {"status": "success", "message": f"Typed '{text}'"}
    return create_response(response_data, return_screenshot)


@app.route("/scroll", methods=["POST"])
@validate_request("x", "y", "scroll_x", "scroll_y", "return_screenshot")
@require_website_open
@catch_error
def scroll_page():
    browser = get_browser()
    x = request.json["x"]
    y = request.json["y"]
    scroll_x = request.json["scroll_x"]
    scroll_y = request.json["scroll_y"]
    return_screenshot = request.json["return_screenshot"]
    action = ActionChains(browser)
    action.move_by_offset(x, y).perform()
    browser.execute_script(f"window.scrollBy({scroll_x}, {scroll_y});")
    response_data = {
        "status": "success",
        "message": f"Scrolled by ({scroll_x}, {scroll_y}) at position ({x}, {y})",
    }
    return create_response(response_data, return_screenshot)


@app.route("/get_text", methods=["POST"])
@validate_request("selector", "return_screenshot")
@require_website_open
@catch_error
def get_text():
    selector = request.json["selector"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    try:
        element = WebDriverWait(browser, LOCATE_ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        return create_response({"status": "error", "message": f"Element specified by the CSS selector {selector!r} not found"}, False)
    text = element.text
    response_data = {
        "status": "success",
        "message": f"Text of element selected by {selector!r}: {text!r}",
    }
    return create_response(response_data, return_screenshot)


@app.route("/get_attribute", methods=["POST"])
@validate_request("selector", "attribute", "return_screenshot")
@require_website_open
@catch_error
def get_attribute():
    selector = request.json["selector"]
    attribute = request.json["attribute"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    try:
        element = WebDriverWait(browser, LOCATE_ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        return create_response(
            {
                "status": "error",
                "message": f"Element specified by the CSS selector {selector!r} not found.",
            },
            False,
        )
    value = element.get_attribute(attribute)
    response_data = {
        "status": "success",
        "message": f"Attribute {attribute} for the element specified by the CSS selector {selector!r}: {value!r}",
    }
    return create_response(response_data, return_screenshot)


@app.route("/execute_script", methods=["POST"])
@validate_request("script", "return_screenshot")
@require_website_open
@catch_error
def execute_script():
    browser = get_browser()
    script = request.json["script"]
    return_screenshot = request.json["return_screenshot"]
    browser.execute_script(script)
    response_data = {"status": "success", "message": "Script executed successfully"}
    return create_response(response_data, return_screenshot)


@app.route("/back", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def navigate_back():
    browser = get_browser()
    return_screenshot = request.json["return_screenshot"]
    browser.back()
    if no_website_open(browser):
        browser.forward()
        return create_response({"status": "error", "message": f"No more pages in history, still at {browser.current_url}."}, False)
    response_data = {
        "status": "success",
        "message": "Navigated back",
    }
    return create_response(response_data, return_screenshot)


@app.route("/forward", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def navigate_forward():
    browser = get_browser()
    return_screenshot = request.json["return_screenshot"]
    previous_url = browser.current_url
    browser.forward()
    if browser.current_url == previous_url:
        return create_response(
            {
                "status": "error",
                "message": f"Already at the most recent page ({browser.current_url}).",
            },
            False,
        )
    response_data = {
        "status": "success",
        "message": "Navigated forward",
    }
    return create_response(response_data, return_screenshot)


@app.route("/reload", methods=["POST"])
@validate_request("return_screenshot")
@catch_error
@require_website_open
def reload_page():
    browser = get_browser()
    return_screenshot = request.json["return_screenshot"]
    browser.refresh()
    response_data = {"status": "success", "message": "Page reloaded"}
    return create_response(response_data, return_screenshot)


@app.route("/list_elements", methods=["POST"])
@validate_request("selector", "return_screenshot")
@catch_error
@require_website_open
def list_elements():
    selector = request.json["selector"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    elements = browser.find_elements(By.CSS_SELECTOR, selector)
    element_list = [element.get_attribute("outerHTML") for element in elements]
    response_data = {"status": "success", "elements": element_list}
    return create_response(response_data, return_screenshot)


@app.route("/wait", methods=["POST"])
@validate_request("ms", "return_screenshot")
@catch_error
def wait():
    ms = request.json["ms"]
    return_screenshot = request.json["return_screenshot"]
    time.sleep(ms / 1000.0)  # convert milliseconds to seconds
    response_data = {"status": "success", "message": f"Waited {ms} milliseconds"}
    return create_response(response_data, return_screenshot)


@app.route("/keypress", methods=["POST"])
@validate_request("keys", "return_screenshot")
@catch_error
@require_website_open
def keypress():
    keys = request.json["keys"]
    return_screenshot = request.json["return_screenshot"]
    browser = get_browser()
    action = ActionChains(browser)
    modifier_keys = []
    main_keys = []
    for key in keys:
        key_upper = key.upper()
        if key_upper in ['CTRL', 'CONTROL', 'SHIFT', 'ALT', 'CMD', 'COMMAND', 'META']:
            modifier_keys.append(KEY_MAP[key_upper])
        elif key_upper in KEY_MAP:
            main_keys.append(KEY_MAP[key_upper])
        else:
            main_keys.append(key)
    for mod_key in modifier_keys:
        action.key_down(mod_key)
    for main_key in main_keys:
        if isinstance(main_key, str) and len(main_key) == 1:
            action.send_keys(main_key)
        else:
            action.send_keys(main_key)
    for mod_key in reversed(modifier_keys):
        action.key_up(mod_key)
    action.perform()
    response_data = {"status": "success", "message": f"Executed keypress: {keys}"}
    return create_response(response_data, return_screenshot)


@app.route("/goto", methods=["POST"])
@validate_request("url", "return_screenshot")
@catch_error
def goto_url():
    url = request.json["url"]
    return_screenshot = request.json["return_screenshot"]
    if "://" not in url:
        url = "https://" + url
    browser = get_browser()
    time.sleep(0.3)
    print(f"Opening {url}")
    try:
        browser.get(url)
    except WebDriverException as e:
        if "net::ERR_NAME_NOT_RESOLVED" in str(e):
            return create_response({"status": "error", "message": f"Could not resolve {url}"}, False)
    response_data = {"status": "success", "message": f"Navigated to {url}"}
    return create_response(response_data, return_screenshot)


def main():
    base_url = os.environ.get("SWEER_BASEURL", "http://localhost:8009")
    port = int(base_url.split(":")[-1])
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
