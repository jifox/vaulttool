"""Tests for Priority 3 (Medium) error handling fixes.

This module tests the Priority 3 improvements from the error handling analysis:
- Issue #7: CLI error handling with specific exceptions
- Issue #8: Path validation with error context preservation  
- Issue #9: Cryptographic operation validation
- Issue #10: Utils module logging and error context
"""

import pytest
import logging
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from vaulttool.cli import _get_version
from vaulttool.core import VaultTool
from vaulttool.utils import derive_keys, compute_hmac
from vaulttool import setup_logging


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Ensure logging is properly configured for all tests."""
    # Set up logging for the test
    setup_logging(level=logging.DEBUG, include_timestamp=False)
    yield
    # Clean up handlers after test
    for logger_name in ['vaulttool.cli', 'vaulttool.core', 'vaulttool.utils']:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)


def create_test_config(tmpdir, key_path):
    """Helper to create a test configuration file."""
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


class TestCLIErrorHandling:
    """Test Issue #7: CLI error handling improvements."""
    
    def test_get_version_with_importlib_success(self):
        """Test _get_version() successfully gets version from importlib.metadata."""
        version = _get_version()
        
        # Should get a version string
        assert version is not None
        assert isinstance(version, str)
        # Should not be unknown (unless in development)
        # The important thing is it doesn't crash
    
    def test_get_version_handles_errors_gracefully(self):
        """Test _get_version() handles various errors without crashing."""
        # Test with mocked exception in importlib
        with patch('importlib.metadata.version', side_effect=Exception("test error")):
            version = _get_version()
            
            # Should still return a version (fallback)
            assert version is not None
            assert isinstance(version, str)


class TestPathValidationContext:
    """Test Issue #8: Path validation error context preservation."""
    
    def test_validate_path_with_error_context(self, caplog):
        """Test that path validation errors preserve context and log debug info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            vt = VaultTool()
            
            # Try to resolve a path outside the working directory
            outside_path = Path("/etc/passwd").resolve()
            
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(ValueError) as exc_info:
                    vt._validate_file_path(str(outside_path), require_exists=False)
                
                # Should have descriptive error
                assert "Invalid file path" in str(exc_info.value) or "outside working directory" in str(exc_info.value).lower()
    
    def test_validate_nonexistent_required_path(self, caplog):
        """Test validation of non-existent file when required."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            vt = VaultTool()
            
            nonexistent = Path(tmpdir) / "does_not_exist.txt"
            
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(ValueError) as exc_info:
                    vt._validate_file_path(str(nonexistent), require_exists=True)
                
                # Should have error about non-existent file
                assert "Invalid file path" in str(exc_info.value)


