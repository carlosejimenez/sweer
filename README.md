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
sweer open nytimes.com
sweer screenshot
sweer click 0
```

If navigating a lot, you can activate automatic screenshotting with

```bash
export SWEER_AUTOSCREENSHOT="1"
```
