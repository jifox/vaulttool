import tempfile
import os
from pathlib import Path
from vaulttool.core import VaultTool

def test_source_added_to_gitignore():
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
        
        # Remove .gitignore if exists
        gitignore_path = Path(tmpdir) / ".gitignore"
        if gitignore_path.exists():
            gitignore_path.unlink()
        
        # Create VaultTool instance and encrypt
        vt = VaultTool()
        vt.encrypt_task()
        
        # Check .gitignore exists and contains the source file
        assert gitignore_path.exists()
        with open(gitignore_path) as gi:
            lines = [line.strip() for line in gi if line.strip()]
        rel_path = os.path.relpath(plain_path, Path(tmpdir).absolute())
        assert rel_path in lines
