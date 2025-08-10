import os
import tempfile
from vaulttool.crypto import encrypt_file

def test_encrypt_file_creates_encrypted_file():
    # Create a temporary plaintext file
    with tempfile.TemporaryDirectory() as tmpdir:
        plaintext_path = os.path.join(tmpdir, "test.txt")
        encrypted_path = os.path.join(tmpdir, "test.txt.enc")
        key_path = os.path.join(tmpdir, "keyfile")
        # Write a key and plaintext
        with open(key_path, "w") as kf:
            kf.write("mysecretpassword")
        with open(plaintext_path, "w") as pf:
            pf.write("hello world")
        # Encrypt using OpenSSL
        encrypt_file(
            input_path=plaintext_path,
            output_path=encrypted_path,
            key_file=key_path,
            algorithm="aes-256-cbc",
            openssl_path="openssl"
        )
        # Check that encrypted file exists and is not empty
        assert os.path.exists(encrypted_path)
        assert os.path.getsize(encrypted_path) > 0
        # Optionally, decrypt and check content
        decrypted_path = os.path.join(tmpdir, "decrypted.txt")
        os.system(f"openssl enc -d -aes-256-cbc -in {encrypted_path} -out {decrypted_path} -pass file:{key_path}")
        with open(decrypted_path) as df:
            assert df.read() == "hello world"
