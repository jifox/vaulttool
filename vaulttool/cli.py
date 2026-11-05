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
- generate-key: Generate encryption key with backup and rekey options
"""

import logging
import os
import sys
import secrets
from pathlib import Path
from datetime import datetime
import typer
from . import setup_logging, __version__
from .core import VaultTool

# Create app with proper help text
# Note: Using triple-quoted string with \b to preserve formatting
app = typer.Typer(
    help="""Secure file encryption for secrets and configuration files.

Encrypts sensitive files using AES-256-GCM and manages their encrypted counterparts.

\b
Key Options:
  encrypt --force      Re-encrypt all files (ignores checksums)
  refresh --no-force   Only restore missing files
  generate-key         Create new encryption key with backup

\b
Config: .vaulttool.yml (current dir) or ~/.vaulttool/.vaulttool.yml

\b
Examples:
  vaulttool gen-vaulttool > .vaulttool.yml    # Generate config file
  vaulttool generate-key                      # Create encryption key
  vaulttool encrypt                           # Encrypt changed files only
  vaulttool refresh                           # Restore all source files
  vaulttool remove                            # Delete all vault files
\b
  vaulttool generate-key --rekey              # Replace key and re-encrypt all vaults
  vaulttool --verbose encrypt                 # Show detailed debug logs
  vaulttool --quiet refresh                   # Show errors only
