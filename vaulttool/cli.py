
"""Command-line interface for VaultTool.

This module provides the command-line interface for VaultTool using Typer.
It exposes the main VaultTool functionality through a set of subcommands
for encrypting, decrypting, and managing vault files.

Available commands:
- encrypt: Encrypt source files to vault files
- refresh: Decrypt vault files to restore source files  
- remove: Delete all vault files
- check-ignore: Validate .gitignore entries for source files
- version: Display VaultTool version information
- gen-vaulttool: Generate example configuration file
"""

import logging
import sys
import typer
from . import setup_logging, get_logger
from .core import VaultTool

# Create app with proper help text
app = typer.Typer(
    help="""Secure file encryption for secrets and configuration files.

Encrypts sensitive files using AES-256-CBC and manages their encrypted counterparts.

Key Options:
  encrypt --force      Re-encrypt all files (ignores checksums)
  refresh --no-force   Only restore missing files
  
Config: .vaulttool.yml (current dir) or ~/.vaulttool/.vaulttool.yml

Examples:
  vaulttool gen-vaulttool > .vaulttool.yml    # Generate config file
  vaulttool encrypt          # Encrypt changed files only
  vaulttool refresh          # Restore all source files  
  vaulttool remove           # Delete all vault files
  
  vaulttool --verbose encrypt    # Show detailed debug logs
  vaulttool --quiet refresh      # Show errors only
"""
)

# Global options for logging control
verbose_option = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
quiet_option = typer.Option(False, "--quiet", "-q", help="Show only errors (suppress info/warning)")


def _setup_cli_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Configure logging for CLI based on verbosity flags.
    
    Args:
        verbose: Enable DEBUG level logging
        quiet: Show only ERROR and CRITICAL messages
        
    Returns:
        Configured logger instance
    """
    if verbose and quiet:
        typer.echo("Warning: --verbose and --quiet are mutually exclusive. Using --verbose.", err=True)
        quiet = False
    
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    
    return setup_logging(level=level, include_timestamp=False)


def _get_version() -> str:
    """Get the version of vaulttool package."""
    logger = get_logger(__name__)
    
    try:
        from importlib.metadata import version
        pkg_version = version("vaulttool")
        logger.debug(f"Retrieved version from importlib.metadata: {pkg_version}")
        return pkg_version
    except ImportError:
        # importlib.metadata not available in older Python versions
        logger.debug("importlib.metadata not available, trying fallback")
    except Exception as e:
        # Package not found or other metadata error
        logger.warning(f"Failed to get version from metadata: {e}")
    
    # Fallback - try to read from pyproject.toml if available
    try:
        from pathlib import Path
        
        # Look for pyproject.toml in parent directories
        current_dir = Path(__file__).parent
        logger.debug(f"Looking for pyproject.toml starting from {current_dir}")
        
        for level in range(3):  # Check up to 3 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                logger.debug(f"Found pyproject.toml at {pyproject_path}")
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    # Simple parsing for version
                    for line in content.split('\n'):
                        if line.strip().startswith('version = "'):
                            fallback_version = line.split('"')[1]
                            logger.debug(f"Extracted version from pyproject.toml: {fallback_version}")
                            return fallback_version
            current_dir = current_dir.parent
            logger.debug(f"Level {level + 1}: No pyproject.toml found, checking parent")
            
    except (IOError, OSError) as e:
        logger.warning(f"Failed to read pyproject.toml: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error reading pyproject.toml: {e}")
    
    logger.debug("Using development version fallback")
    return "unknown (development version)"


@app.command("version")
def version_cmd(
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Display VaultTool version information.
    
    Shows the currently installed version of VaultTool along with
    basic package information.
    
    Args:
        verbose: Enable verbose debug logging
        quiet: Show only errors
    """
    _setup_cli_logging(verbose, quiet)
    pkg_version = _get_version()
    typer.echo(f"VaultTool version {pkg_version}")


