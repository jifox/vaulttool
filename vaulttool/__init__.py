"""VaultTool - Secure file encryption for secrets and configuration files.

This package provides secure encryption and management of sensitive files using
AES-256-CBC encryption with HMAC authentication.
"""

import logging
import sys
from typing import Optional

__version__ = "2.0.0"

# Default logger for the package
_logger: Optional[logging.Logger] = None


def get_logger(name: str = "vaulttool") -> logging.Logger:
    """Get or create the VaultTool logger.

    Args:
        name: Logger name (default: "vaulttool")

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
) -> logging.Logger:
    """Configure logging for VaultTool.

    Sets up the root vaulttool logger with appropriate handlers and formatters.
    This should be called once at application startup, typically from the CLI.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string. If None, uses default format.
        include_timestamp: Whether to include timestamps in log messages

    Returns:
        Configured logger instance

    Example:
        >>> from vaulttool import setup_logging
        >>> import logging
        >>> logger = setup_logging(level=logging.DEBUG)
        >>> logger.info("VaultTool initialized")
    """
    logger = logging.getLogger("vaulttool")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    if format_string is None:
        if include_timestamp:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            # Simpler format without timestamp (better for CLI usage)
            format_string = "%(levelname)s: %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    global _logger
    _logger = logger

    return logger


# For backward compatibility and convenience
__all__ = [
    "__version__",
    "get_logger",
    "setup_logging",
]