""",
    pretty_exceptions_enable=False,
)

# Global options for logging control
@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Show only errors"),
) -> None:
    """Secure file encryption for secrets and configuration files."""
    ctx.obj = {"verbose": verbose, "quiet": quiet}


def _verbosity(ctx: typer.Context, verbose: bool, quiet: bool) -> tuple[bool, bool]:
    """Merge the root options (``vaulttool -v cmd``) with command options.

    Both spellings are supported: ``vaulttool --verbose encrypt`` and
    ``vaulttool encrypt --verbose``.

    Args:
        ctx: Typer context carrying the root options.
        verbose: Command-level ``--verbose`` value.
        quiet: Command-level ``--quiet`` value.

    Returns:
        Tuple of (verbose, quiet).
    """
    root = ctx.obj or {}
    return verbose or bool(root.get("verbose")), quiet or bool(root.get("quiet"))


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


def _write_private_file(path: Path, content: str, exclusive: bool = False) -> None:
    """Write a file that is only readable by its owner (mode 0600).

    The permissions are applied with ``os.open`` at creation time, so the file
    is never world-readable, not even briefly (``write_text`` + ``chmod`` leaves
    such a window open).

    Args:
        path: Destination path.
        content: Text to write.
        exclusive: If True, fail instead of overwriting an existing file.
    """
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


class Ui:
    """Console helper that centralises CLI output and ``--quiet`` handling.

    Each command builds one instance from its ``--quiet`` flag, so the
    ``if not quiet:`` boilerplate lives in a single place.
    """

    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet

    def say(self, message: str = "", err: bool = False) -> None:
        """Print an informational message unless --quiet was requested."""
        if not self.quiet:
            typer.echo(message, err=err)

    def error(self, message: str) -> None:
        """Print an error message; errors are never suppressed."""
        typer.echo(message, err=True)

    def heading(self, title: str) -> None:
        """Print a ``====`` banner around ``title``."""
        self.say("\n" + "=" * 60)
        self.say(title)
        self.say("=" * 60)

    def summary(self, title: str, rows) -> None:
        """Print an aligned label/value summary block.

        Args:
            title: Heading shown above the rows.
            rows: Iterable of ``(label, value)`` pairs.
        """
        rows = list(rows)
        self.heading(title)
        if not rows:
            return
        width = max(len(str(label)) for label, _ in rows)
        for label, value in rows:
            self.say(f"  {str(label) + ':':<{width + 1}} {value}")


def _get_version() -> str:
    """Return the installed VaultTool version.

    The version is resolved once, at import time, from the installed package
    metadata (see :mod:`vaulttool`), so ``pyproject.toml`` never has to be
    parsed at runtime.
    """
    return __version__


@app.command("generate-key")
def generate_key_cmd(
    ctx: typer.Context,
    key_file: str = typer.Option(
        None,
        "--key-file",
        "-k",
        help="Path to key file (default: from .vaulttool.yml config)",
    ),
    rekey: bool = typer.Option(
        False,
        "--rekey",
        help="Rekey all vault files with the new key",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip confirmation prompts (use with caution)",
    ),
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Generate a new encryption key with backup and rekey options.

\b
This command helps you manage encryption keys safely:
  1. If key file doesn't exist: Creates a new key
  2. If key file exists: Offers to backup and replace with new key
  3. If --rekey specified: Re-encrypts all vaults with the new key

\b
The rekey process:
  1. Restores plaintext files from existing vaults
  2. Removes old vault files
  3. Backs up the old key
  4. Writes the new key
  5. Encrypts files with the new key

\b
Examples:
  vaulttool generate-key                              # Generate new key
  vaulttool generate-key --rekey                      # Generate and rekey
  vaulttool generate-key --key-file ~/.vault/key      # Custom location
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    logger = _setup_cli_logging(verbose, quiet)
    ui = Ui(quiet)

    try:
        # Determine key file path
        if key_file is None:
            # Try to load from config
            try:
                from .config import load_config
                config = load_config()
                options = config.get("options", {})
                key_file = options.get("key_file")

                if not key_file:
                    typer.echo(
                        "ERROR: No key_file specified in config or via --key-file option.",
                        err=True
                    )
                    sys.exit(1)

                ui.say(f"Using key file from config: {key_file}")
            except Exception as e:
                typer.echo(
                    f"ERROR: Cannot load configuration. "
                    f"Please specify --key-file or create .vaulttool.yml config.\n"
                    f"Details: {e}",
                    err=True
                )
                sys.exit(1)

        key_path = Path(key_file).expanduser().resolve()
        key_exists = key_path.exists()

        # Generate new key
        new_key = secrets.token_hex(32)  # 64 hex chars = 32 bytes

        if not key_exists:
            # Create new key file
            ui.say(f"\nKey file does not exist: {key_path}")
            ui.say("Creating new key file...")

            # Ensure parent directory exists
            key_path.parent.mkdir(parents=True, exist_ok=True)

            # Create the key with 0600 permissions from the start
            _write_private_file(key_path, new_key + "\n", exclusive=True)

            ui.say(f"✅ Successfully created new key file: {key_path}")
            ui.say("   Permissions: 600 (owner read/write only)")
            ui.say("\n⚠️  IMPORTANT: Back up this key file securely!")
            ui.say("   Without this key, you cannot decrypt your vault files.")

            return

        # Key file exists - offer backup and replace
        ui.say(f"\n⚠️  Key file already exists: {key_path}")
        ui.say("\nOptions:")
        ui.say("  1. Backup old key and replace with new key")
        if rekey:
            ui.say("  2. Re-encrypt all vault files with new key (--rekey enabled)")
        ui.say("  3. Cancel operation")

        if not force:
            if rekey:
                typer.echo("\n⚠️  WARNING: Rekey operation will:")
                typer.echo("     - Decrypt all vault files to plaintext")
                typer.echo("     - Remove all old vault files")
                typer.echo("     - Backup the old key")
                typer.echo("     - Replace with new key")
                typer.echo("     - Re-encrypt all files with new key")
                typer.echo("\n   This is a DESTRUCTIVE operation!")

            try:
                response = typer.confirm(
                    "\nDo you want to proceed with replacing the key?",
                    default=False
                )
            except (KeyboardInterrupt, typer.Abort):
                typer.echo("\nOperation cancelled.")
                return

            if not response:
                typer.echo("Operation cancelled.")
                return

        # Perform rekey if requested
        if rekey:
            ui.say("\n" + "="*60)
            ui.say("Starting rekey process...")
            ui.say("="*60)

            # Step 1: Restore plaintext files from vaults
            ui.say("\n[1/5] Restoring plaintext files from vaults...")

            try:
                vt = VaultTool()
                refresh_result = vt.refresh_task(force=True)

                ui.say(f"   ✅ Restored: {refresh_result['succeeded']} files")
                if refresh_result['failed'] > 0:
                    ui.say(f"   ❌ Failed: {refresh_result['failed']} files", err=True)

                if refresh_result['failed'] > 0:
                    typer.echo("\nERROR: Failed to restore some files. Aborting rekey.", err=True)
                    sys.exit(1)

            except Exception as e:
                typer.echo(f"\nERROR during refresh: {e}", err=True)
                sys.exit(1)

            # Step 2: Remove old vault files
            ui.say("\n[2/5] Removing old vault files...")

            try:
                remove_result = vt.remove_task()

                ui.say(f"   ✅ Removed: {remove_result['removed']} vault files")
                if remove_result['failed'] > 0:
                    ui.say(f"   ❌ Failed: {remove_result['failed']} files", err=True)

            except Exception as e:
                typer.echo(f"\nERROR during remove: {e}", err=True)
                sys.exit(1)

            # Step 3 & 4: Backup old key and write new key
            ui.say("\n[3/5] Backing up old key...")

        # Backup existing key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = key_path.parent / f"{key_path.name}.backup_{timestamp}"

        try:
            # Read old key
            old_key = key_path.read_text()

            # Write backup (0600, never overwrite an existing backup)
            _write_private_file(backup_path, old_key, exclusive=True)

            ui.say(f"   ✅ Old key backed up to: {backup_path}")
        except Exception as e:
            typer.echo(f"\nERROR: Failed to backup old key: {e}", err=True)
            sys.exit(1)

        ui.say("\n[4/5] Writing new key...")

        # Write new key
        try:
            _write_private_file(key_path, new_key + "\n")

            ui.say(f"   ✅ New key written to: {key_path}")
        except Exception as e:
            typer.echo(f"\nERROR: Failed to write new key: {e}", err=True)
            typer.echo(f"   Old key backup is safe at: {backup_path}")
            sys.exit(1)

        # Step 5: Re-encrypt with new key
        if rekey:
            ui.say("\n[5/5] Re-encrypting files with new key...")

            try:
                # Reload VaultTool with new key
                vt = VaultTool()
                encrypt_result = vt.encrypt_task(force=True)

                ui.say(f"   ✅ Created: {encrypt_result['created']} vault files")
                ui.say(f"   ✅ Updated: {encrypt_result['updated']} vault files")
                if encrypt_result['failed'] > 0:
                    ui.say(f"   ❌ Failed: {encrypt_result['failed']} files", err=True)

                if encrypt_result['failed'] > 0:
                    typer.echo("\nWARNING: Some files failed to encrypt.", err=True)
                    sys.exit(1)

            except Exception as e:
                typer.echo(f"\nERROR during encryption: {e}", err=True)
                typer.echo(f"   Old key backup: {backup_path}")
                typer.echo("   You may need to restore the old key and try again.")
                sys.exit(1)

        # Success summary
        ui.say("\n" + "="*60)
        ui.say("✅ Key generation complete!")
        ui.say("="*60)
        ui.say(f"   New key: {key_path}")
        ui.say(f"   Backup:  {backup_path}")
        if rekey:
            ui.say("\n   Rekey summary:")
            ui.say(f"     - Restored {refresh_result['succeeded']} plaintext files")
            ui.say(f"     - Removed {remove_result['removed']} old vault files")
            ui.say(f"     - Created {encrypt_result['created'] + encrypt_result['updated']} new vault files")
        ui.say("\n⚠️  IMPORTANT:")
        ui.say("   1. Back up both keys securely")
        ui.say("   2. Test decryption before deleting backup")
        if rekey:
            ui.say("   3. Commit new vault files to version control")

    except KeyboardInterrupt:
        typer.echo("\n\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"\nERROR: {e}", err=True)
        logger.exception("Unexpected error during key generation")
        sys.exit(1)


@app.command("version")
def version_cmd(
    ctx: typer.Context,
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Display VaultTool version information.

\b
Shows the currently installed version of VaultTool.

\b
Example:
  vaulttool version
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    _setup_cli_logging(verbose, quiet)
    pkg_version = _get_version()
    typer.echo(f"VaultTool version {pkg_version}")


@app.command("gen-vaulttool")
def gen_config():
    """Generate an example .vaulttool.yml configuration file.

