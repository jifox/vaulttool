import tempfile
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from vaulttool.core import VaultTool

def test_encrypt_files_creates_vault_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        # Create a plaintext file
        plain_path = os.path.join(tmpdir, "secret.env")
        with open(plain_path, "w") as pf:
            pf.write("SECRET=12345")
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"mysecretpassword12345678901234")  # 32 bytes for better key material
        # Write config YAML
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
        
        # Create VaultTool instance and encrypt
        vt = VaultTool()
        vt.encrypt_task()
        
        vault_path = plain_path + ".vault"
        assert os.path.exists(vault_path)
        assert os.path.getsize(vault_path) > 0
        
        # Verify vault file format (HMAC + Base64 encrypted content)
        with open(vault_path, "r") as vf:
            lines = vf.readlines()
            assert len(lines) >= 2
            hmac_tag = lines[0].strip()
            lines[1].strip()
            
            # Verify HMAC is 64 hex characters (SHA-256)
            assert len(hmac_tag) == 64
            assert all(c in '0123456789abcdef' for c in hmac_tag)
            
        # Test decryption using VaultTool's decrypt method
        os.remove(plain_path)
        vt.refresh_task()
        
        # Verify decrypted content
        with open(plain_path, "r") as f:
            assert f.read() == "SECRET=12345"



def test_source_filename_static_method():
    """Test the static source_filename method."""
    # Test with vault file
    assert VaultTool.source_filename("config.env.vault", ".vault") == "config.env"
    assert VaultTool.source_filename("secrets/api.key.vault", ".vault") == "secrets/api.key"
    
    # Test with non-vault file
    assert VaultTool.source_filename("config.env", ".vault") == "config.env"
    
    # Test with different suffix
    assert VaultTool.source_filename("config.env_prod.vault", "_prod.vault") == "config.env"


def test_vault_filename_static_method():
    """Test the vault_filename method with default settings (backward compatibility)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create minimal config with use_branch_suffix=False (default)
        key_path = Path(tmpdir) / "keyfile"
        key_path.write_bytes(b"test_key_minimum_16_bytes")
        
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
        
        # Test with default suffix
        assert vt.vault_filename("config.env") == "config.env.vault"
        assert vt.vault_filename("secrets/api.key") == "secrets/api.key.vault"
        
        # Test with custom suffix
        assert vt.vault_filename("config.env", "_prod.vault") == "config.env_prod.vault"


def test_constructor_suffix_validation():
    """Test constructor validates suffix correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Test invalid suffix without dot
        config_yaml = """
vaulttool:
  include_directories: ['.']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: "vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        with pytest.raises(ValueError, match="Suffix must contain a dot"):
            VaultTool()


def test_constructor_suffix_underscore_prefix():
    """Test constructor handles suffix correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        config_yaml = f"""
vaulttool:
  include_directories: ['.']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: "prod.vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        # The suffix should be stored as provided (with dot)
        assert vt.suffix == "_prod.vault"


def test_encrypt_file_method():
    """Test the encrypt_file method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create test files
        source_path = os.path.join(tmpdir, "test.txt")
        encrypted_path = os.path.join(tmpdir, "test.txt.enc")
        key_path = os.path.join(tmpdir, "keyfile")
        
        with open(source_path, "w") as f:
            f.write("test content")
        with open(key_path, "wb") as f:
            f.write(b"testkey-16-bytes")  # 16 bytes minimum
        
        # Create VaultTool with minimal config
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.txt']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
    algorithm: "aes-256-cbc"
    openssl_path: "openssl"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        vt.encrypt_file(source_path, encrypted_path)
        
        assert os.path.exists(encrypted_path)
        assert os.path.getsize(encrypted_path) > 0


def test_decrypt_file_method():
    """Test the decrypt_file method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create test files
        source_path = os.path.join(tmpdir, "test.txt")
        encrypted_path = os.path.join(tmpdir, "test.txt.enc")
        decrypted_path = os.path.join(tmpdir, "test.txt.dec")
        key_path = os.path.join(tmpdir, "keyfile")
        
        with open(source_path, "w") as f:
            f.write("test content")
        with open(key_path, "wb") as f:
            f.write(b"testkey-16-bytes")  # 16 bytes minimum
        
        # Create VaultTool with minimal config
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.txt']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
    algorithm: "aes-256-cbc"
    openssl_path: "openssl"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        # First encrypt
        vt.encrypt_file(source_path, encrypted_path)
        # Then decrypt
        vt.decrypt_file(encrypted_path, decrypted_path)
        
        assert os.path.exists(decrypted_path)
        with open(decrypted_path) as f:
            assert f.read() == "test content"


def test_iter_source_files():
    """Test the iter_source_files generator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create test files
        env_file = Path(tmpdir) / "config.env"
        txt_file = Path(tmpdir) / "readme.txt"
        log_file = Path(tmpdir) / "app.log"
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        sub_env_file = subdir / "sub.env"
        
        env_file.touch()
        txt_file.touch()
        log_file.touch()
        sub_env_file.touch()
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: ['*.log']
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        source_files = list(vt.iter_source_files())
        
        # Should include .env files but not .log files
        assert len(source_files) == 2
        file_names = [f.name for f in source_files]
        assert "config.env" in file_names
        assert "sub.env" in file_names
        assert "app.log" not in file_names
        assert "readme.txt" not in file_names


