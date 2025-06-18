from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest
import requests

from sweer.config import ClientConfig

TEST_SITE_DIR = Path(__file__).parent / "test_site"
TEST_HTML_FILE = TEST_SITE_DIR / "index.html"


config = ClientConfig()


@pytest.fixture(scope="module")
def sweer_backend():
    process = subprocess.Popen(
        ["sweer-backend"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    yield process
    process.terminate()
    process.wait()


def send_request(endpoint, method="GET", data=None):
    url = f"http://localhost:{config.port}/{endpoint}"
    if method == "GET":
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    return response


class TestInvalidRequests:
    def test_malformed_json_request(self, sweer_backend):
        response = requests.post(f"http://localhost:{config.port}/click", data="invalid json")
        assert response.status_code == 400 or response.json()["status"] == "error", (
            "Malformed JSON should return 400 status code or error response"
        )

    def test_missing_content_type(self, sweer_backend):
        response = requests.post(
            f"http://localhost:{config.port}/click",
            data='{"x": 100, "y": 100}',
            headers={"Content-Type": "text/plain"}
        )
        data = response.json()
        assert data["status"] == "error", (
            "Request with wrong Content-Type should return error status"
        )
        assert "JSON" in data["message"], (
            "Error message should mention JSON requirement"
        )

    def test_empty_request_body(self, sweer_backend):
        response = requests.post(
            f"http://localhost:{config.port}/click",
            json=None
        )
        data = response.json()
        assert data["status"] == "error", (
            "Empty request body should return error status"
        )

    def test_missing_required_fields(self, sweer_backend):
        response = send_request("click", "POST", {})
        data = response.json()
        assert data["status"] == "error", (
            "Click request with missing coordinates should return error status"
        )
        assert "request body cannot be empty" in data["message"].lower(), (
            "Error message should indicate empty request body"
        )
        response = send_request("click", "POST", {"x": 100})
        data = response.json()
        assert data["status"] == "error", (
            "Click request missing y coordinate should return error status"
        )
        assert "y" in data["message"], (
            "Error message should mention missing y coordinate"
        )
        response = send_request("click", "POST", {"y": 100})
        data = response.json()
        assert data["status"] == "error", (
            "Click request missing x coordinate should return error status"
        )
        assert "x" in data["message"], (
            "Error message should mention missing x coordinate"
        )


class TestInvalidCoordinates:
    def test_negative_coordinates(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for negative coordinates test"
        )
        response = send_request("click", "POST", {
            "x": -10, "y": 100, "button": "left", "return_screenshot": False
        })
        response = send_request("click", "POST", {
            "x": 100, "y": -10, "button": "left", "return_screenshot": False
        })

    def test_coordinates_outside_viewport(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for outside viewport coordinates test"
        )
        response = send_request("click", "POST", {
            "x": 5000, "y": 5000, "button": "left", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Click with coordinates outside viewport should return error status"
        )

    def test_invalid_coordinate_types(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid coordinate types test"
        )
        response = send_request("click", "POST", {
            "x": "invalid", "y": "invalid", "button": "left", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Click with string coordinates should return error status"
        )


class TestOperationsWithoutOpenWebsite:
    def test_screenshot_without_website(self, sweer_backend):
        send_request("close", "POST")
        response = send_request("screenshot", "GET")
        data = response.json()
        assert data["status"] == "error", (
            "Screenshot without open website should return error status"
        )
        assert "website" in data["message"].lower() or "open" in data["message"].lower(), (
            "Error message should indicate no website is open"
        )

    def test_click_without_website(self, sweer_backend):
        send_request("close", "POST")
        response = send_request("click", "POST", {
            "x": 100, "y": 100, "button": "left", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Click without open website should return error status"
        )

    def test_type_without_website(self, sweer_backend):
        send_request("close", "POST")
        response = send_request("type", "POST", {
            "text": "hello", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Type without open website should return error status"
        )

    def test_scroll_without_website(self, sweer_backend):
        send_request("close", "POST")
        response = send_request("scroll", "POST", {
            "scroll_x": 0, "scroll_y": 100, "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Scroll without open website should return error status"
        )


class TestInvalidURLs:
    def test_invalid_url_format(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": "not-a-valid-url", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Invalid URL format should return error status"
        )
        response = send_request("goto", "POST", {
            "url": "://invalid", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Malformed URL should return error status"
        )

    def test_nonexistent_local_file(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": "file:///nonexistent/path/file.html", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Nonexistent local file should return error status"
        )

    def test_empty_url(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": "", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "success", (
            "Empty URL should return success status (empty url represents cwd)"
        )


class TestInvalidParameters:
    def test_invalid_mouse_button(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid mouse button test"
        )
        response = send_request("click", "POST", {
            "x": 100, "y": 100, "button": "middle", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "success", (
            "Click with invalid mouse button should return success status"
        )
        response = send_request("click", "POST", {
            "x": 100, "y": 100, "button": "invalid", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Click with invalid mouse button should return error status"
        )

    def test_invalid_scroll_values(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid scroll values test"
        )
        response = send_request("scroll", "POST", {
            "scroll_x": "invalid", "scroll_y": "invalid", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Scroll with string values should return error status"
        )

    def test_invalid_window_size(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid window size test"
        )
        response = send_request("set_window_size", "POST", {
            "width": -100, "height": -100, "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Window size with negative dimensions should return error status"
        )
        response = send_request("set_window_size", "POST", {
            "width": 0, "height": 0, "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Window size with zero dimensions should return error status"
        )
        response = send_request("set_window_size", "POST", {
            "width": "invalid", "height": "invalid", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Window size with string dimensions should return error status"
        )


class TestInvalidJavaScript:
    def test_malformed_javascript(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for malformed JavaScript test"
        )
        response = send_request("execute_script", "POST", {
            "script": "invalid javascript syntax {{{", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Malformed JavaScript should return error status"
        )

    def test_javascript_runtime_error(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for JavaScript runtime error test"
        )
        response = send_request("execute_script", "POST", {
            "script": "nonexistentFunction();", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "JavaScript runtime error should return error status"
        )


class TestInvalidDragOperations:
    def test_invalid_drag_path_format(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid drag path test"
        )
        response = send_request("drag", "POST", {
            "path": "invalid json", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Drag with invalid JSON path should return error status"
        )
        response = send_request("drag", "POST", {
            "path": [], "return_screenshot": False
        })
        data = response.json()

    def test_invalid_drag_coordinates(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid drag coordinates test"
        )
        response = send_request("drag", "POST", {
            "path": [["invalid", "invalid"]], "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Drag with invalid coordinate format should return error status"
        )


class TestInvalidKeypress:
    def test_invalid_key_names(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid key names test"
        )
        response = send_request("keypress", "POST", {
            "keys": "InvalidKeyName", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Keypress with invalid key name should return error status"
        )


class TestInvalidWaitTime:
    def test_negative_wait_time(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for negative wait time test"
        )
        response = send_request("wait", "POST", {
            "ms": -1000, "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Wait with negative time should return error status"
        )

    def test_invalid_wait_time_type(self, sweer_backend):
        response = send_request("goto", "POST", {
            "url": f"file://{TEST_HTML_FILE.resolve()}",
            "return_screenshot": False
        })
        assert response.json()["status"] == "success", (
            "Failed to open test page for invalid wait time type test"
        )
        response = send_request("wait", "POST", {
            "ms": "invalid", "return_screenshot": False
        })
        data = response.json()
        assert data["status"] == "error", (
            "Wait with invalid time type should return error status"
        )


class TestInvalidHTTPMethods:
    def test_get_on_post_endpoints(self, sweer_backend):
        response = requests.get(f"http://localhost:{config.port}/click")
        assert response.status_code == 405, (
            "GET request on POST-only endpoint should return 405 Method Not Allowed"
        )
        response = requests.get(f"http://localhost:{config.port}/goto")
        assert response.status_code == 405, (
            "GET request on POST-only endpoint should return 405 Method Not Allowed"
        )

    def test_post_on_get_endpoints(self, sweer_backend):
        response = requests.post(f"http://localhost:{config.port}/screenshot", json={})
        assert response.status_code == 405, (
            "POST request on GET-only endpoint should return 405 Method Not Allowed"
        ) 