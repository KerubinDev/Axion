import os
import pathlib
from typing import Dict, Any, Optional
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import tomli_w

CONFIG_DIR = pathlib.Path.home() / ".akita"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "model": {
        "provider": "openai",
        "name": "gpt-4o-mini",
    }
}

def ensure_config_dir():
    """Ensure the ~/.akita directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> Optional[Dict[str, Any]]:
    """Load configuration from ~/.akita/config.toml."""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None

def save_config(config: Dict[str, Any]):
    """Save configuration to ~/.akita/config.toml."""
    ensure_config_dir()
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(config, f)

def reset_config():
    """Delete the configuration file."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()

def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """Get a specific value from the config."""
    config = load_config()
    if not config:
        return default
    return config.get(section, {}).get(key, default)
