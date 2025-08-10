import tempfile
import os
import time
from vaulttool.core import encrypt_files

def test_encrypt_only_on_checksum_change():
    with tempfile.TemporaryDirectory() as tmpdir:
        plain_path = os.path.join(tmpdir, "secret.env")
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "w") as kf:
            kf.write("mysecretpassword")
        config = {
            "include_directories": [tmpdir],
            "exclude_directories": [],
            "include_patterns": ["*.env"],
            "exclude_patterns": [],
            "options": {
                "suffix": ".vault",
                "openssl_path": "openssl",
                "algorithm": "aes-256-cbc",
                "key_type": "file",
                "key_file": key_path
            }
        }
        # Write initial content and encrypt
        with open(plain_path, "w") as pf:
            pf.write("SECRET=12345")
        encrypt_files(config)
        vault_path = plain_path + ".vault"
        initial_mtime = os.path.getmtime(vault_path)
        # Run again without changing file, should not update .vault
        time.sleep(1)
        encrypt_files(config)
        assert os.path.getmtime(vault_path) == initial_mtime
        # Change file content, should update .vault
        time.sleep(1)
        with open(plain_path, "w") as pf:
            pf.write("SECRET=67890")
        encrypt_files(config)
        assert os.path.getmtime(vault_path) > initial_mtime