def test_iter_vault_files():
    """Test the iter_vault_files generator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create test vault files
        vault1 = Path(tmpdir) / "config.env.vault"
        vault2 = Path(tmpdir) / "secrets.txt.vault"
        not_vault = Path(tmpdir) / "normal.txt"
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        vault3 = subdir / "sub.env.vault"
        
        vault1.touch()
        vault2.touch()
        not_vault.touch()
        vault3.touch()
        
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
        vault_files = list(vt.iter_vault_files())
        
        assert len(vault_files) == 3
        file_names = [f.name for f in vault_files]
        assert "config.env.vault" in file_names
        assert "secrets.txt.vault" in file_names
        assert "sub.env.vault" in file_names
        assert "normal.txt" not in file_names


def test_iter_missing_sources():
    """Test the iter_missing_sources generator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create vault files with and without corresponding source files
        vault1 = Path(tmpdir) / "config.env.vault"
        vault2 = Path(tmpdir) / "secrets.txt.vault"
        source1 = Path(tmpdir) / "config.env"  # This source exists
        # source2 does not exist (missing)
        
        vault1.touch()
        vault2.touch()
        source1.touch()
        
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
        missing_sources = list(vt.iter_missing_sources())
        
        assert len(missing_sources) == 1
        assert missing_sources[0].name == "secrets.txt"


def test_add_to_gitignore():
    """Test the add_to_gitignore method."""
    if os.getenv("VAULTTOOL_PRECOMMIT") == "1":
        pytest.skip("Skipping test in pre-commit environment")
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Initialize git repo
        os.system("git init")
        
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
        test_file = Path(tmpdir) / "secret.env"
        
        # Initially no .gitignore
        assert not Path(".gitignore").exists()
        
        vt.add_to_gitignore(test_file)
        
        # .gitignore should be created and contain the file
        assert Path(".gitignore").exists()
        with open(".gitignore") as f:
            content = f.read()
        assert "secret.env" in content
        
        # Adding same file again should not duplicate
        vt.add_to_gitignore(test_file)
        with open(".gitignore") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        assert lines.count("secret.env") == 1


def test_add_to_gitignore_precommit_env():
    """Test add_to_gitignore respects VAULTTOOL_PRECOMMIT environment variable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Initialize git repo
        os.system("git init")
        
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
        
        with patch.dict(os.environ, {"VAULTTOOL_PRECOMMIT": "1"}):
            # Need to reimport the module to pick up the environment variable
            import importlib
            from vaulttool import core
            importlib.reload(core)
            
            vt = core.VaultTool()
            test_file = Path(tmpdir) / "secret.env"
            
            vt.add_to_gitignore(test_file)
            
            # .gitignore should NOT be created in precommit mode
            assert not Path(".gitignore").exists()


def test_remove_vault_files():
    """Test the remove_vault_files method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create test vault files
        vault1 = Path(tmpdir) / "config.env.vault"
        vault2 = Path(tmpdir) / "secrets.txt.vault"
        not_vault = Path(tmpdir) / "normal.txt"
        
        vault1.touch()
        vault2.touch()
        not_vault.touch()
        
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
        vt.remove_task()
        
        # Vault files should be removed
        assert not vault1.exists()
        assert not vault2.exists()
        # Non-vault files should remain
        assert not_vault.exists()


def test_validate_gitignore():
    """Test the validate_gitignore method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create test files
        env_file = Path(tmpdir) / "config.env"
        env_file.touch()
        
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
        # This should not raise any exceptions
        vt.check_ignore_task()


def test_encrypt_with_force_parameter():
    """Test encrypt method with force parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create test files
        source_path = Path(tmpdir) / "secret.env"
        key_path = Path(tmpdir) / "keyfile"
        
        source_path.write_text("SECRET=12345")
        key_path.write_bytes(b"testkey-16-bytes")  # 16 bytes minimum
        
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
        vault_path = source_path.with_suffix(source_path.suffix + ".vault")
        assert vault_path.exists()
        
        # Get initial modification time
        initial_mtime = vault_path.stat().st_mtime
        
        # Wait a bit to ensure different timestamp
        import time
        time.sleep(0.1)
        
        # Encrypt again without force - should not update (same checksum)
        vt.encrypt_task(force=False)
        assert vault_path.stat().st_mtime == initial_mtime
        
        # Encrypt with force - should update even with same checksum
        vt.encrypt_task(force=True)
        assert vault_path.stat().st_mtime > initial_mtime


def test_exclude_directories():
    """Test that exclude_directories works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")

        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create directory structure
        included_dir = Path(tmpdir) / "included"
        excluded_dir = Path(tmpdir) / "excluded"
        included_dir.mkdir()
        excluded_dir.mkdir()
        
        included_file = included_dir / "config.env"
        excluded_file = excluded_dir / "secret.env"
        included_file.touch()
        excluded_file.touch()
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: ['excluded']
  include_patterns: ['*.env']
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        source_files = list(vt.iter_source_files())
        
        # Should only include files from non-excluded directories
        assert len(source_files) == 1
        assert source_files[0].name == "config.env"


def test_exclude_patterns():
    """Test that exclude_patterns works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Create a key file
        key_path = os.path.join(tmpdir, "keyfile")
        with open(key_path, "wb") as kf:
            kf.write(b"test_key_12345678901234567890")
        
        # Create test files
        env_file = Path(tmpdir) / "config.env"
        log_file = Path(tmpdir) / "app.log"
        txt_file = Path(tmpdir) / "readme.txt"
        
        env_file.touch()
        log_file.touch()
        txt_file.touch()
        
        config_yaml = f"""
vaulttool:
  include_directories: ['{tmpdir}']
  exclude_directories: []
  include_patterns: ['*.env']
  exclude_patterns: ['*.log', '*.txt', '*.yml']
  options:
    suffix: ".vault"
    key_file: "{key_path}"
"""
        with open(".vaulttool.yml", "w") as cf:
            cf.write(config_yaml)
        
        vt = VaultTool()
        source_files = list(vt.iter_source_files())
        
        # Should only include .env file, excluding .log, .txt, and .yml files
        assert len(source_files) == 1
        assert source_files[0].name == "config.env"
