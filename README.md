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

# Use WebKit (Safari engine)
export SWEER_BROWSER_TYPE="webkit"
sweer-backend

# Use Chromium (default)
export SWEER_BROWSER_TYPE="chromium"
sweer-backend
```

Supported browser types:
- `chromium` (default) - Uses Chromium browser
- `firefox` - Uses Firefox browser  
- `webkit` - Uses WebKit browser (Safari engine)

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
