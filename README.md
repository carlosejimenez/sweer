# Sweer - Browser Automation Toolset

Sweer is a browser automation toolset that provides command-line tools for web interaction, built on top of Playwright and Flask. It's designed for automated testing, web scraping, and browser automation tasks.

## Installation

Run the installation script to set up all dependencies:

```bash
cd toolset
./install.sh
```

This will:
- Install Python dependencies (Flask, Requests, Playwright)
- Install Playwright browser dependencies
- Set up Chromium browser executable
- Configure environment variables
- Start the Sweer server in the background

## Architecture

Sweer uses a client-server architecture:

- **Server**: Flask backend (`run_sweer_server`) that manages browser instances via Playwright
- **Client Tools**: Command-line executables in `toolset/bin/` that communicate with the server
- **Library**: Core modules in `toolset/lib/` providing the automation functionality

## Available Tools

### Core Browser Operations
- `open_site <url>` - Open websites or local files
- `close_site` - Close the browser
- `screenshot_site` - Take screenshots
- `reload_page` - Reload current page
- `navigate_back` / `navigate_forward` - Browser navigation

### Mouse & Input Operations
- `click_mouse <x> <y> [<button>]` - Click at coordinates (shows red crosshair)
- `double_click_mouse <x> <y>` - Double-click at coordinates
- `move_mouse <x> <y>` - Move mouse to coordinates
- `drag_mouse <path>` - Drag along a JSON path: `'[[x1,y1],[x2,y2]]'`
- `type_text <text>` - Type text at focused element
- `press_keys_on_page <keys>` - Press keys as JSON: `'["ctrl", "c"]'`

### Page Operations
- `scroll_on_page <x> <y>` - Scroll by pixel amounts
- `execute_script_on_page <script>` - Run JavaScript on page
- `set_browser_window_size <width> <height>` - Resize browser window
- `wait_time <ms>` - Wait for specified milliseconds

## Quick Start

1. **Start the server** (done automatically by `install.sh`):
   ```bash
   run_sweer_server &
   ```

2. **Open a website**:
   ```bash
   open_site https://example.com
   # or open a local file
   open_site /path/to/file.html
   ```

3. **Take a screenshot**:
   ```bash
   screenshot_site
   ```

4. **Interact with the page**:
   ```bash
   click_mouse 100 200
   type_text "Hello World"
   press_keys_on_page '["enter"]'
   ```

## Configuration

Configure Sweer using environment variables:

### Browser Configuration

```bash
# Browser type (default: chromium)
export SWEER_BROWSER_TYPE="chromium"  # or "firefox"

# Custom browser paths
export SWEER_CHROMIUM_EXECUTABLE_PATH="/usr/bin/google-chrome"
export SWEER_FIREFOX_EXECUTABLE_PATH="/usr/bin/firefox"

# Display mode (default: headless)
export SWEER_HEADLESS="0"  # Set to 0 for visible browser window
```

### Window and Screenshot Settings

```bash
# Browser window size
export SWEER_WINDOW_WIDTH="1280"
export SWEER_WINDOW_HEIGHT="720"

# Screenshot behavior
export SWEER_AUTOSCREENSHOT="1"        # Auto-screenshot after actions
export SWEER_SCREENSHOT_MODE="save"    # "save" or "print"
export SWEER_SCREENSHOT_DELAY="0.2"    # Delay in seconds
```

### Server Configuration

```bash
# Server port (default: 8009)
export SWEER_PORT="8009"

# Connection timeout
export SWEER_RECONNECT_TIMEOUT="15"
```

## Examples

### Web Scraping Example
```bash
# Open a news site
open_site https://news.ycombinator.com

# Take a screenshot
screenshot_site

# Click on first story
click_mouse 100 150

# Scroll down
scroll_on_page 0 300

# Go back
navigate_back
```

### Form Automation Example
```bash
# Open a form
open_site https://example.com/contact

# Click in name field
click_mouse 200 100

# Type name
type_text "John Doe"

# Tab to next field
press_keys_on_page '["tab"]'

# Type email
type_text "john@example.com"

# Submit form
press_keys_on_page '["enter"]'
```

### JavaScript Execution Example
```bash
# Execute custom JavaScript
execute_script_on_page "document.querySelector('h1').style.color = 'red'"

# Get page info
execute_script_on_page "console.log(document.title)"
```

## File Structure
