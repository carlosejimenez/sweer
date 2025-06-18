from __future__ import annotations

import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "invalid: marks tests for invalid operations"
    )


@pytest.fixture(autouse=True)
def setup_test_environment():
    os.environ["SWEER_AUTOSCREENSHOT"] = "0"
    os.environ["SWEER_WINDOW_WIDTH"] = "800"
    os.environ["SWEER_WINDOW_HEIGHT"] = "600"
    os.environ["SWEER_HEADLESS"] = "1"
    os.environ["SWEER_SCREENSHOT_DELAY"] = "0.1"
    yield
    for key in [
        "SWEER_AUTOSCREENSHOT",
        "SWEER_WINDOW_WIDTH", 
        "SWEER_WINDOW_HEIGHT",
        "SWEER_HEADLESS",
        "SWEER_SCREENSHOT_DELAY"
    ]:
        os.environ.pop(key, None) 