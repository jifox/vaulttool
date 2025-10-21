"""Configuration loading and validation for VaultTool.

This module handles loading VaultTool configuration from YAML files,
with support for multiple configuration file locations, environment variable
overrides, and validation of required configuration keys.

Environment Variable Support:
    Configuration can be overridden using environment variables with the
    VAULTTOOL_ prefix. For list values, use comma-separated strings.

    Examples:
        VAULTTOOL_OPTIONS_KEY_FILE=/path/to/key
        VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK=true
        VAULTTOOL_INCLUDE_PATTERNS="*.env,*.secret"
        VAULTTOOL_EXCLUDE_DIRECTORIES=".git,.venv"
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml


def _parse_bool(value: str) -> bool:
    """Parse boolean value from string.

    Args:
        value: String value to parse (case-insensitive)

    Returns:
        Boolean value

    Example:
        >>> _parse_bool("true")
        True
        >>> _parse_bool("false")
        False
        >>> _parse_bool("1")
        True
    """
    return value.lower() in ("true", "yes", "1", "on")


def _parse_list(value: str) -> List[str]:
    """Parse comma-separated list from string.

    Args:
        value: Comma-separated string

    Returns:
        List of stripped strings

    Example:
        >>> _parse_list("*.env, *.ini, *.secret")
        ['*.env', '*.ini', '*.secret']
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Environment variables with VAULTTOOL_ prefix override config values.
    Nested keys use double underscores, e.g., VAULTTOOL_OPTIONS_KEY_FILE.
    Lists use comma-separated values.

    Args:
        config: Base configuration dictionary

    Returns:
        Configuration with environment overrides applied

    Example:
        export VAULTTOOL_OPTIONS_KEY_FILE=/custom/key
        export VAULTTOOL_INCLUDE_PATTERNS="*.env,*.secret"
    """
    env_prefix = "VAULTTOOL_"

    # Map of config keys to environment variable names
    env_mappings = {
        # Top-level lists
        "include_directories": f"{env_prefix}INCLUDE_DIRECTORIES",
        "exclude_directories": f"{env_prefix}EXCLUDE_DIRECTORIES",
        "include_patterns": f"{env_prefix}INCLUDE_PATTERNS",
        "exclude_patterns": f"{env_prefix}EXCLUDE_PATTERNS",

        # Options (nested)
        "options.suffix": f"{env_prefix}OPTIONS_SUFFIX",
        "options.key_file": f"{env_prefix}OPTIONS_KEY_FILE",
        "options.algorithm": f"{env_prefix}OPTIONS_ALGORITHM",
        "options.openssl_path": f"{env_prefix}OPTIONS_OPENSSL_PATH",
        "options.use_suffix_fallback": f"{env_prefix}OPTIONS_USE_SUFFIX_FALLBACK",
    }

    for config_key, env_var in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value is None:
            continue

        # Parse the configuration key path
        if "." in config_key:
            # Nested key (e.g., "options.key_file")
            parent_key, child_key = config_key.split(".", 1)

            # Ensure parent exists
            if parent_key not in config:
                config[parent_key] = {}
            if not isinstance(config[parent_key], dict):
                config[parent_key] = {}

            # Determine value type and parse
            if child_key in ("use_suffix_fallback",):
                # Boolean values
                config[parent_key][child_key] = _parse_bool(env_value)
            else:
                # String values
                config[parent_key][child_key] = env_value
        else:
            # Top-level key
            if config_key.endswith(("_directories", "_patterns")):
                # List values
                config[config_key] = _parse_list(env_value)
            else:
                # String values
                config[config_key] = env_value

    return config


def load_config(path: str = ".vaulttool.yml") -> Dict[str, Any]:
    """Load and validate the VaultTool configuration file.

    Attempts to load configuration from the specified path. If the file doesn't
    exist, searches for configuration files in standard locations:

    1. Current directory: .vaulttool.yml
    2. User config: ~/.vaulttool/.vaulttool.yml
    3. System config: /etc/vaulttool/config.yml

    After loading, applies environment variable overrides with VAULTTOOL_ prefix.
    Environment variables override file configuration.

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

        >>> # With environment override:
        >>> os.environ['VAULTTOOL_OPTIONS_KEY_FILE'] = '/custom/key'
        >>> config = load_config()
        >>> print(config['options']['key_file'])
        '/custom/key'
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

    # Apply environment variable overrides
    cfg = _apply_env_overrides(cfg)

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
        # Check if suffix contains a dot at all
        if "." not in suffix:
            raise ValueError("Suffix must contain a dot (e.g., .vault, .secret.vault)")

        # If suffix comes from environment variable, enforce .vault ending
        # Check if VAULTTOOL_OPTIONS_SUFFIX is set
        if os.environ.get("VAULTTOOL_OPTIONS_SUFFIX"):
            if not suffix.endswith(".vault"):
                raise ValueError(f"'options.suffix' from environment must end with '.vault', got: {suffix}")

        if not suffix.startswith("."):
            # If a dot is present but doesn't start with dot, ensure it starts with underscore
            if not suffix.startswith("_"):
                # Prepend underscore
                new_suffix = f"_{suffix}"
                options["suffix"] = new_suffix

    # Ensure exclude_patterns contains the suffix pattern
    exclude_patterns = cfg.get("exclude_patterns", [])
    suffix_pattern = f"*{suffix}" if suffix else "*.vault"
    if suffix_pattern not in exclude_patterns:
        # Add suffix pattern to exclude_patterns to avoid self-encryption
        cfg["exclude_patterns"].append(suffix_pattern)

    return cfg