\b
Displays a formatted example configuration file that can be saved as
.vaulttool.yml to configure VaultTool for your project. The configuration
includes all available options with comments explaining their purpose.

\b
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
    ctx: typer.Context,
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Remove all vault files matching the configured suffix.

\b
This command will permanently delete all .vault files found in the configured
include directories that match the suffix pattern. This operation cannot be undone.

\b
Example:
  vaulttool remove
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    _setup_cli_logging(verbose, quiet)
    ui = Ui(quiet)

    try:
        vt = VaultTool()
        result = vt.remove_task()

        ui.summary("Remove Summary:", [
            ("Total", result["total"]),
            ("Removed", result["removed"]),
            ("Failed", result["failed"]),
        ])

        if result['failed'] > 0:
            sys.exit(1)

    except Exception as e:
        ui.error(f"ERROR: {e}")
        sys.exit(1)


@app.command()
def encrypt(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files"),
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Encrypt files as configured.

\b
Encrypts all source files matching the configured patterns into vault files.
By default, only encrypts files that have changed (different HMAC) or
don't have existing vault files.

\b
Options:
  --force        Re-encrypt all files, overwriting existing .vault files
  --verbose      Show detailed debug information
  --quiet        Show only errors

\b
Examples:
  vaulttool encrypt                # Encrypt changed files only
  vaulttool encrypt --force        # Re-encrypt all files
  vaulttool --verbose encrypt      # Show debug output
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    _setup_cli_logging(verbose, quiet)
    ui = Ui(quiet)

    try:
        vt = VaultTool()
        result = vt.encrypt_task(force=force)

        ui.summary("Encrypt Summary:", [
            ("Total", result["total"]),
            ("Created", result["created"]),
            ("Updated", result["updated"]),
            ("Skipped", result["skipped"]),
            ("Failed", result["failed"]),
        ])

        if result['failed'] > 0:
            sys.exit(1)

    except Exception as e:
        ui.error(f"ERROR: {e}")
        sys.exit(1)


@app.command()
def refresh(
    ctx: typer.Context,
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Overwrite plaintext files from existing .vault files",
    ),
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Restore/refresh plaintext files from .vault files.

\b
Decrypts vault files to restore their corresponding source files.
By default, overwrites existing source files (force=True).

\b
Options:
  --force        Overwrite existing plaintext files (default)
  --no-force     Only restore missing files
  --verbose      Show detailed debug information
  --quiet        Show only errors

\b
Examples:
  vaulttool refresh                # Restore all files (overwrite)
  vaulttool refresh --no-force     # Restore only missing files
  vaulttool --verbose refresh      # Show debug output
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    _setup_cli_logging(verbose, quiet)
    ui = Ui(quiet)

    try:
        vt = VaultTool()
        result = vt.refresh_task(force=force)

        ui.summary("Refresh Summary:", [
            ("Total", result["total"]),
            ("Succeeded", result["succeeded"]),
            ("Failed", result["failed"]),
            ("Skipped", result["skipped"]),
        ])

        if result['failed'] > 0:
            sys.exit(1)

    except Exception as e:
        ui.error(f"ERROR: {e}")
        sys.exit(1)


@app.command()
def check_ignore(
    ctx: typer.Context,
    verbose: bool = verbose_option,
    quiet: bool = quiet_option,
):
    """Check that all plaintext files are ignored by Git.

\b
Validates that all source files matching the configured patterns are
properly added to .gitignore to prevent accidental commits of sensitive data.

\b
Example:
  vaulttool check-ignore
    """
    verbose, quiet = _verbosity(ctx, verbose, quiet)
    _setup_cli_logging(verbose, quiet)
    ui = Ui(quiet)

    try:
        vt = VaultTool()
        result = vt.check_ignore_task()

        ui.say("\n" + "=" * 60)
        ui.say("Check Ignore Summary:")
        ui.say(f"  Total:       {result['total']}")
        ui.say(f"  Ignored:     {result['ignored']}")
        ui.say(f"  Not ignored: {len(result['not_ignored'])}")
        ui.say("=" * 60)
        for not_ignored in result["not_ignored"]:
            ui.say(f"  \u26a0  {not_ignored}", err=True)

        if result["not_ignored"]:
            sys.exit(1)
    except Exception as e:
        ui.error(f"ERROR: {e}")
        sys.exit(1)
