import tempfile
import os
from pathlib import Path
from vaulttool.core import VaultTool

def test_decrypt_missing_sources_restores_file():
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
        # Write config YAML
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
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        # Create VaultTool instance and encrypt file to create .vault
        vt = VaultTool()
        vt.encrypt_task()
        
        vault_path = plain_path.with_suffix(plain_path.suffix + ".vault")
        assert vault_path.exists()
        # Remove the source file
        plain_path.unlink()
        assert not plain_path.exists()
        # Run decrypt_missing_sources
        vt.refresh_task()
        # Source file should be restored
        assert plain_path.exists()
        with open(plain_path) as pf:
            assert pf.read() == "SECRET=12345"
