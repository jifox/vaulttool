import tempfile
import os
import subprocess
from unittest import mock

import pytest

from vaulttool.utils import compute_checksum, encode_base64, compute_hmac, derive_keys, get_git_branch

def test_compute_checksum_and_base64():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"vaulttool test data")
        tf.flush()
        checksum = compute_checksum(tf.name)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # sha256
        with open(tf.name, "rb") as f:
            encoded = encode_base64(f.read())
        assert isinstance(encoded, bytes)
        assert encoded.startswith(b"dmF1bHR0b29sIHRlc3QgZGF0YQ==")
    os.unlink(tf.name)


def test_derive_keys():
    """Test HKDF key derivation produces two different keys."""
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as kf:
        kf.write(b"test_master_key_for_derivation_1234567890")
        kf.flush()
        key_file = kf.name
    
    try:
        hmac_key, encryption_key = derive_keys(key_file)
        
        # Check both keys are 32 bytes
        assert len(hmac_key) == 32
        assert len(encryption_key) == 32
        
        # Check keys are different (cryptographically separated)
        assert hmac_key != encryption_key
        
        # Check keys are deterministic (same input = same output)
        hmac_key2, encryption_key2 = derive_keys(key_file)
        assert hmac_key == hmac_key2
        assert encryption_key == encryption_key2
        
    finally:
        os.unlink(key_file)


def test_compute_hmac():
    """Test HMAC computation."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as tf:
        tf.write("test data for HMAC computation")
        tf.flush()
        test_file = tf.name
    
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as kf:
        kf.write(b"test_key_1234567890")
        kf.flush()
        key_file = kf.name
    
    try:
        hmac_key, _ = derive_keys(key_file)
        hmac_tag = compute_hmac(test_file, hmac_key)
        
        # Check HMAC is 64 hex characters (SHA-256 in hex)
        assert isinstance(hmac_tag, str)
        assert len(hmac_tag) == 64
        assert all(c in '0123456789abcdef' for c in hmac_tag)
        
        # Check HMAC is consistent
        hmac_tag2 = compute_hmac(test_file, hmac_key)
        assert hmac_tag == hmac_tag2
        
        # Check HMAC changes when file changes
        with open(test_file, 'a') as f:
            f.write("\nmodified")
        hmac_tag3 = compute_hmac(test_file, hmac_key)
        assert hmac_tag != hmac_tag3
        
    finally:
        os.unlink(test_file)
        os.unlink(key_file)


class TestGetGitBranch:
    """Tests for get_git_branch() detection, sanitising and fallbacks."""

    @staticmethod
    def _completed(stdout, returncode=0):
        """Build a CompletedProcess-like result for subprocess.run mocks."""
        return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr="")

    def test_returns_sanitised_branch_from_git_command(self):
        """A branch containing slashes is converted into a filesystem-safe name."""
        with mock.patch("subprocess.run", return_value=self._completed("feature/add-encryption\n")):
            assert get_git_branch() == "feature-add-encryption"

    def test_strips_leading_trailing_and_collapses_dashes(self):
        """Repeated separators collapse and leading/trailing dashes are removed."""
        with mock.patch("subprocess.run", return_value=self._completed("--feature//x--\n")):
            assert get_git_branch() == "feature-x"

    def test_detached_head_uses_git_head_file(self, tmp_path, monkeypatch):
        """A detached HEAD ('HEAD') falls back to reading .git/HEAD."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/release/2.0\n")

        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", return_value=self._completed("HEAD\n")):
            assert get_git_branch() == "release-2-0"

    def test_falls_back_to_git_head_file(self, tmp_path, monkeypatch):
        """When the git command fails, .git/HEAD is used."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/fix_thing\n")

        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", return_value=self._completed("", returncode=128)):
            assert get_git_branch() == "fix_thing"

    def test_git_head_with_detached_sha_falls_back_to_main(self, tmp_path, monkeypatch):
        """A .git/HEAD holding a raw commit SHA yields the default branch."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("9fceb02d0ae598e95dc970b74767f19372d61af8\n")

        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", return_value=self._completed("", returncode=128)):
            assert get_git_branch() == "main"

    def test_empty_branch_output_falls_back_to_main(self, tmp_path, monkeypatch):
        """An empty (or whitespace-only) branch name does not leak through."""
        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", return_value=self._completed("   \n")):
            assert get_git_branch() == "main"

    def test_handles_missing_git_binary(self, tmp_path, monkeypatch):
        """FileNotFoundError (git not installed) is handled gracefully."""
        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("git")):
            assert get_git_branch() == "main"

    def test_handles_git_timeout(self, tmp_path, monkeypatch):
        """A hanging git command times out and falls back to the default."""
        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=2)):
            assert get_git_branch() == "main"

    def test_handles_unreadable_git_head(self, tmp_path, monkeypatch):
        """An unreadable .git/HEAD does not raise; the default is returned."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/broken\n")

        monkeypatch.chdir(tmp_path)
        with mock.patch("subprocess.run", return_value=self._completed("", returncode=128)), \
                mock.patch("pathlib.Path.read_text", side_effect=OSError("permission denied")):
            assert get_git_branch() == "main"

    def test_uses_real_git_command_when_available(self):
        """Without mocking, the function returns a sanitised non-empty name."""
        branch = get_git_branch()
        assert isinstance(branch, str)
        assert branch
        assert all(c.isalnum() or c in "-_" for c in branch)


def test_derive_keys_wraps_hkdf_failures():
    """An exception from HKDF.derive() is logged and re-raised unchanged."""
    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as kf:
        kf.write(b"test_master_key_for_derivation_1234567890")
        kf.flush()
        key_file = kf.name

    try:
        with mock.patch("vaulttool.utils.HKDF") as mock_hkdf:
            mock_hkdf.return_value.derive.side_effect = RuntimeError("kdf boom")
            with pytest.raises(RuntimeError, match="kdf boom"):
                derive_keys(key_file)
    finally:
        os.unlink(key_file)
