from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).parent / "test_data"
assert TEST_DIR.exists()
TEST_HTML_FILE = TEST_DIR / "index.html"
assert TEST_HTML_FILE.exists()


@pytest.fixture
def sweer_backend():
    process = subprocess.Popen(["sweer-backend"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    yield process
    process.terminate()
    process.wait()


def _run(command, fail=False, substr=""):
    result = subprocess.run(command, capture_output=True)
    err = result.stderr.decode()
    out = result.stdout.decode()
    if not fail:
        assert result.returncode == 0, (command, err, out)
        if substr:
            assert substr in err + out
    if fail:
        assert result.returncode != 0
        if substr:
            assert substr in err + out


def test_run(sweer_backend):
    for command in [
        (["sweer", "open", "doesnotexist"], True),
        ["sweer", "open", str(TEST_HTML_FILE)],
        ["sweer", "screenshot"],
        ["sweer", "screenshot", "--with-overlay"],
        ["sweer", "click", "0"],
        (["sweer", "click", "1"], True),
        ["sweer", "scroll", "down", "1"],
        ["sweer", "scroll", "up", "1"],
        ["sweer", "scroll", "left", "1"],
        ["sweer", "scroll", "right", "1"],
        ["sweer", "get-text", "#button"],
        ["sweer", "get-attribute", "#div1", "class"],
        (["sweer", "get-attribute", "#div10", "class"], True),
        ["sweer", "execute-script", ""],
        (["sweer", "navigate", "forward"], True, "Already at the most recent"),
        (["sweer", "navigate", "back"], True, "No more pages in history"),
        ["sweer", "reload"],
    ]:
        if isinstance(command, list):
            _run(command)
        if isinstance(command, tuple):
            _run(*command)
