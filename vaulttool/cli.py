
"""Command-line interface for VaultTool.

This module provides the command-line interface for VaultTool using Typer.
It exposes the main VaultTool functionality through a set of subcommands
for encrypting, decrypting, and managing vault files.

Available commands:
- encrypt: Encrypt source files to vault files
- refresh: Decrypt vault files to restore source files  
- remove: Delete all vault files
- check-ignore: Validate .gitignore entries for source files
"""

import typer
from .core import VaultTool

app = typer.Typer()


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
def encrypt(force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files.")):
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
