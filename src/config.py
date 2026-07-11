"""
config.py – loads config.json and provides typed access helpers.
"""
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"
_config: dict = {}


def load_config(path: Path | None = None) -> dict:
    """Load (or reload) configuration from *path* (defaults to config.json)."""
    global _config
    p = path or _CONFIG_PATH
    if p.exists():
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        # Remove comment keys so they don't interfere
        _config = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _config


def get(section: str, key: str, default=None):
    """Return config[section][key], or *default* if missing."""
    return _config.get(section, {}).get(key, default)


# Load on import so providers can call get() directly.
load_config()
