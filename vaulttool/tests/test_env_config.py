"""Tests for environment variable configuration overrides.

This module tests that VAULTTOOL_ environment variables properly override
configuration file settings.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from vaulttool.config import load_config, _parse_bool, _parse_list


class TestEnvironmentVariableOverrides:
    """Test environment variable configuration overrides."""
    
    def setup_method(self):
        """Set up test environment."""
        # Save original cwd first (before creating temp dir)
        try:
            self.original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current directory doesn't exist, use a safe default
            self.original_cwd = Path.home()
        
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()
        os.chdir(self.test_dir)
        
        # Create basic config file
        self.config_file = Path('.vaulttool.yml')
        self.config_file.write_text("""
options:
  suffix: .vault
  key_file: /home/user/.vaulttool/key
  use_suffix_fallback: true

include_directories:
  - .

exclude_directories:
  - .git

include_patterns:
  - "*.env"

exclude_patterns:
  - "*.log"
""")
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        # Restore original environment - clear all VAULTTOOL_ vars first
        for key in list(os.environ.keys()):
            if key.startswith('VAULTTOOL_'):
                del os.environ[key]
        # Then restore original
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_parse_bool_true_values(self):
        """Test boolean parsing for true values."""
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("1") is True
        assert _parse_bool("on") is True
    
    def test_parse_bool_false_values(self):
        """Test boolean parsing for false values."""
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("no") is False
        assert _parse_bool("0") is False
        assert _parse_bool("off") is False
    
    def test_parse_list_single_item(self):
        """Test list parsing with single item."""
        result = _parse_list("*.env")
        assert result == ["*.env"]
    
    def test_parse_list_multiple_items(self):
        """Test list parsing with multiple items."""
        result = _parse_list("*.env,*.ini,*.secret")
        assert result == ["*.env", "*.ini", "*.secret"]
    
    def test_parse_list_with_spaces(self):
        """Test list parsing with spaces."""
        result = _parse_list("*.env, *.ini , *.secret")
        assert result == ["*.env", "*.ini", "*.secret"]
    
    def test_parse_list_empty(self):
        """Test list parsing with empty string."""
        result = _parse_list("")
        assert result == []
    
    def test_no_env_overrides(self):
        """Test config loading without environment overrides."""
        config = load_config()
        assert config['options']['key_file'] == '/home/user/.vaulttool/key'
        assert config['options']['use_suffix_fallback'] is True  # Default is True
        assert config['include_directories'] == ['.']
        assert '*.env' in config['include_patterns']
    
    def test_env_override_key_file(self):
        """Test overriding key_file with environment variable."""
        os.environ['VAULTTOOL_OPTIONS_KEY_FILE'] = '/custom/path/key'
        config = load_config()
        assert config['options']['key_file'] == '/custom/path/key'
    
    def test_env_override_use_suffix_fallback(self):
        """Test overriding use_suffix_fallback with environment variable."""
        os.environ['VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK'] = 'true'
        config = load_config()
        assert config['options']['use_suffix_fallback'] is True
        
        os.environ['VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK'] = 'false'
        config = load_config()
        assert config['options']['use_suffix_fallback'] is False
    
    def test_env_override_suffix(self):
        """Test overriding suffix with environment variable."""
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = '.encrypted.vault'
        config = load_config()
        assert config['options']['suffix'] == '.encrypted.vault'
    
    def test_env_override_include_patterns(self):
        """Test overriding include_patterns with environment variable."""
        os.environ['VAULTTOOL_INCLUDE_PATTERNS'] = '*.secret,*.credentials,*.key'
        config = load_config()
        assert '*.secret' in config['include_patterns']
        assert '*.credentials' in config['include_patterns']
        assert '*.key' in config['include_patterns']
    
    def test_env_override_exclude_directories(self):
        """Test overriding exclude_directories with environment variable."""
        os.environ['VAULTTOOL_EXCLUDE_DIRECTORIES'] = '.git,.venv,node_modules'
        config = load_config()
        assert '.git' in config['exclude_directories']
        assert '.venv' in config['exclude_directories']
        assert 'node_modules' in config['exclude_directories']
    
    def test_env_override_include_directories(self):
        """Test overriding include_directories with environment variable."""
        os.environ['VAULTTOOL_INCLUDE_DIRECTORIES'] = './src,./config,./secrets'
        config = load_config()
        assert './src' in config['include_directories']
        assert './config' in config['include_directories']
        assert './secrets' in config['include_directories']
    
    def test_env_override_exclude_patterns(self):
        """Test overriding exclude_patterns with environment variable."""
        os.environ['VAULTTOOL_EXCLUDE_PATTERNS'] = '*.log,*.tmp,*.bak'
        config = load_config()
        assert '*.log' in config['exclude_patterns']
        assert '*.tmp' in config['exclude_patterns']
        assert '*.bak' in config['exclude_patterns']
    
    def test_multiple_env_overrides(self):
        """Test multiple environment overrides simultaneously."""
        os.environ['VAULTTOOL_OPTIONS_KEY_FILE'] = '/env/key'
        os.environ['VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK'] = 'false'
        os.environ['VAULTTOOL_INCLUDE_PATTERNS'] = '*.env,*.secret'
        os.environ['VAULTTOOL_EXCLUDE_DIRECTORIES'] = '.git,.venv'
        
        config = load_config()
        assert config['options']['key_file'] == '/env/key'
        assert config['options']['use_suffix_fallback'] is False
        assert '*.env' in config['include_patterns']
        assert '*.secret' in config['include_patterns']
        assert '.git' in config['exclude_directories']
        assert '.venv' in config['exclude_directories']
    
    def test_env_overrides_take_precedence(self):
        """Test that environment variables override config file values."""
        # Config file has: key_file = /home/user/.vaulttool/key
        config_no_env = load_config()
        assert config_no_env['options']['key_file'] == '/home/user/.vaulttool/key'
        
        # Environment variable should override
        os.environ['VAULTTOOL_OPTIONS_KEY_FILE'] = '/override/key'
        config_with_env = load_config()
        assert config_with_env['options']['key_file'] == '/override/key'
    
    def test_suffix_validation_ends_with_vault(self):
        """Test that suffix must end with .vault."""
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = '.encrypted.vault'
        config = load_config()
        assert config['options']['suffix'] == '.encrypted.vault'
        
        # Invalid suffix (doesn't end with .vault)
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = '.encrypted'
        with pytest.raises(ValueError, match="must end with '\\.vault'"):
            load_config()
    
    def test_suffix_added_to_exclude_patterns(self):
        """Test that suffix pattern is automatically added to exclude_patterns."""
        config = load_config()
        assert '*.vault' in config['exclude_patterns']
        
        # Custom suffix
        os.environ['VAULTTOOL_OPTIONS_SUFFIX'] = '.secret.vault'
        config = load_config()
        assert '*.secret.vault' in config['exclude_patterns']


class TestEnvironmentVariableIntegration:
    """Integration tests with VaultTool using environment variables."""
    
    def setup_method(self):
        """Set up test environment."""
        # Save original cwd first (before creating temp dir)
        try:
            self.original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current directory doesn't exist, use a safe default
            self.original_cwd = Path.home()
        
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()
        os.chdir(self.test_dir)
        
        # Setup git
        os.makedirs('.git/refs/heads', exist_ok=True)
        with open('.git/HEAD', 'w') as f:
            f.write('ref: refs/heads/main\n')
        
        # Create key file
        self.key_file = Path('test.key')
        self.key_file.write_text('a' * 32)
        
        # Create basic config
        self.config_file = Path('.vaulttool.yml')
        self.config_file.write_text(f"""
