from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

TEST_SITE_DIR = Path(__file__).parent / "test_site"
assert TEST_SITE_DIR.exists()
TEST_HTML_FILE = TEST_SITE_DIR / "index.html"
assert TEST_HTML_FILE.exists()
TOOLSET_BIN_DIR = Path(__file__).parent.parent / "toolset" / "bin"


@pytest.fixture(scope="module")
def sweer_backend():
    process = subprocess.Popen(
        [str(TOOLSET_BIN_DIR / "run_sweer_server")], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    time.sleep(1)
    yield process
    process.terminate()
    process.wait()


def test_backend_starts_successfully(sweer_backend):
    assert sweer_backend.poll() is None


def test_executables_exist():
    """Test that all expected standalone executables exist and are executable."""
    expected_executables = [
        "run_sweer_server",
        "click_mouse", 
        "double_click_mouse",
        "move_mouse",
        "drag_mouse",
        "open_site",
        "close_site", 
        "reload_page",
        "navigate_back",
        "navigate_forward",
        "type_text",
        "press_keys_on_page",
        "scroll_on_page",
        "screenshot_site",
        "execute_script_on_page",
        "set_browser_window_size",
        "wait_time"
    ]
    
    for executable in expected_executables:
        executable_path = TOOLSET_BIN_DIR / executable
        assert executable_path.exists(), f"Executable {executable} should exist"
        assert executable_path.is_file(), f"Executable {executable} should be a file"
        # Check if it's executable (has execute permission)
        assert executable_path.stat().st_mode & 0o111, f"Executable {executable} should have execute permissions"
