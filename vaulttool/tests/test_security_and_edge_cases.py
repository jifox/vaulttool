"""Additional security and edge case tests for VaultTool v2.0."""

import tempfile
import os
from pathlib import Path
from vaulttool.core import VaultTool
from vaulttool.utils import derive_keys, compute_hmac
import base64


def test_iv_uniqueness():
    """Test that each encryption generates a unique IV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create source file
        source_path = os.path.join(tmpdir, "test.txt")
        with open(source_path, "w") as f:
            f.write("Same content for both encryptions")
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.txt']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        
        # First encryption
        vt.encrypt_task(force=True)
        vault_path = source_path + ".vault"
        with open(vault_path, "r") as f:
            lines1 = f.readlines()
            encrypted1 = lines1[1].strip()
        
        # Second encryption (force)
        vt.encrypt_task(force=True)
        with open(vault_path, "r") as f:
            lines2 = f.readlines()
            encrypted2 = lines2[1].strip()
        
        # Encrypted content should be different (different IV)
        assert encrypted1 != encrypted2, "IVs should be random, making ciphertext different"
        
        # But HMAC should be the same (same plaintext)
        assert lines1[0] == lines2[0], "HMAC should be the same for same plaintext"


def test_binary_file_encryption():
    """Test encryption of binary files (non-text)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create binary file with various byte values
        binary_path = os.path.join(tmpdir, "test.bin")
        binary_content = bytes(range(256)) + b"\x00\x01\xff\xfe" * 100
        with open(binary_path, "wb") as f:
            f.write(binary_content)
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.bin']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_task()
        
        # Remove original and decrypt
        os.remove(binary_path)
        vt.refresh_task()
        
        # Verify binary content is restored correctly
        with open(binary_path, "rb") as f:
            restored_content = f.read()
        
        assert restored_content == binary_content, "Binary content should be preserved exactly"


def test_empty_file_encryption():
    """Test encryption of empty files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create empty file
        empty_path = os.path.join(tmpdir, "empty.txt")
        Path(empty_path).touch()
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.txt']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_task()
        
        vault_path = empty_path + ".vault"
        assert os.path.exists(vault_path), "Vault file should be created for empty file"
        
        # Remove original and decrypt
        os.remove(empty_path)
        vt.refresh_task()
        
        # Verify empty file is restored
        assert os.path.exists(empty_path)
        assert os.path.getsize(empty_path) == 0, "Restored file should be empty"


def test_large_file_encryption():
    """Test encryption of larger files (1MB)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create 1MB file
        large_path = os.path.join(tmpdir, "large.bin")
        large_content = b"A" * (1024 * 1024)  # 1MB of 'A'
        with open(large_path, "wb") as f:
            f.write(large_content)
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.bin']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_task()
        
        # Remove original and decrypt
        os.remove(large_path)
        vt.refresh_task()
        
        # Verify content is restored correctly
        with open(large_path, "rb") as f:
            restored_content = f.read()
        
        assert restored_content == large_content, "Large file content should be preserved"
        assert len(restored_content) == 1024 * 1024


def test_corrupted_vault_file_short():
    """Test handling of corrupted vault file (too short)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create corrupted vault file (too short - missing IV)
        vault_path = os.path.join(tmpdir, "corrupted.env.vault")
        with open(vault_path, "w") as f:
            f.write("a" * 64 + "\n")  # HMAC only, no encrypted content
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        
        # Should handle gracefully (skip the file)
        # The refresh_task checks for len(lines) < 2
        vt.refresh_task()
        
        source_path = os.path.join(tmpdir, "corrupted.env")
        assert not os.path.exists(source_path), "Corrupted file should not be decrypted"


def test_corrupted_vault_file_invalid_iv():
    """Test handling of vault file with encrypted data shorter than IV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create vault file with data shorter than IV (16 bytes)
        vault_path = os.path.join(tmpdir, "short.env.vault")
        short_data = b"tooshort"  # Less than 16 bytes
        with open(vault_path, "w") as f:
            f.write("a" * 64 + "\n")  # HMAC
            f.write(base64.b64encode(short_data).decode() + "\n")
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        
        # refresh_task should handle this gracefully (prints error, doesn't raise)
        # The corrupted file should be skipped
        vt.refresh_task()
        
        # Source file should NOT be created due to decryption error
        source_file = os.path.join(tmpdir, "short.env")
        assert not os.path.exists(source_file)