options:
  suffix: .vault
  key_file: {self.key_file.absolute()}
  use_suffix_fallback: true

include_directories: [.]
exclude_directories: []
include_patterns: ["*.env"]
exclude_patterns: []
""")
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        # Restore original environment - clear all VAULTTOOL_ vars first
        for key in list(os.environ.keys()):
            if key.startswith('VAULTTOOL_'):
                del os.environ[key]
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_vaulttool_with_env_override(self):
        """Test VaultTool initialization with environment overrides."""
        from vaulttool.core import VaultTool
        
        # Enable suffix fallback via environment (default is already true)
        os.environ['VAULTTOOL_OPTIONS_USE_SUFFIX_FALLBACK'] = 'true'
        
        vt = VaultTool()
        assert vt.use_suffix_fallback is True
        assert vt.suffix == '.vault'
    
    def test_encryption_with_env_patterns(self):
        """Test encryption with environment-defined patterns."""
        from vaulttool.core import VaultTool
        
        # Create source files
        Path('config.env').write_text('SECRET=value\n')
        Path('database.ini').write_text('password=secret\n')
        
        # Override patterns via environment to include both
        os.environ['VAULTTOOL_INCLUDE_PATTERNS'] = '*.env,*.ini'
        
        vt = VaultTool()
        result = vt.encrypt_task(force=True)
        
        # Should encrypt both files
        assert result['total'] == 2
        assert Path('config.env.vault').exists()
        assert Path('database.ini.vault').exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