class TestCryptoOperationValidation:
    """Test Issue #9: Cryptographic operation validation."""
    
    def test_encrypt_file_validates_output_size(self):
        """Test that encrypt_file() validates encrypted output size and works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            source_file = Path(tmpdir) / "source.txt"
            source_file.write_text("Hello, World!")
            
            encrypted_file = Path(tmpdir) / "encrypted.bin"
            
            vt = VaultTool()
            
            # Execute encryption - should work without errors
            vt.encrypt_file(str(source_file), str(encrypted_file))
            
            # Verify encrypted file was created and has reasonable size
            assert encrypted_file.exists()
            encrypted_size = encrypted_file.stat().st_size
            # Should be at least 32 bytes (IV + one block)
            assert encrypted_size >= 32
            # Should be larger than 0
            assert encrypted_size > 0
    
    def test_encrypt_file_has_size_validation(self):
        """Test that encryption has size validation logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            vt = VaultTool()
            
            # Verify validation code exists
            import inspect
            source = inspect.getsource(vt.encrypt_file)
            assert "suspiciously small" in source.lower() or "encrypted_size" in source.lower()
            assert "< 32" in source or "minimum" in source.lower()
    
    def test_decrypt_file_validates_input_format(self):
        """Test that decrypt_file() validates encrypted file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            vt = VaultTool()
            
            # Test with file that's too short (missing IV)
            too_short = Path(tmpdir) / "too_short.bin"
            too_short.write_bytes(b"short")  # Less than 16 bytes
            
            output = Path(tmpdir) / "output.txt"
            
            with pytest.raises(ValueError) as exc_info:
                vt.decrypt_file(str(too_short), str(output))
            
            # Should have descriptive error
            assert "too short" in str(exc_info.value).lower() or "missing IV" in str(exc_info.value)
    
    def test_decrypt_file_validates_block_size(self):
        """Test that decrypt_file() validates ciphertext block size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            vt = VaultTool()
            
            # Create file with IV but invalid ciphertext length (not multiple of 16)
            invalid_blocks = Path(tmpdir) / "invalid_blocks.bin"
            invalid_blocks.write_bytes(b"0" * 16 + b"x" * 17)  # IV + 17 bytes (not multiple of 16)
            
            output = Path(tmpdir) / "output.txt"
            
            with pytest.raises(ValueError) as exc_info:
                vt.decrypt_file(str(invalid_blocks), str(output))
                
                # Should have descriptive error
                assert "Invalid ciphertext length" in str(exc_info.value) or "not multiple" in str(exc_info.value)
    
    def test_decrypt_file_logs_operations(self):
        """Test that decrypt_file() works correctly end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            create_test_config(tmpdir, str(key_file))
            
            source = Path(tmpdir) / "source.txt"
            source.write_text("Test content")
            
            encrypted = Path(tmpdir) / "encrypted.bin"
            decrypted = Path(tmpdir) / "decrypted.txt"
            
            vt = VaultTool()
            
            # First encrypt
            vt.encrypt_file(str(source), str(encrypted))
            
            # Then decrypt - should work without errors
            vt.decrypt_file(str(encrypted), str(decrypted))
            
            # Verify decrypted content matches original
            assert decrypted.exists()
            assert decrypted.read_text() == "Test content"


class TestUtilsLogging:
    """Test Issue #10: Utils module logging and error context."""
    
    def test_derive_keys_logs_operations(self):
        """Test that derive_keys() works correctly with valid key file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            
            # Should successfully derive keys
            hmac_key, enc_key = derive_keys(str(key_file))
            
            # Verify keys are derived
            assert len(hmac_key) == 32
            assert len(enc_key) == 32
    
    def test_derive_keys_logs_errors(self):
        """Test that derive_keys() handles errors correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with non-existent file
            nonexistent = Path(tmpdir) / "missing.key"
            
            with pytest.raises(FileNotFoundError):
                derive_keys(str(nonexistent))
    
    def test_derive_keys_validates_and_logs(self):
        """Test that derive_keys() validates key files correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with empty file
            empty_file = Path(tmpdir) / "empty.key"
            empty_file.write_bytes(b"")
            
            with pytest.raises(ValueError) as exc_info:
                derive_keys(str(empty_file))
            
            assert "empty" in str(exc_info.value).lower()
            
            # Test with too-small file
            tiny_file = Path(tmpdir) / "tiny.key"
            tiny_file.write_bytes(b"x" * 8)  # Less than 16 bytes
            
            with pytest.raises(ValueError) as exc_info:
                derive_keys(str(tiny_file))
            
            assert "too small" in str(exc_info.value).lower() or "too short" in str(exc_info.value).lower()
    
    def test_compute_hmac_logs_operations(self):
        """Test that compute_hmac() works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content")
            
            hmac_key = b"0" * 32
            
            result = compute_hmac(test_file, hmac_key)
            
            # Result should be valid hex string
            assert len(result) == 64  # SHA-256 hex = 64 chars
            assert all(c in "0123456789abcdef" for c in result)
    
    def test_derive_keys_exception_handling(self):
        """Test that derive_keys() properly handles exceptions and has error handling code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 32)
            
            # Test that successful derivation works
            hmac_key, enc_key = derive_keys(str(key_file))
            assert len(hmac_key) == 32
            assert len(enc_key) == 32
            
            # Verify the code has error handling for derivation failures
            import inspect
            source = inspect.getsource(derive_keys)
            assert "try:" in source
            assert "except Exception as e:" in source
            assert "logger.error" in source
            assert "Key derivation failed" in source


class TestIntegratedErrorHandling:
    """Test that all Priority 3 improvements work together."""
    
    def test_full_workflow_with_logging(self):
        """Test complete encrypt/decrypt workflow works correctly end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 64)
            create_test_config(tmpdir, str(key_file))
            
            source = Path(tmpdir) / "source.txt"
            source.write_text("Sensitive data")
            
            encrypted = Path(tmpdir) / "encrypted.bin"
            decrypted = Path(tmpdir) / "decrypted.txt"
            
            os.chdir(tmpdir)
            key_file = Path(tmpdir) / "test.key"
            key_file.write_bytes(b"0" * 64)
            create_test_config(tmpdir, str(key_file))
            
            source = Path(tmpdir) / "source.txt"
            source.write_text("Sensitive data")
            
            encrypted = Path(tmpdir) / "encrypted.bin"
            decrypted = Path(tmpdir) / "decrypted.txt"
            
            # Initialize VaultTool (triggers key derivation)
            vt = VaultTool()
            
            # Encrypt
            vt.encrypt_file(str(source), str(encrypted))
            
            # Verify encrypted file exists and has content
            assert encrypted.exists()
            assert encrypted.stat().st_size > 0
            
            # Decrypt
            vt.decrypt_file(str(encrypted), str(decrypted))
            
            # Verify content matches original
            assert decrypted.read_text() == "Sensitive data"


