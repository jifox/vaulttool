import tempfile
import os
import time
from vaulttool.core import VaultTool

def test_encrypt_only_on_checksum_change():
    original_dir = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            plain_path = os.path.join(tmpdir, "secret.env")
            key_path = os.path.join(tmpdir, "keyfile")
            
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
            
            # Write initial content and encrypt
            with open(plain_path, "w") as pf:
                pf.write("SECRET=12345")
            
            vt = VaultTool()
            vt.encrypt_task()
            
            vault_path = plain_path + ".vault"
            initial_mtime = os.path.getmtime(vault_path)
            # Run again without changing file, should not update .vault
            time.sleep(1)
            vt.encrypt_task()
            assert os.path.getmtime(vault_path) == initial_mtime
            # Change file content, should update .vault
            time.sleep(1)
            with open(plain_path, "w") as pf:
                pf.write("SECRET=67890")
            vt.encrypt_task()
            assert os.path.getmtime(vault_path) > initial_mtime
            
            # Change back to original directory before tmpdir is deleted
            os.chdir(original_dir)
    finally:
        # Ensure we're back in original directory even if test fails
        if os.path.exists(original_dir):
            os.chdir(original_dir)
