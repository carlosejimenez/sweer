#!/usr/bin/env python3

from pathlib import Path
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import base64

app = Flask(__name__)

# Global variable to store the browser instance
browser = None

VIMIUM_PATH_DEFAULT = Path("./vimium-master")

def get_browser(*, vimium_extension_path=VIMIUM_PATH_DEFAULT):
    global browser
    if browser is None:
        if not vimium_extension_path.exists():
            raise FileNotFoundError(
                f"Vimium extension path not found: {vimium_extension_path}. "
                "Please follow instructions in readme to first download it."
            )
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f"--disable-extensions-except={vimium_extension_path}")
        options.add_argument(f"--load-extension={vimium_extension_path}")
        browser = webdriver.Chrome(options=options)
    return browser

@app.route('/open', methods=['POST'])
def open_website():
    url = request.json['url']
    browser = get_browser()
    browser.get(url)
    return jsonify({"status": "success", "message": f"Opened {url}"})

@app.route('/close', methods=['POST'])
def close_website():
    global browser
    if browser:
        browser.quit()
        browser = None
        return jsonify({"status": "success", "message": "Closed browser"})
    return jsonify({"status": "error", "message": "No open windows"})


def _activate_vimium_overlay():
    webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()
    webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()
    webdriver.ActionChains(browser).send_keys('f').perform()
    time.sleep(0.1)

def _deactivate_vimium_overlay():
    webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()
    webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()


@app.route('/screenshot', methods=['GET'])
def take_screenshot():
    browser = get_browser()
    if not browser:
        return jsonify({"status": "error", "message": "No open windows"})
    # Make sure to get overlays from vimum
    _activate_vimium_overlay()
    screenshot = browser.get_screenshot_as_base64()
    _deactivate_vimium_overlay()
    return jsonify({"status": "success", "screenshot": screenshot})

@app.route('/click', methods=['POST'])
def click_element():
    selector = request.json['selector']
    browser = get_browser()
    try:
        element = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()
        return jsonify({"status": "success", "message": f"Clicked element {selector}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/click2', methods=['POST'])
def click_vimium():
    selector = request.json['selector']
    browser = get_browser()
    if not browser:
        return jsonify({"status": "error", "message": "No open windows"})
    _activate_vimium_overlay()
    webdriver.ActionChains(browser).send_keys(selector).perform()
    return jsonify({"status": "success", "message": f"Clicked element {selector}"})


@app.route('/type', methods=['POST'])
def type_text():
    selector = request.json['selector']
    text = request.json['text']
    browser = get_browser()
    try:
        element = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element.send_keys(text)
        return jsonify({"status": "success", "message": f"Typed '{text}' into {selector}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/scroll', methods=['POST'])
def scroll_page():
    direction = request.json['direction']
    amount = request.json['amount']
    browser = get_browser()
    try:
        if direction == 'up':
            browser.execute_script(f"window.scrollBy(0, -{amount});")
        elif direction == 'down':
            browser.execute_script(f"window.scrollBy(0, {amount});")
        elif direction == 'left':
            browser.execute_script(f"window.scrollBy(-{amount}, 0);")
        elif direction == 'right':
            browser.execute_script(f"window.scrollBy({amount}, 0);")
        return jsonify({"status": "success", "message": f"Scrolled {direction} by {amount}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/get_text', methods=['POST'])
def get_text():
    selector = request.json['selector']
    browser = get_browser()
    try:
        element = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        text = element.text
        return jsonify({"status": "success", "text": text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/get_attribute', methods=['POST'])
def get_attribute():
    selector = request.json['selector']
    attribute = request.json['attribute']
    browser = get_browser()
    try:
        element = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        value = element.get_attribute(attribute)
        return jsonify({"status": "success", "value": value})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/execute_script', methods=['POST'])
def execute_script():
    script = request.json['script']
    browser = get_browser()
    try:
        browser.execute_script(script)
        return jsonify({"status": "success", "message": "Script executed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/navigate', methods=['POST'])
def navigate():
    direction = request.json['direction']
    browser = get_browser()
    try:
        if direction == 'back':
            browser.back()
        elif direction == 'forward':
            browser.forward()
        return jsonify({"status": "success", "message": f"Navigated {direction}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/reload', methods=['POST'])
def reload_page():
    browser = get_browser()
    try:
        browser.refresh()
        return jsonify({"status": "success", "message": "Page reloaded"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/list_elements', methods=['POST'])
def list_elements():
    selector = request.json['selector']
    browser = get_browser()
    try:
        elements = browser.find_elements(By.CSS_SELECTOR, selector)
        element_list = [element.get_attribute('outerHTML') for element in elements]
        return jsonify({"status": "success", "elements": element_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8009)
    