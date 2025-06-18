import os
from dataclasses import dataclass, field

from sweer.utils import ScreenshotMode


@dataclass
class Config:
    """Configuration for the sweer server"""
    base_url: str = os.getenv("SWEER_BASEURL", "http://localhost:8009")
    autoscreenshot: bool = os.getenv("SWEER_AUTOSCREENSHOT", "1") == "1"
    screenshot_mode: ScreenshotMode = ScreenshotMode(
        os.getenv("SWEER_SCREENSHOT_MODE", ScreenshotMode.SAVE.value)
    )
    window_width: int = int(os.getenv("SWEER_WINDOW_WIDTH", 1024))
    window_height: int = int(os.getenv("SWEER_WINDOW_HEIGHT", 768))
    headless: bool = os.getenv("SWEER_HEADLESS", "1") != "0"
    screenshot_delay: float = float(os.getenv("SWEER_SCREENSHOT_DELAY", 0.2))
    crosshair_id: str = "__sweer_crosshair__"
    cli_context_settings: dict = field(default_factory=lambda: {"allow_interspersed_args": False})
