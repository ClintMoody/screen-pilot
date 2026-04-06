import os
import tempfile
from pathlib import Path

from screen_pilot.config import load_config, DEFAULT_CONFIG


def test_default_config_has_required_sections():
    cfg = DEFAULT_CONFIG
    assert "server" in cfg
    assert "capture" in cfg
    assert "input" in cfg
    assert "omniparser" in cfg
    assert "backend" in cfg
    assert "safety" in cfg
    assert cfg["server"]["port"] == 7222


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[server]\nport = 9999\n')
        f.flush()
        try:
            cfg = load_config(Path(f.name))
            assert cfg["server"]["port"] == 9999
            assert cfg["safety"]["max_steps_per_task"] == 30
        finally:
            os.unlink(f.name)


def test_load_config_missing_file_returns_defaults():
    cfg = load_config(Path("/nonexistent/config.toml"))
    assert cfg["server"]["port"] == 7222


def test_safety_blocked_patterns_default():
    cfg = DEFAULT_CONFIG
    assert "sudo rm -rf" in cfg["safety"]["blocked_patterns"]
