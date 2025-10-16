"""Tests for suffix fallback behavior.

This module tests that VaultTool properly handles suffix fallback when
use_suffix_fallback is enabled and a custom suffix is configured.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from vaulttool.core import VaultTool


class TestSuffixFallback:
    """Test suffix fallback functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Save original cwd first (before creating temp dir)
        try:
            self.original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current directory doesn't exist, use a safe default
            self.original_cwd = Path.home()
            
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        
        # Create key file
        self.key_file = Path('test.key')
        self.key_file.write_text('a' * 32)
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_custom_suffix_encryption_creates_custom_vault(self):
        """Test that encryption with custom suffix creates custom vault file."""
        # Create config with custom suffix
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Create source file
        Path('config.env').write_text('SECRET=value\n')
        
        # Encrypt
        vt = VaultTool()
        result = vt.encrypt_task(force=True)
        
        # Should create custom suffix vault
        assert result['created'] == 1
        assert Path('config.env.secret.vault').exists()
        assert not Path('config.env.vault').exists()
    
    def test_decryption_with_only_custom_suffix_vault(self):
        """Test decryption when only custom suffix vault exists."""
        # Create config with custom suffix
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Create and encrypt source file
        Path('config.env').write_text('SECRET=value\n')
        vt = VaultTool()
        vt.encrypt_task(force=True)
        
        # Remove source file
        Path('config.env').unlink()
        
        # Decrypt
        result = vt.refresh_task(force=True)
        
        # Should restore from custom suffix vault
        assert result['succeeded'] == 1
        assert Path('config.env').exists()
        assert Path('config.env').read_text() == 'SECRET=value\n'
    
    def test_decryption_fallback_to_generic_vault(self):
        """Test that decryption falls back to .vault when custom suffix doesn't exist."""
        # Create generic vault file first (simulating old setup)
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        Path('config.env').write_text('OLD_VALUE=generic\n')
        vt_old = VaultTool()
        vt_old.encrypt_task(force=True)
        assert Path('config.env.vault').exists()
        
        # Remove source
        Path('config.env').unlink()
        
        # Now switch to custom suffix with fallback enabled
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Decrypt - should fallback to .vault
        vt_new = VaultTool()
        result = vt_new.refresh_task(force=True)
        
        # Should restore from generic .vault as fallback
        assert result['succeeded'] == 1
        assert Path('config.env').exists()
        assert Path('config.env').read_text() == 'OLD_VALUE=generic\n'
    
    def test_custom_suffix_preferred_over_generic_vault(self):
        """Test that custom suffix vault is preferred when both exist."""
        # Create generic vault first
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        Path('config.env').write_text('GENERIC=value\n')
        vt_generic = VaultTool()
        vt_generic.encrypt_task(force=True)
        assert Path('config.env.vault').exists()
        
        # Now create custom suffix vault with different content
        Path('config.env').write_text('CUSTOM=different\n')
        
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        vt_custom = VaultTool()
        vt_custom.encrypt_task(force=True)
        assert Path('config.env.secret.vault').exists()
        
        # Remove source
        Path('config.env').unlink()
        
        # Decrypt - should use custom suffix (not generic)
        result = vt_custom.refresh_task(force=True)
        
        # Should restore from custom suffix vault, not generic
        assert result['succeeded'] == 1
        assert Path('config.env').exists()
        assert Path('config.env').read_text() == 'CUSTOM=different\n'
    
    def test_fallback_disabled_ignores_generic_vault(self):
        """Test that fallback disabled only reads custom suffix vaults."""
        # Create generic vault
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        Path('config.env').write_text('GENERIC=value\n')
        vt_generic = VaultTool()
        vt_generic.encrypt_task(force=True)
        Path('config.env').unlink()
        
        # Switch to custom suffix with fallback DISABLED
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Should not find any vault files (custom suffix doesn't exist, fallback disabled)
        vt_custom = VaultTool()
        vault_files = list(vt_custom.iter_vault_files())
        
        assert len(vault_files) == 0
    
    def test_multiple_files_with_mixed_vaults(self):
        """Test multiple files with some having custom suffix and some only generic."""
        # Create first file with generic vault
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        Path('file1.env').write_text('FILE1=generic\n')
        Path('file2.env').write_text('FILE2=generic\n')
        vt_generic = VaultTool()
        vt_generic.encrypt_task(force=True)
        
        # Now create custom suffix vault for file2 only
        Path('file2.env').write_text('FILE2=custom\n')
        
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .secret.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        vt_custom = VaultTool()
        vt_custom.encrypt_task(force=True)
        
        # Should have both vaults
        assert Path('file1.env.vault').exists()  # Only generic
        assert Path('file2.env.vault').exists()  # Old generic
        assert Path('file2.env.secret.vault').exists()  # New custom
        
        # Remove source files
        Path('file1.env').unlink()
        Path('file2.env').unlink()
        
        # Decrypt - file1 should use generic fallback, file2 should use custom
        result = vt_custom.refresh_task(force=True)
        
        assert result['succeeded'] == 2
        assert Path('file1.env').read_text() == 'FILE1=generic\n'  # From fallback
        assert Path('file2.env').read_text() == 'FILE2=custom\n'  # From custom suffix
    
    def test_environment_variable_custom_suffix(self):
        """Test suffix fallback with environment variable configuration."""
        # Create generic vault
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        Path('config.env').write_text('GENERIC=value\n')
        vt_generic = VaultTool()
        vt_generic.encrypt_task(force=True)
        Path('config.env').unlink()
        
        # Use environment variable to set custom suffix with fallback
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = '.prod.vault'
        os.environ['VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK'] = 'true'
        
        try:
            # Should fallback to generic .vault
            vt_env = VaultTool()
            result = vt_env.refresh_task(force=True)
            
            assert result['succeeded'] == 1
            assert Path('config.env').read_text() == 'GENERIC=value\n'
        finally:
            # Clean up env vars
            os.environ.pop('VAULTTOOL_OPTIONS_SUFFIX', None)
            os.environ.pop('VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK', None)

    def test_remove_deletes_both_custom_and_fallback_vaults(self):
        """Test that remove task deletes both custom suffix and fallback .vault files."""
        # Create config with custom suffix and fallback enabled
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .prod.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Create source file and encrypt with custom suffix
        Path('config.env').write_text('CONFIG=prod_value\n')
        vt_custom = VaultTool()
        vt_custom.encrypt_task(force=True)
        
        # Verify custom vault exists
        assert Path('config.env.prod.vault').exists()
        
        # Create another file with generic .vault suffix (simulating fallback scenario)
        Path('legacy.env').write_text('LEGACY=value\n')
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: false

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        vt_legacy = VaultTool()
        vt_legacy.encrypt_task(force=True)
        
        # Verify generic vault exists
        assert Path('legacy.env.vault').exists()
        
        # Now switch back to custom suffix with fallback
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .prod.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
        
        # Run remove task - should remove BOTH custom and fallback vaults
        vt_remove = VaultTool()
        result = vt_remove.remove_task()
        
        # Verify both vault files were removed
        assert not Path('config.env.prod.vault').exists(), "Custom suffix vault should be removed"
        assert not Path('legacy.env.vault').exists(), "Fallback .vault file should be removed"
        
        # Should remove at least 2 files (the ones we explicitly created)
        assert result['removed'] >= 2, f"Expected at least 2 files removed, got {result['removed']}"
        assert result['failed'] == 0, f"Expected 0 failures, got {result['failed']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
