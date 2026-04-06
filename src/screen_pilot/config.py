"""Configuration loading and defaults for screen-pilot."""

import copy
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import tomli_w

DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 7222,
    },
    "capture": {
        "tool": "auto",
    },
    "input": {
        "socket": "/run/user/1000/.ydotool_socket",
    },
    "omniparser": {
        "weights_dir": "~/.local/share/screen-pilot/weights",
        "auto_download": True,
        "idle_unload_seconds": 60,
        "device": "auto",
    },
    "backend": {},
    "safety": {
        "max_steps_per_task": 30,
        "min_action_delay": 0.5,
        "confirm_actions": [],
        "emergency_stop": "ctrl+shift+escape",
        "dry_run": False,
        "blocked_regions": [],
        "blocked_patterns": ["sudo rm -rf", ":(){ :|:&", "dd if="],
        "allowed_apps": [],
    },
}

CONFIG_DIR = Path.home() / ".config" / "screen-pilot"
CONFIG_PATH = CONFIG_DIR / "config.toml"


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: Path | None = None) -> dict:
    if path is None:
        path = CONFIG_PATH
    if path.exists():
        with open(path, "rb") as f:
            user_config = tomllib.load(f)
        return _deep_merge(DEFAULT_CONFIG, user_config)
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config: dict, path: Path | None = None) -> None:
    if path is None:
        path = CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(config, f)
