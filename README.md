# SWEer

## Dev setup

```bash
pip install -e '.[dev]'
pre-commit install
pytest
```

## Usage

First, start the backend

```bash
sweer-backend
```

Next, start running commands

```bash
# If argument is an existing local path, will try to open local file instead
sweer open theguardian.com
sweer screenshot
sweer click 0
```

## Configuration

SWEer can be configured using environment variables:

### Browser Configuration

You can configure which browser backend to use:

```bash
# Use Firefox instead of the default Chromium
export SWEER_BROWSER_TYPE="firefox"
sweer-backend

# Use Chromium (default)
export SWEER_BROWSER_TYPE="chromium"
sweer-backend
```

Supported browser types:
- `chromium` (default) - Uses Chromium browser
- `firefox` - Uses Firefox browser

#### Custom Browser Executable Paths

You can specify custom installations of browsers instead of using Playwright's default bundled browsers:

```bash
# Use a custom Chromium installation
export SWEER_CHROMIUM_EXECUTABLE_PATH="/usr/bin/chromium-browser"
export SWEER_BROWSER_TYPE="chromium"
sweer-backend

# Use a custom Firefox installation
export SWEER_FIREFOX_EXECUTABLE_PATH="/usr/bin/firefox"
export SWEER_BROWSER_TYPE="firefox"
sweer-backend
```

This is useful when:
- You want to use a system-installed browser instead of Playwright's bundled version
- You need to use a specific browser version
- You want to use a browser with custom configurations or extensions pre-installed
- You're working in an environment where Playwright's bundled browsers aren't available

### Other Configuration Options

```bash
# Enable automatic screenshotting after each action
export SWEER_AUTOSCREENSHOT="1"

# Configure window size
export SWEER_WINDOW_WIDTH="1280"
export SWEER_WINDOW_HEIGHT="720"

# Run browser in headed mode (visible window)
export SWEER_HEADLESS="0"

# Change screenshot delay (in seconds)
export SWEER_SCREENSHOT_DELAY="0.5"
```

If navigating a lot, you can activate automatic screenshotting with

```bash
export SWEER_AUTOSCREENSHOT="1"
```
