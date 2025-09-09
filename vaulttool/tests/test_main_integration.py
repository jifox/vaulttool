import tempfile
from pathlib import Path
import sys
import os


def test_main_runs_encrypt_and_decrypt(monkeypatch):
    # Ensure cwd is valid before entering tempdir context
    os.chdir(os.path.dirname(__file__))
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.chdir(tmpdir)
        # All file operations must happen after chdir
        plain_path = Path(tmpdir) / "secret.env"
        with open(plain_path, "w") as pf:
            pf.write("SECRET=12345")
        # Create a key file
        key_path = Path(tmpdir) / "keyfile"
        with open(key_path, "w") as kf:
            kf.write("mysecretpassword")
        # Write config
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    openssl_path: "openssl"
    algorithm: "aes-256-cbc"
    key_type: "file"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        # Remove .gitignore if exists
        gitignore_path = Path(tmpdir) / ".gitignore"
        if gitignore_path.exists():
            gitignore_path.unlink()
        # Run main program
        sys.path.insert(0, str(Path(tmpdir).parent))
        from typer.testing import CliRunner
        from vaulttool.cli import app
        runner = CliRunner()
        monkeypatch.chdir(tmpdir)
        result = runner.invoke(app, ["encrypt"])
        assert result.exit_code == 0
        # Check .vault file created
        vault_path = plain_path.with_suffix(plain_path.suffix + ".vault")
        assert vault_path.exists()
        # Remove source file
        plain_path.unlink()
        assert not plain_path.exists()
        # Run CLI app to restore (decrypt)
        result = runner.invoke(app, ["refresh"])
        assert result.exit_code == 0
        # Source file should be restored
        assert plain_path.exists()
        with open(plain_path) as pf:
            assert pf.read() == "SECRET=12345"
