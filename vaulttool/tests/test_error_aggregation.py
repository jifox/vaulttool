"""Tests for error aggregation and return values from task methods."""

import os
import pytest
from vaulttool.core import VaultTool
from vaulttool import setup_logging
import logging


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests to suppress output."""
    setup_logging(level=logging.ERROR)  # Only show errors during tests


def test_refresh_task_returns_summary(tmp_path):
    """Test that refresh_task returns a summary dict with correct keys."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file and encrypt it
    source = tmp_path / "test.txt"
    source.write_text("test content")
    
    vt = VaultTool()
    vt.encrypt_task()
    
    # Now test refresh_task
    source.unlink()  # Remove source to trigger refresh
    result = vt.refresh_task(force=True)
    
    # Verify result structure
    assert isinstance(result, dict)
    assert 'total' in result
    assert 'succeeded' in result
    assert 'failed' in result
    assert 'skipped' in result
    assert 'errors' in result
    
    # Verify values
    assert result['total'] == 1
    assert result['succeeded'] == 1
    assert result['failed'] == 0
    assert result['skipped'] == 0
    assert len(result['errors']) == 0


def test_encrypt_task_returns_summary(tmp_path):
    """Test that encrypt_task returns a summary dict with correct keys."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source files
    source1 = tmp_path / "test1.txt"
    source1.write_text("test content 1")
    source2 = tmp_path / "test2.txt"
    source2.write_text("test content 2")
    
    vt = VaultTool()
    result = vt.encrypt_task()
    
    # Verify result structure
    assert isinstance(result, dict)
    assert 'total' in result
    assert 'created' in result
    assert 'updated' in result
    assert 'skipped' in result
    assert 'failed' in result
    assert 'errors' in result
    
    # Verify values
    assert result['total'] == 2
    assert result['created'] == 2
    assert result['updated'] == 0
    assert result['failed'] == 0
    assert len(result['errors']) == 0


def test_remove_task_returns_summary(tmp_path):
    """Test that remove_task returns a summary dict with correct keys."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file and encrypt it
    source = tmp_path / "test.txt"
    source.write_text("test content")
    
    vt = VaultTool()
    vt.encrypt_task()
    
    # Now test remove_task
    result = vt.remove_task()
    
    # Verify result structure
    assert isinstance(result, dict)
    assert 'total' in result
    assert 'removed' in result
    assert 'failed' in result
    assert 'errors' in result
    
    # Verify values
    assert result['total'] == 1
    assert result['removed'] == 1
    assert result['failed'] == 0
    assert len(result['errors']) == 0
    
    # Verify vault file was actually removed
    vault_file = tmp_path / "test.txt.vault"
    assert not vault_file.exists()


def test_encrypt_task_with_force_updates_existing(tmp_path):
    """Test that encrypt_task with force=True updates existing vault files."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file and encrypt it
    source = tmp_path / "test.txt"
    source.write_text("test content")
    
    vt = VaultTool()
    
    # First encrypt
    result1 = vt.encrypt_task()
    assert result1['created'] == 1
    assert result1['updated'] == 0
    
    # Second encrypt without force (should skip)
    result2 = vt.encrypt_task(force=False)
    assert result2['skipped'] == 1
    assert result2['created'] == 0
    assert result2['updated'] == 0
    
    # Third encrypt with force (should update)
    result3 = vt.encrypt_task(force=True)
    assert result3['updated'] == 1
    assert result3['created'] == 0
    assert result3['skipped'] == 0


def test_refresh_task_with_malformed_vault_file(tmp_path):
    """Test that refresh_task handles malformed vault files gracefully."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create a malformed vault file (only 1 line, needs 2)
    vault_file = tmp_path / "test.txt.vault"
    vault_file.write_text("just-one-line\n")
    
    vt = VaultTool()
    result = vt.refresh_task(force=True)
    
    # Should fail gracefully
    assert result['total'] == 1
    assert result['failed'] == 1
    assert result['succeeded'] == 0
    assert len(result['errors']) == 1
    
    # Check error details
    vault_path, error_msg = result['errors'][0]
    assert "test.txt.vault" in vault_path
    assert "Malformed" in error_msg or "insufficient" in error_msg.lower()


def test_refresh_task_skips_existing_when_force_false(tmp_path):
    """Test that refresh_task skips existing files when force=False."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file and encrypt it
    source = tmp_path / "test.txt"
    source.write_text("test content")
    
    vt = VaultTool()
    vt.encrypt_task()
    
    # Source file already exists, refresh with force=False should skip
    result = vt.refresh_task(force=False)
    
    assert result['total'] == 1
    assert result['skipped'] == 1
    assert result['succeeded'] == 0
    assert result['failed'] == 0


def test_encrypt_task_validates_write_operations(tmp_path):
    """Test that encrypt_task validates vault file writes properly."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file
    source = tmp_path / "test.txt"
    source.write_text("test content for validation")
    
    vt = VaultTool()
    result = vt.encrypt_task()
    
    # Should succeed with validation
    assert result['total'] == 1
    assert result['created'] == 1
    assert result['failed'] == 0
    
    # Verify vault file exists and has correct structure
    vault_file = tmp_path / "test.txt.vault"
    assert vault_file.exists()
    
    # Verify content structure
    content = vault_file.read_text()
    lines = content.split('\n')
    assert len(lines) >= 2  # At least HMAC line and encrypted line
    assert len(lines[0]) == 64  # HMAC is 64 hex chars
    assert len(lines[1]) > 0  # Encrypted content exists


def test_file_write_verification_detects_issues(tmp_path, monkeypatch):
    """Test that file write verification catches problems."""
    # Setup
    os.chdir(tmp_path)
    
    # Create key file
    key_file = tmp_path / "test.key"
    key_file.write_text("test-key-16-bytes-minimum")
    
    # Create config
    config_file = tmp_path / ".vaulttool.yml"
    config_file.write_text(f"""
vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.txt"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
""")
    
    # Create source file
    source = tmp_path / "test.txt"
    source.write_text("test content")
    
    # First, create a valid vault file
    vt = VaultTool()
    result = vt.encrypt_task()
    assert result['created'] == 1
    
    # Verify the vault file is valid and complete
    vault_file = tmp_path / "test.txt.vault"
    assert vault_file.exists()
    original_size = vault_file.stat().st_size
    assert original_size > 0
    
    # Verify we can read it back
    with open(vault_file, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 2