def test_tampered_ciphertext_detection():
    """Test that tampering with ciphertext is detected during decryption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create and encrypt a file
        source_path = os.path.join(tmpdir, "test.env")
        with open(source_path, "w") as f:
            f.write("SECRET=value")
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_task()
        
        vault_path = source_path + ".vault"
        
        # Tamper with the ciphertext
        with open(vault_path, "r") as f:
            lines = f.readlines()
        
        # Decode, tamper, re-encode
        encrypted_data = base64.b64decode(lines[1].strip())
        tampered = bytearray(encrypted_data)
        tampered[-1] ^= 0xFF  # Flip bits in last byte
        
        with open(vault_path, "w") as f:
            f.write(lines[0])  # Keep original HMAC
            f.write(base64.b64encode(bytes(tampered)).decode() + "\n")
        
        # Remove source and try to decrypt
        os.remove(source_path)
        
        # refresh_task should handle errors gracefully (no exception raised)
        # The tampered file should either:
        # 1. Fail decryption (padding error), or
        # 2. Decrypt to garbage and fail HMAC verification
        # Either way, source file should NOT be created/restored
        vt.refresh_task()
        
        # Verify source was NOT restored due to tampering
        assert not os.path.exists(source_path)


def test_hmac_change_detection():
    """Test that file changes are detected via HMAC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create source file
        source_path = os.path.join(tmpdir, "test.env")
        with open(source_path, "w") as f:
            f.write("SECRET=value1")
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        
        # First encryption
        vt.encrypt_task()
        vault_path = source_path + ".vault"
        
        with open(vault_path, "r") as f:
            hmac1 = f.readline().strip()
        
        # Modify source file
        with open(source_path, "w") as f:
            f.write("SECRET=value2")
        
        # Encrypt again (should update due to HMAC mismatch)
        vt.encrypt_task()
        
        with open(vault_path, "r") as f:
            hmac2 = f.readline().strip()
        
        # HMACs should be different
        assert hmac1 != hmac2, "HMAC should change when file content changes"


def test_special_characters_in_content():
    """Test encryption of files with special characters and Unicode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create file with special characters (using binary mode to preserve exact bytes)
        source_path = os.path.join(tmpdir, "special.txt")
        special_content = b"Hello \xe4\xb8\x96\xe7\x95\x8c! \xf0\x9f\x94\x90\nLine2: \xc3\xa0\xc3\xa9\xc3\xae\xc3\xb6\xc3\xbc\nLine3: Tab\tNull\x00End"
        with open(source_path, "wb") as f:
            f.write(special_content)
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.txt']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_task()
        
        # Remove and decrypt
        os.remove(source_path)
        vt.refresh_task()
        
        # Verify binary content is preserved exactly
        with open(source_path, "rb") as f:
            restored = f.read()
        
        assert restored == special_content, "Special characters should be preserved exactly"


def test_key_separation_verification():
    """Verify that HMAC key and encryption key are truly different."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_master_key_123456789")
        
        hmac_key, enc_key = derive_keys(key_path)
        
        # Keys must be different
        assert hmac_key != enc_key, "HMAC and encryption keys must be different"
        
        # Keys must be full 32 bytes
        assert len(hmac_key) == 32
        assert len(enc_key) == 32
        
        # Keys should have good distribution (not all zeros, etc.)
        assert hmac_key.count(b'\x00') < 16, "HMAC key should have entropy"
        assert enc_key.count(b'\x00') < 16, "Encryption key should have entropy"
        
        # Derive again with same key - should be deterministic
        hmac_key2, enc_key2 = derive_keys(key_path)
        assert hmac_key == hmac_key2, "HKDF should be deterministic"
        assert enc_key == enc_key2, "HKDF should be deterministic"


def test_hmac_verification_with_different_files():
    """Test that HMAC is specific to file content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        hmac_key, _ = derive_keys(key_path)
        
        # Create two different files
        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")
        
        with open(file1, "w") as f:
            f.write("content1")
        with open(file2, "w") as f:
            f.write("content2")
        
        hmac1 = compute_hmac(file1, hmac_key)
        hmac2 = compute_hmac(file2, hmac_key)
        
        # HMACs should be different for different content
        assert hmac1 != hmac2, "Different files should have different HMACs"
        
        # Create file with same content as file1
        file3 = os.path.join(tmpdir, "file3.txt")
        with open(file3, "w") as f:
            f.write("content1")
        
        hmac3 = compute_hmac(file3, hmac_key)
        
        # Same content should give same HMAC
        assert hmac1 == hmac3, "Same content should give same HMAC"
