"""End-to-end tests for the Typer command bodies in :mod:`vaulttool.cli`."""

import logging
import stat
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vaulttool.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_logging():
    """Stop CLI logging handlers from leaking between tests."""
    for name in ("vaulttool", "vaulttool.cli", "vaulttool.core", "vaulttool.utils"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    yield
    for name in ("vaulttool", "vaulttool.cli", "vaulttool.core", "vaulttool.utils"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """Create an isolated VaultTool project (config + key) and chdir into it."""
    monkeypatch.chdir(tmp_path)
    key_file = tmp_path / "vault.key"
    key_file.write_bytes(b"0123456789abcdef0123456789abcdef")
    key_file.chmod(0o600)
    (tmp_path / ".vaulttool.yml").write_text(
        f"""vaulttool:
  include_directories: ["."]
  exclude_directories: [".git"]
  include_patterns: ["*.env"]
  exclude_patterns: []
  options:
    suffix: ".vault"
    key_file: "{key_file}"
"""
    )
    (tmp_path / "app.env").write_text("SECRET=1")
    return tmp_path


@pytest.fixture()
def no_config(tmp_path, monkeypatch):
    """Working directory without any configuration file."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestVersionCommand:
    def test_prints_version(self):
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "VaultTool version" in result.output

    def test_verbose_and_quiet_warn_about_exclusivity(self):
        result = runner.invoke(app, ["--verbose", "--quiet", "version"])

        assert result.exit_code == 0
        assert "mutually exclusive" in result.output


class TestGenConfigCommand:
    def test_prints_example_configuration(self):
        result = runner.invoke(app, ["gen-vaulttool"])

        assert result.exit_code == 0
        assert "vaulttool:" in result.output
        assert "include_patterns" in result.output


class TestEncryptAndRefresh:
    def test_encrypt_creates_vault_file(self, project):
        result = runner.invoke(app, ["encrypt"])

        assert result.exit_code == 0
        assert (project / "app.env.vault").exists()
        assert "Encrypt Summary" in result.output

    def test_encrypt_quiet_prints_nothing(self, project):
        result = runner.invoke(app, ["--quiet", "encrypt"])

        assert result.exit_code == 0
        assert (project / "app.env.vault").exists()
        assert result.output.strip() == ""

    def test_encrypt_then_refresh_restores_plaintext(self, project):
        runner.invoke(app, ["encrypt", "--force"])
        (project / "app.env").unlink()

        result = runner.invoke(app, ["refresh"])

        assert result.exit_code == 0
        assert (project / "app.env").read_text() == "SECRET=1"
        assert "Refresh Summary" in result.output

    def test_refresh_no_force_skips_existing_files(self, project):
        runner.invoke(app, ["encrypt", "--force"])

        result = runner.invoke(app, ["refresh", "--no-force"])

        assert result.exit_code == 0
        assert "Skipped" in result.output

    def test_refresh_reports_tampering_and_exits_non_zero(self, project):
        runner.invoke(app, ["encrypt", "--force"])
        vault_file = project / "app.env.vault"
        lines = vault_file.read_text().splitlines()
        vault_file.write_text(lines[0] + "\n" + "A" * len(lines[1]) + "\n")
        (project / "app.env").unlink()

        result = runner.invoke(app, ["refresh"])

        assert result.exit_code == 1
        assert not (project / "app.env").exists()

    def test_encrypt_without_configuration_fails(self, no_config):
        result = runner.invoke(app, ["encrypt"])

        assert result.exit_code == 1
        assert "ERROR" in result.output


class TestRemoveCommand:
    def test_remove_deletes_vault_files(self, project):
        runner.invoke(app, ["encrypt", "--force"])
        assert (project / "app.env.vault").exists()

        result = runner.invoke(app, ["remove"])

        assert result.exit_code == 0
        assert not (project / "app.env.vault").exists()
        assert "Remove Summary" in result.output

    def test_remove_without_configuration_fails(self, no_config):
        result = runner.invoke(app, ["remove"])

        assert result.exit_code == 1


class TestCheckIgnoreCommand:
    def _init_repo(self, path: Path):
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)

    def test_exits_zero_when_everything_is_ignored(self, project):
        self._init_repo(project)
        (project / ".gitignore").write_text("*.env\n")

        result = runner.invoke(app, ["check-ignore"])

        assert result.exit_code == 0
        assert "Check Ignore Summary" in result.output

    def test_exits_non_zero_when_a_file_is_not_ignored(self, project):
        self._init_repo(project)
        (project / ".gitignore").write_text("")

        result = runner.invoke(app, ["check-ignore"])

        assert result.exit_code == 1

    def test_without_configuration_fails(self, no_config):
        result = runner.invoke(app, ["check-ignore"])

        assert result.exit_code == 1


class TestGenerateKeyCommand:
    def test_creates_key_from_option(self, no_config):
        key_file = no_config / "new.key"

        result = runner.invoke(app, ["generate-key", "--key-file", str(key_file)])

        assert result.exit_code == 0
        assert key_file.exists()
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
        assert len(key_file.read_text().strip()) == 64

    def test_uses_key_file_from_configuration(self, project):
        (project / "vault.key").unlink()

        result = runner.invoke(app, ["generate-key", "--force"])

        assert result.exit_code == 0
        assert (project / "vault.key").exists()

    def test_replaces_existing_key_and_creates_backup(self, no_config):
        key_file = no_config / "existing.key"
        key_file.write_text("0" * 64 + "\n")

        result = runner.invoke(app, ["generate-key", "--key-file", str(key_file), "--force"])

        assert result.exit_code == 0
        backups = sorted(no_config.glob("existing.key.backup_*"))
        assert len(backups) == 1
        assert backups[0].read_text().strip() == "0" * 64
        assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
        assert key_file.read_text().strip() != "0" * 64

    def test_cancels_when_user_declines(self, no_config):
        key_file = no_config / "keep.key"
        original = "1" * 64
        key_file.write_text(original + "\n")

        result = runner.invoke(app, ["generate-key", "--key-file", str(key_file)], input="n\n")

        assert result.exit_code == 0
        assert key_file.read_text().strip() == original

    def test_rekey_round_trip(self, project):
        runner.invoke(app, ["encrypt", "--force"])

        result = runner.invoke(app, ["generate-key", "--rekey", "--force"])

        assert result.exit_code == 0
        assert (project / "app.env").read_text() == "SECRET=1"
        assert (project / "app.env.vault").exists()
        assert list(project.glob("vault.key.backup_*"))
