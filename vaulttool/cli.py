import typer
from .config import load_config
from .core import encrypt_files, decrypt_missing_sources, check_unencrypted_files_ignored

app = typer.Typer()


@app.command()
def encrypt(force: bool = typer.Option(False, "--force", help="Re-encrypt and overwrite existing .vault files.")):
    """Encrypt files as configured. Use --force to re-encrypt even if unchanged."""
    config = load_config()
    encrypt_files(config, force=force)


@app.command()
def refresh(
    force: bool = typer.Option(
        True,
        "--force/--no-force",
        help="Overwrite plaintext files from existing .vault files.",
    ),
):
    """Restore/refresh plaintext files from .vault files (defaults to overwrite)."""
    config = load_config()
    decrypt_missing_sources(config, force=force)


@app.command()
def check_ignore():
    """Check that all plaintext files are ignored by Git; exit nonzero if any are not."""
    config = load_config()
    missing = check_unencrypted_files_ignored(config)
    if missing:
        typer.echo("The following plaintext files are not ignored by Git:")
        for m in missing:
            typer.echo(f" - {m}")
        raise typer.Exit(code=1)
    typer.echo("All plaintext files are ignored by Git.")
