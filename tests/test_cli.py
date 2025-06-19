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


@pytest.fixture(scope="module")
def sweer_backend():
    env = os.environ.copy()
    env["SWEER_PORT"] = str(TEST_PORT)
    env["SWEER_BROWSER_TYPE"] = "chromium"
    
    process = subprocess.Popen(
        ["sweer-backend"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(2)
    yield process
    process.terminate()
    process.wait()


def run_sweer_command(*args):
    env = os.environ.copy()
    env["SWEER_PORT"] = str(TEST_PORT)
    return subprocess.run(
        ["sweer"] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )


class TestKeyPress:
    @pytest.mark.slow
    def test_every_key(self, sweer_backend):
        result = run_sweer_command("open", str(TEST_HTML_FILE))
        assert result.returncode == 0, (
            f"Open command with '{TEST_HTML_FILE}' should return zero exit code"
        )
        from sweer.browser_manager import KEY_MAP
        for key in KEY_MAP.keys():
            inputs = json.dumps([key])
            result = run_sweer_command("keypress", inputs)
            assert result.returncode == 0, (
                f"Keypress command with '{inputs}' should return zero exit code"
            )


class TestInvalidCLICommands:
    def test_nonexistent_command(self, sweer_backend):
        result = run_sweer_command("nonexistent-command")
        assert result.returncode != 0, (
            "Nonexistent command should return non-zero exit code"
        )
        assert "No such command" in result.stderr or "Usage:" in result.stderr

    def test_help_command(self, sweer_backend):
        result = run_sweer_command("--help")
        assert result.returncode == 0, (
            "Help command should return zero exit code"
        )
        assert "Usage:" in result.stdout or "Commands:" in result.stdout


class TestInvalidClickCommands:
    def test_click_missing_coordinates(self, sweer_backend):
        result = run_sweer_command("click")
        assert result.returncode != 0, (
            "Click command without coordinates should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_click_missing_y_coordinate(self, sweer_backend):
        result = run_sweer_command("click", "100")
        assert result.returncode != 0, (
            "Click command with only x coordinate should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_click_invalid_coordinate_format(self, sweer_backend):
        result = run_sweer_command("click", "invalid", "100")
        assert result.returncode != 0, (
            "Click command with invalid x coordinate should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("click", "100", "invalid")
        assert result.returncode != 0, (
            "Click command with invalid y coordinate should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("click", "100.5", "200.5")
        assert result.returncode != 0, (
            "Click command with invalid coordinates should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr

    def test_click_invalid_button_option(self, sweer_backend):
        result = run_sweer_command("click", "100", "100", "--button", "invalid")
        assert result.returncode != 0, (
            "Click command with invalid button option should return non-zero exit code"
        )


class TestInvalidDoubleClickCommands:
    def test_double_click_missing_coordinates(self, sweer_backend):
        result = run_sweer_command("double-click")
        assert result.returncode != 0, (
            "Double-click command without coordinates should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_double_click_invalid_coordinates(self, sweer_backend):
        result = run_sweer_command("double-click", "invalid", "100")
        assert result.returncode != 0, (
            "Double-click command with invalid coordinates should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr


class TestInvalidMoveCommands:
    def test_move_missing_coordinates(self, sweer_backend):
        result = run_sweer_command("move")
        assert result.returncode != 0, (
            "Move command without coordinates should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_move_invalid_coordinates(self, sweer_backend):
        result = run_sweer_command("move", "invalid", "100")
        assert result.returncode != 0, (
            "Move command with invalid coordinates should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr


class TestInvalidScrollCommands:
    def test_scroll_missing_arguments(self, sweer_backend):
        result = run_sweer_command("scroll")
        assert result.returncode != 0, (
            "Scroll command without arguments should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_scroll_invalid_values(self, sweer_backend):
        result = run_sweer_command("scroll", "invalid", "100")
        assert result.returncode != 0, (
            "Scroll command with invalid scroll values should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("scroll", "100", "invalid")
        assert result.returncode != 0, (
            "Scroll command with invalid scroll values should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr


class TestInvalidTypeCommands:
    def test_type_missing_text(self, sweer_backend):
        result = run_sweer_command("type")
        assert result.returncode != 0, (
            "Type command without text should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr


class TestInvalidWaitCommands:
    def test_wait_missing_time(self, sweer_backend):
        result = run_sweer_command("wait")
        assert result.returncode != 0, (
            "Wait command without time should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_wait_invalid_time_format(self, sweer_backend):
        result = run_sweer_command("wait", "invalid")
        assert result.returncode != 0, (
            "Wait command with invalid time should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("wait", "-100")


class TestInvalidKeypressCommands:
    def test_keypress_missing_keys(self, sweer_backend):
        result = run_sweer_command("keypress")
        assert result.returncode != 0, (
            "Keypress command without keys should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_keypress_invalid_json(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        result = run_sweer_command("keypress", "invalid json")
        assert result.returncode == 0, (
            "Keypress command with invalid JSON should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Keys must be valid JSON" in result.stderr


class TestInvalidSetWindowSizeCommands:
    def test_set_window_size_missing_arguments(self, sweer_backend):
        result = run_sweer_command("set-window-size")
        assert result.returncode != 0, (
            "Set-window-size command without arguments should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_set_window_size_missing_height(self, sweer_backend):
        result = run_sweer_command("set-window-size", "800")
        assert result.returncode != 0, (
            "Set-window-size command without height should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_set_window_size_invalid_dimensions(self, sweer_backend):
        result = run_sweer_command("set-window-size", "invalid", "600")
        assert result.returncode != 0, (
            "Set-window-size command with invalid width should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("set-window-size", "800", "invalid")
        assert result.returncode != 0, (
            "Set-window-size command with invalid height should return non-zero exit code"
        )
        assert "Invalid value" in result.stderr or "not a valid integer" in result.stderr
        result = run_sweer_command("set-window-size", "-800", "600")
        assert result.returncode != 0, (
            "Set-window-size command with negative width should return non-zero exit code"
        )
        result = run_sweer_command("set-window-size", "800", "-600")
        assert result.returncode == 0, (
            "Set-window-size command with negative height should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Invalid dimensions" in result.stderr


class TestInvalidOpenCommands:
    def test_open_missing_url(self, sweer_backend):
        result = run_sweer_command("open")
        assert result.returncode != 0, (
            "Open command without URL should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr


class TestInvalidExecuteScriptCommands:
    def test_execute_script_missing_script(self, sweer_backend):
        result = run_sweer_command("execute-script")
        assert result.returncode != 0, (
            "Execute-script command without script should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr


class TestInvalidDragCommands:
    def test_drag_missing_path(self, sweer_backend):
        result = run_sweer_command("drag")
        assert result.returncode != 0, (
            "Drag command without path should return non-zero exit code"
        )
        assert "Missing argument" in result.stderr or "Usage:" in result.stderr

    def test_drag_invalid_json_path(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        result = run_sweer_command("drag", "invalid json")
        assert result.returncode == 0, (
            "Drag command with invalid JSON path should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Path must be valid JSON" in result.stderr


class TestInvalidOptionCombinations:
    def test_unknown_global_options(self, sweer_backend):
        result = run_sweer_command("--unknown-option", "open", str(TEST_HTML_FILE))
        assert result.returncode != 0, (
            "Unknown global options should return non-zero exit code"
        )

    def test_unknown_command_options(self, sweer_backend):
        result = run_sweer_command("click", "100", "100", "--unknown-option")
        assert result.returncode != 0, (
            "Unknown command options should return non-zero exit code"
        )


class TestEdgeCaseArguments:
    def test_extremely_large_coordinates(self, sweer_backend):
        result = run_sweer_command("click", "999999999", "999999999")
        assert result.returncode == 0, (
            "Click command with extremely large coordinates should return zero exit code but print error to stderr"
        )
        assert "ERROR:" in result.stderr and "Invalid coordinates" in result.stderr

    def test_zero_coordinates(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        result = run_sweer_command("click", "0", "0")
        assert result.returncode == 0, (
            "Click command with zero coordinates should return zero exit code"
        )

    @pytest.mark.slow
    def test_very_long_text_input(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        long_text = "a" * 10000
        result = run_sweer_command("type", long_text)
        assert result.returncode == 0, (
            "Type command with very long text should return zero exit code"
        )

    def test_special_characters_in_text(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        special_text = "!@#$%^&*()[]{}|\\:;\"'<>?,./"
        result = run_sweer_command("type", special_text)
        assert result.returncode == 0, (
            "Type command with special characters should return zero exit code"
        )

    def test_unicode_text_input(self, sweer_backend):
        run_sweer_command("open", str(TEST_HTML_FILE))
        unicode_text = "hello 世界 🌍 émojis"
        result = run_sweer_command("type", unicode_text)
        assert result.returncode == 0, (
            "Type command with unicode characters should return zero exit code"
        )
