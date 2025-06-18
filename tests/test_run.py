from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

TEST_SITE_DIR = Path(__file__).parent / "test_site"
assert TEST_SITE_DIR.exists()
TEST_HTML_FILE = TEST_SITE_DIR / "index.html"
assert TEST_HTML_FILE.exists()


@pytest.fixture(scope="module")
def sweer_backend():
    import time
    process = subprocess.Popen(["sweer-backend"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)
    yield process
    process.terminate()
    process.wait()


def test_backend_starts_successfully(sweer_backend):
    assert sweer_backend.poll() is None
