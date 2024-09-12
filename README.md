# SWEer

## Dev setup

```bash
pip install -e '.[dev]'
pre-commit install
```

## Usage

First, start the backend

```bash
sweer-backend
```

Next, start running commands

```bash
sweer open nytimes.com
sweer screenshot
sweer click 0
```

If navigating a lot, you can activate automatic screenshotting with

```bash
export SWEER_AUTOSCREENSHOT="1"
```