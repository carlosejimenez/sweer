from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        return s.getsockname()[1]


TEST_SITE_DIR = Path(__file__).parent / "test_site"
TEST_HTML_FILE = TEST_SITE_DIR / "index.html"
TEST_PORT = get_free_port()
TOOLSET_BIN_DIR = Path(__file__).parent.parent / "toolset" / "bin"


@pytest.fixture(scope="module")
def sweer_backend():
    env = os.environ.copy()
    env["SWEER_PORT"] = str(TEST_PORT)
    env["SWEER_BROWSER_TYPE"] = "chromium"
    
    process = subprocess.Popen(
        [str(TOOLSET_BIN_DIR / "run_sweer_server")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(2)
    yield process
    process.terminate()
    process.wait()


def run_executable(executable_name, *args):
    """Run a standalone executable from the toolset/bin directory."""
    env = os.environ.copy()
    env["SWEER_PORT"] = str(TEST_PORT)
    executable_path = TOOLSET_BIN_DIR / executable_name
    return subprocess.run(
        [str(executable_path)] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )


class TestKeyPress:
    @pytest.mark.slow
    def test_every_key(self, sweer_backend):
        result = run_executable("open_site", str(TEST_HTML_FILE))
        assert result.returncode == 0, (
            f"Open command with '{TEST_HTML_FILE}' should return zero exit code"
        )
        
        # Import the KEY_MAP from the new location
        import sys
        lib_path = str(TOOLSET_BIN_DIR.parent / "lib")
        sys.path.insert(0, lib_path)
        from browser_manager import KEY_MAP
        
        for key in KEY_MAP.keys():
            inputs = json.dumps([key])
            result = run_executable("press_keys_on_page", inputs)
            assert result.returncode == 0, (
                f"Keypress command with '{inputs}' should return zero exit code"
            )


class TestInvalidCLICommands:
    def test_nonexistent_command(self, sweer_backend):
        # With standalone executables, trying to run a nonexistent file raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            run_executable("nonexistent-command")

    def test_help_command(self, sweer_backend):
        result = run_executable("click_mouse", "--help")
        assert result.returncode == 0, (
            "Help command should return zero exit code"
        )
        assert "usage:" in result.stdout.lower() or "help" in result.stdout.lower()


class TestInvalidClickCommands:
    def test_click_missing_coordinates(self, sweer_backend):
        result = run_executable("click_mouse")
        assert result.returncode != 0, (
            "Click command without coordinates should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_click_missing_y_coordinate(self, sweer_backend):
        result = run_executable("click_mouse", "100")
        assert result.returncode != 0, (
            "Click command with only x coordinate should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_click_invalid_coordinate_format(self, sweer_backend):
        result = run_executable("click_mouse", "invalid", "100")
        assert result.returncode != 0, (
            "Click command with invalid x coordinate should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        result = run_executable("click_mouse", "100", "invalid")
        assert result.returncode != 0, (
            "Click command with invalid y coordinate should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        result = run_executable("click_mouse", "100.5", "200.5")
        assert result.returncode != 0, (
            "Click command with invalid coordinates should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()

    def test_click_invalid_button_option(self, sweer_backend):
        result = run_executable("click_mouse", "100", "100", "--button", "invalid")
        assert result.returncode != 0, (
            "Click command with invalid button option should return non-zero exit code"
        )


class TestInvalidDoubleClickCommands:
    def test_double_click_missing_coordinates(self, sweer_backend):
        result = run_executable("double_click_mouse")
        assert result.returncode != 0, (
            "Double-click command without coordinates should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_double_click_invalid_coordinates(self, sweer_backend):
        result = run_executable("double_click_mouse", "invalid", "100")
        assert result.returncode != 0, (
            "Double-click command with invalid coordinates should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()


class TestInvalidMoveCommands:
    def test_move_missing_coordinates(self, sweer_backend):
        result = run_executable("move_mouse")
        assert result.returncode != 0, (
            "Move command without coordinates should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_move_invalid_coordinates(self, sweer_backend):
        result = run_executable("move_mouse", "invalid", "100")
        assert result.returncode != 0, (
            "Move command with invalid coordinates should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()


class TestInvalidScrollCommands:
    def test_scroll_missing_arguments(self, sweer_backend):
        result = run_executable("scroll_on_page")
        assert result.returncode != 0, (
            "Scroll command without arguments should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_scroll_invalid_values(self, sweer_backend):
        result = run_executable("scroll_on_page", "invalid", "100")
        assert result.returncode != 0, (
            "Scroll command with invalid scroll values should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        result = run_executable("scroll_on_page", "100", "invalid")
        assert result.returncode != 0, (
            "Scroll command with invalid scroll values should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()


class TestInvalidTypeCommands:
    def test_type_missing_text(self, sweer_backend):
        result = run_executable("type_text")
        assert result.returncode != 0, (
            "Type command without text should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()


class TestInvalidWaitCommands:
    def test_wait_missing_time(self, sweer_backend):
        result = run_executable("wait_time")
        assert result.returncode != 0, (
            "Wait command without time should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_wait_invalid_time_format(self, sweer_backend):
        result = run_executable("wait_time", "invalid")
        assert result.returncode != 0, (
            "Wait command with invalid time should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        # For negative numbers, the argument parsing might succeed but server should return error
        result = run_executable("wait_time", "-100")
        # Check if either argparse rejects it OR server returns error
        if result.returncode == 0:
            # If executable runs, check for error in output  
            assert "error" in result.stderr.lower()
        else:
            # If argparse rejects it, that's also valid
            assert result.returncode != 0


class TestInvalidKeypressCommands:
    def test_keypress_missing_keys(self, sweer_backend):
        result = run_executable("press_keys_on_page")
        assert result.returncode != 0, (
            "Keypress command without keys should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_keypress_invalid_json(self, sweer_backend):
        run_executable("open_site", str(TEST_HTML_FILE))
        result = run_executable("press_keys_on_page", "invalid json")
        assert result.returncode == 0, (
            "Keypress command with invalid JSON should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Keys must be valid JSON" in result.stderr


class TestInvalidSetWindowSizeCommands:
    def test_set_window_size_missing_arguments(self, sweer_backend):
        result = run_executable("set_browser_window_size")
        assert result.returncode != 0, (
            "Set-window-size command without arguments should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_set_window_size_missing_height(self, sweer_backend):
        result = run_executable("set_browser_window_size", "800")
        assert result.returncode != 0, (
            "Set-window-size command without height should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_set_window_size_invalid_dimensions(self, sweer_backend):
        result = run_executable("set_browser_window_size", "invalid", "600")
        assert result.returncode != 0, (
            "Set-window-size command with invalid width should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        result = run_executable("set_browser_window_size", "800", "invalid")
        assert result.returncode != 0, (
            "Set-window-size command with invalid height should return non-zero exit code"
        )
        assert "invalid" in result.stderr.lower() or "not a valid" in result.stderr.lower()
        
        result = run_executable("set_browser_window_size", "-800", "600")
        assert result.returncode != 0, (
            "Set-window-size command with negative width should return non-zero exit code"
        )


class TestInvalidOpenCommands:
    def test_open_missing_url(self, sweer_backend):
        result = run_executable("open_site")
        assert result.returncode != 0, (
            "Open command without URL should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()


class TestInvalidExecuteScriptCommands:
    def test_execute_script_missing_script(self, sweer_backend):
        result = run_executable("execute_script_on_page")
        assert result.returncode != 0, (
            "Execute-script command without script should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()


class TestInvalidDragCommands:
    def test_drag_missing_path(self, sweer_backend):
        result = run_executable("drag_mouse")
        assert result.returncode != 0, (
            "Drag command without path should return non-zero exit code"
        )
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_drag_invalid_json_path(self, sweer_backend):
        run_executable("open_site", str(TEST_HTML_FILE))
        result = run_executable("drag_mouse", "invalid json")
        assert result.returncode == 0, (
            "Drag command with invalid JSON should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Path must be valid JSON" in result.stderr


class TestInvalidOptionCombinations:
    def test_unknown_global_options(self, sweer_backend):
        result = run_executable("click_mouse", "--unknown-option", "100", "100")
        assert result.returncode != 0, (
            "Command with unknown option should return non-zero exit code"
        )

    def test_unknown_command_options(self, sweer_backend):
        result = run_executable("open_site", "--unknown-option", "http://example.com")
        assert result.returncode != 0, (
            "Command with unknown option should return non-zero exit code"
        )


class TestEdgeCaseArguments:
    def test_extremely_large_coordinates(self, sweer_backend):
        result = run_executable("click_mouse", "999999", "999999")
        assert result.returncode == 0, (
            "Click command with extremely large coordinates should return zero exit code"
        )

    def test_zero_coordinates(self, sweer_backend):
        result = run_executable("click_mouse", "0", "0")
        assert result.returncode == 0, (
            "Click command with zero coordinates should return zero exit code"
        )

    @pytest.mark.slow
    def test_very_long_text_input(self, sweer_backend):
        run_executable("open_site", str(TEST_HTML_FILE))
        long_text = "a" * 10000
        result = run_executable("type_text", long_text)
        assert result.returncode == 0, (
            "Type command with very long text should return zero exit code"
        )

    def test_special_characters_in_text(self, sweer_backend):
        run_executable("open_site", str(TEST_HTML_FILE))
        special_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = run_executable("type_text", special_text)
        assert result.returncode == 0, (
            "Type command with special characters should return zero exit code"
        )

    def test_unicode_text_input(self, sweer_backend):
        run_executable("open_site", str(TEST_HTML_FILE))
        unicode_text = "Hello 世界 🌍 émojis"
        result = run_executable("type_text", unicode_text)
        assert result.returncode == 0, (
            "Type command with unicode text should return zero exit code"
        )
