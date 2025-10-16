"""Tests for key file validation.

These tests verify that derive_keys() properly validates key files
according to security best practices.
"""

import pytest
from vaulttool.utils import derive_keys


def test_missing_key_file(tmp_path):
    """Test that derive_keys rejects missing key file."""
    key_file = tmp_path / "nonexistent.key"
    
    with pytest.raises(FileNotFoundError, match="Key file not found"):
        derive_keys(str(key_file))


def test_empty_key_file(tmp_path):
    """Test that derive_keys rejects empty key file."""
    key_file = tmp_path / "empty.key"
    key_file.write_bytes(b"")
    
    with pytest.raises(ValueError, match="Key file is empty"):
        derive_keys(str(key_file))


def test_key_file_too_small(tmp_path):
    """Test that derive_keys rejects key files smaller than 16 bytes."""
    key_file = tmp_path / "small.key"
    key_file.write_bytes(b"tooshort")  # Only 8 bytes
    
    with pytest.raises(ValueError, match="Key file too small.*minimum 16 bytes"):
        derive_keys(str(key_file))


def test_key_file_minimum_size_accepted(tmp_path):
    """Test that derive_keys accepts key file with exactly 16 bytes."""
    key_file = tmp_path / "minimum.key"
    key_file.write_bytes(b"x" * 16)  # Exactly 16 bytes
    
    # Should not raise
    hmac_key, enc_key = derive_keys(str(key_file))
    assert len(hmac_key) == 32
    assert len(enc_key) == 32


def test_key_file_too_large(tmp_path):
    """Test that derive_keys rejects key files larger than 1MB."""
    key_file = tmp_path / "huge.key"
    # Create 1MB + 1 byte file
    key_file.write_bytes(b"x" * (1024 * 1024 + 1))
    
    with pytest.raises(ValueError, match="Key file too large.*maximum 1MB"):
        derive_keys(str(key_file))


def test_key_file_whitespace_only(tmp_path):
    """Test that derive_keys rejects key file with only whitespace."""
    key_file = tmp_path / "whitespace.key"
    # Need enough whitespace to pass 16-byte minimum
    key_file.write_bytes(b"   \n\t\r\n   " * 3)  # More than 16 bytes
    
    with pytest.raises(ValueError, match="contains only whitespace"):
        derive_keys(str(key_file))


def test_key_material_too_short_after_stripping(tmp_path):
    """Test that derive_keys rejects key with insufficient content after stripping."""
    key_file = tmp_path / "padded.key"
    # 10 bytes of content + enough whitespace to pass file size check
    key_file.write_bytes(b"   short   \n" + b" " * 10)  # Total > 16 bytes
    
    with pytest.raises(ValueError, match="Key material too short after stripping"):
        derive_keys(str(key_file))


def test_directory_as_key_file(tmp_path):
    """Test that derive_keys rejects directory path."""
    key_dir = tmp_path / "keydir"
    key_dir.mkdir()
    
    with pytest.raises(ValueError, match="not a regular file"):
        derive_keys(str(key_dir))


def test_valid_key_file_with_whitespace(tmp_path):
    """Test that derive_keys accepts valid key with leading/trailing whitespace."""
    key_file = tmp_path / "padded_valid.key"
    # 32 bytes of valid content with whitespace
    key_file.write_bytes(b"  " + b"x" * 32 + b"  \n")
    
    # Should succeed
    hmac_key, enc_key = derive_keys(str(key_file))
    assert len(hmac_key) == 32
    assert len(enc_key) == 32
    assert hmac_key != enc_key  # Keys should be different


def test_key_separation(tmp_path):
    """Test that HMAC key and encryption key are different."""
    key_file = tmp_path / "test.key"
    key_file.write_bytes(b"my-secure-key-material-for-testing")
    
    hmac_key, enc_key = derive_keys(str(key_file))
    
    # Keys must be different (cryptographic separation)
    assert hmac_key != enc_key
    assert len(hmac_key) == 32
    assert len(enc_key) == 32


def test_deterministic_key_derivation(tmp_path):
    """Test that same key file produces same derived keys."""
    key_file = tmp_path / "deterministic.key"
    key_file.write_bytes(b"consistent-key-material")
    
    hmac_key1, enc_key1 = derive_keys(str(key_file))
    hmac_key2, enc_key2 = derive_keys(str(key_file))
    
    # Same input should produce same output
    assert hmac_key1 == hmac_key2
    assert enc_key1 == enc_key2


def test_different_keys_produce_different_derivations(tmp_path):
    """Test that different key files produce different derived keys."""
    key_file1 = tmp_path / "key1.key"
    key_file2 = tmp_path / "key2.key"
    
    key_file1.write_bytes(b"first-key-material-here")
    key_file2.write_bytes(b"different-key-material")
    
    hmac_key1, enc_key1 = derive_keys(str(key_file1))
    hmac_key2, enc_key2 = derive_keys(str(key_file2))
    
    # Different keys should produce different derivations
    assert hmac_key1 != hmac_key2
    assert enc_key1 != enc_key2