@app.command("gen-vaulttool")
def gen_config():
    """Generate an example .vaulttool.yml configuration file.
    
    Displays a formatted example configuration file that can be saved as
    .vaulttool.yml to configure VaultTool for your project. The configuration
    includes all available options with comments explaining their purpose.
    
    Example:
        vaulttool gen-vaulttool > .vaulttool.yml
    """
    example_config = """---
# .vaulttool.yml - VaultTool Configuration File
#
# This configuration file defines how VaultTool handles file encryption.
# Save this as .vaulttool.yml in your project root directory.
#
# Configuration file search order:
#   1. ./.vaulttool.yml (current directory)
#   2. ~/.vaulttool/.vaulttool.yml (user home)
#   3. /etc/vaulttool/config.yml (system-wide)

vaulttool:
  # Directories to search for files to encrypt
  # Defaults to current directory if empty
  include_directories: 
    - "."

  # Directories to exclude from encryption
  exclude_directories:
    - "__pycache__"
    - ".git"
    - ".pytest_cache"
    - ".venv"
    - "dist"
    - "node_modules"

  # File patterns to include for encryption
  include_patterns:
    - "*.conf"          # Config files
    - "*.env"           # Environment files
    - "*.ini"           # Configuration files
    - "*.json"          # JSON config files
    - "*.yaml"          # YAML config files
    - "*.yml"           # YAML config files

  # File patterns to exclude from encryption
  exclude_patterns:
    - "*.log"           # Log files
    - "*.tmp"           # Temporary files
    - "*.vault"         # Existing vault files
    - "*example*"       # Example files
    - "*sample*"        # Sample files

  # Encryption options
  options:
    # Suffix added to encrypted files (e.g., config.env -> config.env.vault)
    suffix: ".vault"
    
    # Full Path to encryption key file
    key_file: "/home/USERNAME/.vaulttool/vault.key"
"""
    typer.echo(example_config.strip())


@app.command()
def remove(
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Remove all vault files matching the configured suffix.
    
    This command will permanently delete all .vault files found in the configured
    include directories that match the suffix pattern. This operation cannot be undone.
    
    Args:
        verbose: Enable verbose debug logging
        quiet: Show only errors
        
    Raises:
        Exit code 1 if any operations failed.
    """
    _setup_cli_logging(verbose, quiet)
    
    try:
        vt = VaultTool()
        result = vt.remove_task()
        
        # Display summary
        if not quiet:
            typer.echo("\n" + "="*60)
            typer.echo("Remove Summary:")
            typer.echo(f"  Total:   {result['total']}")
            typer.echo(f"  Removed: {result['removed']}")
            typer.echo(f"  Failed:  {result['failed']}")
            typer.echo("="*60)
        
        if result['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@app.command()
def encrypt(
    force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files"),
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Encrypt files as configured.
    
    Encrypts all source files matching the configured patterns into vault files.
    By default, only encrypts files that have changed (different HMAC) or 
    don't have existing vault files.
    
    Args:
        force: If True, re-encrypt and overwrite existing .vault files even if 
               the source file hasn't changed.
        verbose: Enable verbose debug logging
        quiet: Show only errors
               
    Raises:
        Exit code 1 if any operations failed.
    """
    _setup_cli_logging(verbose, quiet)
    
    try:
        vt = VaultTool()
        result = vt.encrypt_task(force=force)
        
        # Display summary
        if not quiet:
            typer.echo("\n" + "="*60)
            typer.echo("Encrypt Summary:")
            typer.echo(f"  Total:    {result['total']}")
            typer.echo(f"  Created:  {result['created']}")
            typer.echo(f"  Updated:  {result['updated']}")
            typer.echo(f"  Skipped:  {result['skipped']}")
            typer.echo(f"  Failed:   {result['failed']}")
            typer.echo("="*60)
        
        if result['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@app.command()
def refresh(
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Overwrite plaintext files from existing .vault files",
    ),
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Restore/refresh plaintext files from .vault files.
    
    Decrypts vault files to restore their corresponding source files. 
    By default, overwrites existing source files (force=True).
    
    Args:
        force: If True (default), overwrite existing plaintext files.
               If False, only restore missing files.
        verbose: Enable verbose debug logging
        quiet: Show only errors
               
    Raises:
        Exit code 1 if any operations failed.
    """
    _setup_cli_logging(verbose, quiet)
    
    try:
        vt = VaultTool()
        result = vt.refresh_task(force=force)
        
        # Display summary
        if not quiet:
            typer.echo("\n" + "="*60)
            typer.echo("Refresh Summary:")
            typer.echo(f"  Total:     {result['total']}")
            typer.echo(f"  Succeeded: {result['succeeded']}")
            typer.echo(f"  Failed:    {result['failed']}")
            typer.echo(f"  Skipped:   {result['skipped']}")
            typer.echo("="*60)
        
        if result['failed'] > 0:
            sys.exit(1)
            
    except Exception as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@app.command()
def check_ignore(
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Check that all plaintext files are ignored by Git.
    
    Validates that all source files matching the configured patterns are
    properly added to .gitignore to prevent accidental commits of sensitive data.
    
    Args:
        verbose: Enable verbose debug logging
        quiet: Show only errors
        
    Returns:
        Exit code 0 if operation completed.
    """
    _setup_cli_logging(verbose, quiet)
    
    try:
        vt = VaultTool()
        vt.check_ignore_task()
    except Exception as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
