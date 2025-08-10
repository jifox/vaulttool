import tempfile
import os
from vaulttool.core import encrypt_files

def test_encrypt_files_creates_vault_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a plaintext file
        plain_path = os.path.join(tmpdir, "secret.env")
        with open(plain_path, "w") as pf:
            pf.write("SECRET=12345")
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "w") as kf:
            kf.write("mysecretpassword")
        # Write config YAML
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
        encrypt_files(config)
        vault_path = plain_path + ".vault"
        assert os.path.exists(vault_path)
        assert os.path.getsize(vault_path) > 0
        # Read only the second line (base64 data) from .vault file
        import base64
        with open(vault_path, "r") as vf:
            lines = vf.readlines()
            assert len(lines) >= 2
            encrypted_b64 = lines[1].strip()
        encrypted = base64.b64decode(encrypted_b64)
        decrypted_path = os.path.join(tmpdir, "decrypted.env")
        with open(decrypted_path, "wb") as df:
            df.write(encrypted)
        os.system(f"openssl enc -d -aes-256-cbc -in {decrypted_path} -out {decrypted_path}.txt -pass file:{key_path}")
        with open(f"{decrypted_path}.txt") as final:
            assert final.read() == "SECRET=12345"
