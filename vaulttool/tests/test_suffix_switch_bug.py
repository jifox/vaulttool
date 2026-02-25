"""Test for bug fix: refresh creates wrong filename when suffix changes.

This test suite addresses the issue where `vaulttool refresh` would create
a file with an incorrect name (missing source filename) when the suffix
configuration changed between encryption and refresh operations.

Issue:
- Encrypt file with VAULTTOOL_OPTIONS_SUFFIX=n3test.vault creates development/creds.env_n3test.vault
- Run refresh → should restore development/creds.env
- BUG: created development/creds.env_n3test instead

Root Cause:
When a vault file from a previous suffix (e.g., .prod.vault) is found during refresh
with a different current suffix (e.g., _n3test.vault), the fallback logic would
incorrectly use ".vault" as the suffix, removing only 6 characters instead of 12,
resulting in an incorrect source filename.

Fix:
infer_vault_suffix() method now intelligently determines the actual vault suffix
by recognizing common file extensions (.env, .ini, etc.) and correctly inferring
custom suffixes like .prod.vault.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from vaulttool.core import VaultTool


class TestSuffixSwitchBugFix:
    """Test that refresh correctly handles vault files with different suffix than current."""

    def setup_method(self):
        """Set up test environment."""
        try:
            self.original_cwd = os.getcwd()
        except FileNotFoundError:
            self.original_cwd = Path.home()

        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)

        # Create key file
        self.key_file = Path('test.key')
        self.key_file.write_text('a' * 32)

        # Create development directory
        Path('development').mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_env_variable_suffix_refresh_restores_correct_file(self):
        """Test the exact bug scenario: suffix changed via env var, refresh restores source."""
        # Setup config with default .vault
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns:
  - "*.env"
exclude_patterns: []
""")

        # Create and encrypt with environment variable suffix
        Path('development/creds.env').write_text('DATABASE_PASSWORD=super_secret\n')
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = 'n3test.vault'

        vt = VaultTool()
        vt.encrypt_task(force=True)

        # Verify vault file created with correct name
        assert Path('development/creds.env_n3test.vault').exists()
        source_file = Path('development/creds.env')
        assert source_file.exists()

        # Delete source file
        source_file.unlink()

        # Run refresh - should restore development/creds.env
        result = vt.refresh_task(force=True)

        # Verify success
        assert result['succeeded'] == 1
        assert result['failed'] == 0

        # CRITICAL: Check that the CORRECT file was restored
        assert Path('development/creds.env').exists(), "Source file not restored"
        assert Path('development/creds.env').read_text() == 'DATABASE_PASSWORD=super_secret\n'

        # CRITICAL: Check that no wrong files were created
        wrong_files = list(Path('development').glob('*_n3test'))
        assert len(wrong_files) == 0, f"Wrong file created: {wrong_files}"

    def test_infer_vault_suffix_with_various_file_extensions(self):
        """Test that infer_vault_suffix correctly handles different file types."""
        # Use .custom.vault as current suffix for this test
        Path('.vaulttool.yml').write_text(f"""
options:
  suffix: .custom.vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns:
  - "*.env"
  - "*.ini"
  - "*.yaml"
exclude_patterns: []
""")

        vt = VaultTool()

        # Test cases: (filename, expected_inferred_suffix)
        test_cases = [
            ('config.env.vault', '.vault'),  # Common .env extension
            ('config.ini.vault', '.vault'),  # Common .ini extension
            ('config.yaml.vault', '.vault'),  # Common .yaml extension
            ('config.yml.vault', '.vault'),  # Common .yml extension
            ('config.prod.vault', '.prod.vault'),  # Custom suffix (no common ext)
            ('database.cfg.vault', '.vault'),  # Common .cfg extension
            ('secret.conf.vault', '.vault'),  # Common .conf extension
        ]

        for filename, expected_suffix in test_cases:
            inferred = vt.infer_vault_suffix(filename)
            assert inferred == expected_suffix, \
                f"For {filename}: expected {expected_suffix!r}, got {inferred!r}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

