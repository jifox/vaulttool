"""Configuration loading and validation for VaultTool.

This module handles loading VaultTool configuration from YAML files,
with support for multiple configuration file locations and validation
of required configuration keys.
"""

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str = ".vaulttool.yml") -> Dict[str, Any]:
    """Load and validate the VaultTool configuration file.

    Attempts to load configuration from the specified path. If the file doesn't
    exist, searches for configuration files in standard locations:
    
    1. Current directory: .vaulttool.yml
    2. User config: ~/.vaulttool/.vaulttool.yml  
    3. System config: /etc/vaulttool/config.yml

    Args:
        path: Path to the configuration file. Defaults to ".vaulttool.yml".

    Returns:
        Dictionary containing the parsed and validated configuration.
        
    Raises:
        FileNotFoundError: If no configuration file is found in any location.
        ValueError: If the configuration file is invalid, malformed, or 
                   missing required keys.
        yaml.YAMLError: If the YAML file cannot be parsed.
        
    Example:
        >>> config = load_config()
        >>> print(config['options']['algorithm'])
        'aes-256-cbc'
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

    # Validate types of required keys
    if not isinstance(cfg.get("include_directories"), list):
        raise ValueError("'include_directories' must be a list")
    if not isinstance(cfg.get("exclude_directories"), list):
        raise ValueError("'exclude_directories' must be a list")
    if not isinstance(cfg.get("include_patterns"), list):
        raise ValueError("'include_patterns' must be a list")
    if not isinstance(cfg.get("exclude_patterns"), list):
        raise ValueError("'exclude_patterns' must be a list")

    # Validate include_patterns is not empty
    if not cfg.get("include_patterns"):
        raise ValueError("'include_patterns' cannot be empty - at least one pattern required")

    # Basic validation of options block
    options = cfg.get("options")
    if not isinstance(options, dict):
        raise ValueError("'options' must be a mapping/dictionary.")
    
    # Validate key_file is specified
    if "key_file" not in options:
        raise ValueError("'options.key_file' is required")
    if not isinstance(options.get("key_file"), str):
        raise ValueError("'options.key_file' must be a string")
    if not options.get("key_file"):
        raise ValueError("'options.key_file' cannot be empty")

    # Suffix validation logic
    suffix = options.get("suffix")
    if isinstance(suffix, str):
        if not suffix.startswith("."):
            if "." in suffix:
                # If a dot is present, ensure it starts with an underscore
                if not suffix.startswith("_"):
                    # Prepend underscore
                    new_suffix = f"_{suffix}"
                    options["suffix"] = new_suffix

    return cfg
