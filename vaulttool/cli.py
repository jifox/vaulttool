
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

import typer
from .core import VaultTool

app = typer.Typer(
    help="""Secure file encryption for secrets and configuration files.

Encrypts sensitive files using OpenSSL and manages their encrypted counterparts.

Key Options:
  encrypt --force      Re-encrypt all files (ignores checksums)
  refresh --no-force   Only restore missing files
  
Config: .vaulttool.yml (current dir) or ~/.vaulttool/.vaulttool.yml

Examples:
  vaulttool gen-vaulttool > .vaulttool.yml    # Generate config file
  vaulttool encrypt          # Encrypt changed files only
  vaulttool refresh          # Restore all source files  
  vaulttool remove           # Delete all vault files
"""
)


def _get_version() -> str:
    """Get the version of vaulttool package."""
    try:
        from importlib.metadata import version
        return version("vaulttool")
    except ImportError:
        # importlib.metadata not available in older Python versions
        pass
    except Exception:
        # Package not found or other error
        pass
    
    # Fallback - try to read from pyproject.toml if available
    try:
        from pathlib import Path
        
        # Look for pyproject.toml in parent directories
        current_dir = Path(__file__).parent
        for _ in range(3):  # Check up to 3 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    # Simple parsing for version
                    for line in content.split('\n'):
                        if line.strip().startswith('version = "'):
                            return line.split('"')[1]
            current_dir = current_dir.parent
    except Exception:
        pass
    
    return "unknown (development version)"


@app.command("version")
def version_cmd():
    """Display VaultTool version information.
    
    Shows the currently installed version of VaultTool along with
    basic package information.
    """
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
    - ".git"
    - ".venv"
    - "__pycache__"
    - "node_modules"
    - ".pytest_cache"

  # File patterns to include for encryption
  include_patterns:
    - "*.env"           # Environment files
    - "*.ini"           # Configuration files
    - "*.conf"          # Config files
    - "*.json"          # JSON config files
    - "*.yaml"          # YAML config files
    - "*.yml"           # YAML config files

  # File patterns to exclude from encryption
  exclude_patterns:
    - "*.log"           # Log files
    - "*.tmp"           # Temporary files
    - "*example*"       # Example files
    - "*sample*"        # Sample files
    - "*.vault"         # Existing vault files

  # Encryption options
  options:
    # Suffix added to encrypted files (e.g., config.env -> config.env.vault)
    suffix: ".vault"
    
    # OpenSSL encryption algorithm
    algorithm: "aes-256-cbc"
    
    # Path to encryption key file
    key_file: "~/.vaulttool/vault.key"
    
    # Path to openssl binary (leave as 'openssl' if in PATH)
    openssl_path: "openssl"
"""
    typer.echo(example_config.strip())


@app.command()
def remove():
    """Remove all vault files matching the configured suffix.
    
    This command will permanently delete all .vault files found in the configured
    include directories that match the suffix pattern. This operation cannot be undone.
    
    Raises:
        VaultToolError: If configuration is invalid or operation fails.
    """
    vt = VaultTool()
    vt.remove_task()


@app.command()
def encrypt(force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files. Use --force to unconditionally overwrite files.")):
    """Encrypt files as configured.
    
    Encrypts all source files matching the configured patterns into vault files.
    By default, only encrypts files that have changed (different checksum) or 
    don't have existing vault files.
    
    Args:
        force: If True, re-encrypt and overwrite existing .vault files even if 
               the source file hasn't changed.
               
    Raises:
        VaultToolError: If configuration is invalid or encryption fails.
    """
    vt = VaultTool()
    vt.encrypt_task(force=force)

@app.command()
def refresh(
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Overwrite plaintext files from existing .vault files.",
    ),
):
    """Restore/refresh plaintext files from .vault files.
    
    Decrypts vault files to restore their corresponding source files. 
    By default, overwrites existing source files (force=True).
    
    Args:
        force: If True (default), overwrite existing plaintext files.
               If False, only restore missing files.
               
    Raises:
        VaultToolError: If configuration is invalid or decryption fails.
    """
    vt = VaultTool()
    vt.refresh_task(force=force)

@app.command()
def check_ignore():
    """Check that all plaintext files are ignored by Git.
    
    Validates that all source files matching the configured patterns are
    properly added to .gitignore to prevent accidental commits of sensitive data.
    
    Returns:
        Exit code 0 if all files are ignored, non-zero otherwise.
        
    Raises:
        VaultToolError: If configuration is invalid.
    """
    vt = VaultTool()
    vt.check_ignore_task()
