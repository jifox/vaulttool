
import typer
from .core import VaultTool

app = typer.Typer()


@app.command()
def remove():
    """Remove all vault files matching the configured suffix."""
    vt = VaultTool()
    vt.remove_vault_files()


@app.command()
def encrypt(force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files.")):
    """Encrypt files as configured. Use --force to re-encrypt even if unchanged."""
    vt = VaultTool()
    vt.encrypt(force=force)

@app.command()
def refresh(
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Overwrite plaintext files from existing .vault files.",
    ),
):
    """Restore/refresh plaintext files from .vault files (defaults to overwrite). Use --no-force to skip existing files."""
    vt = VaultTool()
    vt.decrypt_missing_sources(force=force)

@app.command()
def check_ignore():
    """Check that all plaintext files are ignored by Git; exit nonzero if any are not."""
    vt = VaultTool()
    vt.validate_gitignore()
