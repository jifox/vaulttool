from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str = ".vaulttool.yml") -> Dict[str, Any]:
    """Load the configuration from the vaulttool config file.

    This function attempts to load the configuration from the specified path.
    If the file does not exist, it will search for a default configuration file
    - in the user's home directory (`~/.vaulttool/.vaulttool.yml`) or
    - in a system-wide location. (`/etc/vaulttool/config.yml`).

    Raises:
        FileNotFoundError: If the configuration file is not found in any of the expected locations
        ValueError: If the configuration file is invalid or missing required keys
    """
    config_path = Path(path)

    if not config_path.exists():
        # search for ~/.vaulttool/.vaulttool.yml
        user_config_path = Path.home() / ".vaulttool" / ".vaulttool.yml"
        if user_config_path.exists():
            config_path = user_config_path
        else:
            etc_config_path = Path("/etc/vaulttool/config.yml")
            if etc_config_path.exists():
                config_path = etc_config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {path}. Please create a .vaulttool.yml file or specify the correct path."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Support the documented structure with a top-level `vaulttool` key
    cfg = data.get("vaulttool", data)

    # Ensure the config has the required keys
    if cfg is None or not isinstance(cfg, dict):
        raise ValueError("Invalid configuration format. Expected a dictionary.")

    required_keys = [
        "include_directories",
        "exclude_directories",
        "include_patterns",
        "exclude_patterns",
        "options",
    ]
    missing = [k for k in required_keys if k not in cfg]
    if missing:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")

    # Basic validation of options block
    if not isinstance(cfg.get("options"), dict):
        raise ValueError("'options' must be a mapping/dictionary.")

    return cfg
