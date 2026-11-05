"""Security-focused regression tests for the vault format and key handling."""

import base64
import logging
import os
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vaulttool.cli import _write_private_file, app
from vaulttool.core import GCM_MAGIC, HMAC_HEX_LENGTH, VaultTool


@pytest.fixture(autouse=True)
def _isolate_logging():
    """Keep logging state installed by earlier CLI tests from leaking into others."""
    for name in ("vaulttool", "vaulttool.utils", "vaulttool.core"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    yield
    for name in ("vaulttool", "vaulttool.utils", "vaulttool.core"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


@pytest.fixture()
def vt(tmp_path, monkeypatch):
    """Create a VaultTool instance locked into an isolated working directory."""
    monkeypatch.chdir(tmp_path)
    key_file = tmp_path / "test.key"
    key_file.write_bytes(b"0123456789abcdef0123456789abcdef")
    (tmp_path / ".vaulttool.yml").write_text(
        f"""vaulttool:
  include_directories: ["."]
  exclude_directories: []
  include_patterns: ["*.env"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
"""
    )
    return VaultTool()


def _write_vault(vt, name="app.env", content="SECRET=1"):
    """Encrypt a file and return the resulting vault path."""
    Path(name).write_text(content)
    result = vt.encrypt_task(force=True)
    assert result["failed"] == 0
    return Path(f"{name}.vault")


class TestVaultFormat:
    """The on-disk format must be authenticated and path-bound."""

    def test_payload_uses_gcm_format(self, vt):
        """New vault files carry the v2 magic marker inside the payload."""
        vault_file = _write_vault(vt)
        payload = base64.b64decode(vault_file.read_text().splitlines()[1])
        assert payload.startswith(GCM_MAGIC)

    def test_digest_line_is_strict_hex(self, vt):
        """The first line stays a 64 character lowercase digest."""
        vault_file = _write_vault(vt)
        digest = vault_file.read_text().splitlines()[0]
        assert len(digest) == HMAC_HEX_LENGTH
        assert digest == digest.lower()

    def test_swapped_vault_files_are_rejected(self, vt):
        """A vault file moved to another source path no longer authenticates."""
        from pathlib import Path

        Path("a.env").write_text("A=1")
        Path("b.env").write_text("B=2")
        assert vt.encrypt_task(force=True)["failed"] == 0

        Path("a.env.vault").rename("swapped.tmp")
        Path("b.env.vault").rename("a.env.vault")
        Path("swapped.tmp").rename("b.env.vault")

        Path("a.env").unlink()
        Path("b.env").unlink()

        result = vt.refresh_task()
        assert result["succeeded"] == 0
        assert result["failed"] == 2
        assert not Path("a.env").exists()
        assert not Path("b.env").exists()

    def test_tampered_payload_writes_nothing(self, vt):
        """A modified ciphertext never produces plaintext on disk."""
        from pathlib import Path

        vault_file = _write_vault(vt, "tamper.env")
        lines = vault_file.read_text().splitlines()
        raw = bytearray(base64.b64decode(lines[1]))
        raw[-1] ^= 0xFF
        vault_file.write_text(lines[0] + "\n" + base64.b64encode(bytes(raw)).decode() + "\n")

        Path("tamper.env").unlink()
        result = vt.refresh_task()

        assert result["failed"] == 1
        assert not Path("tamper.env").exists()

    def test_legacy_cbc_vault_is_still_readable(self, vt):
        """Vault files written by earlier versions (AES-CBC) still decrypt."""
        from pathlib import Path

        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        from vaulttool.utils import compute_hmac

        plaintext = b"LEGACY=1"
        iv = os.urandom(16)
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()
        encryptor = Cipher(algorithms.AES(vt.encryption_key), modes.CBC(iv)).encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        Path("legacy.env").write_bytes(plaintext)
        digest = compute_hmac("legacy.env", vt.hmac_key)
        Path("legacy.env.vault").write_text(
            digest + "\n" + base64.b64encode(iv + ciphertext).decode() + "\n"
        )
        Path("legacy.env").unlink()

        result = vt.refresh_task()
        assert result["succeeded"] == 1
        assert Path("legacy.env").read_bytes() == plaintext


class TestKeyFileHandling:
    """Key files must never be readable by other users."""

    def test_write_private_file_sets_0600(self, tmp_path):
        """Files are created with owner-only permissions."""
        target = tmp_path / "new.key"
        _write_private_file(target, "secret\n")

        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_write_private_file_exclusive_refuses_overwrite(self, tmp_path):
        """Exclusive mode protects an existing key/backup from being clobbered."""
        target = tmp_path / "existing.key"
        target.write_text("original\n")

        with pytest.raises(FileExistsError):
            _write_private_file(target, "new\n", exclusive=True)

        assert target.read_text() == "original\n"

    def test_generate_key_creates_0600_key_file(self, tmp_path, monkeypatch):
        """The generate-key command creates the key with 0600 permissions."""
        monkeypatch.chdir(tmp_path)
        key_file = tmp_path / "vault.key"

        result = CliRunner().invoke(app, ["generate-key", "--key-file", str(key_file)])

        assert result.exit_code == 0
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
        assert len(key_file.read_text().strip()) == 64

    def test_loose_key_permissions_are_reported(self, tmp_path, caplog):
        """A world-readable key raises a warning during key derivation."""
        key_file = tmp_path / "loose.key"
        key_file.write_bytes(b"0123456789abcdef0123456789abcdef")
        key_file.chmod(0o644)

        with caplog.at_level(logging.WARNING, logger="vaulttool.utils"):
            from vaulttool.utils import derive_keys

            derive_keys(str(key_file))

        assert any("permissions" in record.message for record in caplog.records)
