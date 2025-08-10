import tempfile
import os
from pathlib import Path
import sys
import importlib

def test_main_runs_encrypt_and_decrypt(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Create a plaintext file
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
        main_mod = importlib.import_module("vaulttool.__main__")
        main_mod.main()
        # Check .vault file created
        vault_path = plain_path.with_suffix(plain_path.suffix + ".vault")
        assert vault_path.exists()
        # Remove source file
        plain_path.unlink()
        assert not plain_path.exists()
        # Run main again to trigger decryption
        main_mod.main()
        # Source file should be restored
        assert plain_path.exists()
        with open(plain_path) as pf:
            assert pf.read() == "SECRET=12345"
