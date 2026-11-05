"""Failure-path tests for :mod:`vaulttool.cli`.

These tests inject faults into the task calls so that the error handling of
every command is exercised (the happy paths live in ``test_cli_commands.py``).
"""

import logging

import pytest
import typer
from typer.testing import CliRunner

import vaulttool.cli as cli
from vaulttool.cli import Ui, app

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
def no_config(tmp_path, monkeypatch):
    """Working directory without configuration (commands never reach the config)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _stub_vaulttool(monkeypatch, **tasks):
    """Replace ``vaulttool.cli.VaultTool`` with a stub exposing ``tasks``.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        **tasks: Mapping of method name to a callable used for that task.

    Returns:
        The stub class.
    """

    class StubVaultTool:
        def __init__(self, *args, **kwargs):
            pass

    for name, func in tasks.items():
        setattr(StubVaultTool, name, (lambda f: lambda self, *a, **k: f(*a, **k))(func))
    monkeypatch.setattr(cli, "VaultTool", StubVaultTool)
    return StubVaultTool


def _result(**overrides):
    """Build a task-result dictionary with sensible defaults."""
    result = {"total": 1, "succeeded": 0, "failed": 0, "skipped": 0, "created": 0, "updated": 0, "removed": 0, "errors": []}
    result.update(overrides)
    return result


class TestUiHelper:
    """The console helper must handle empty input gracefully."""

    def test_summary_without_rows_only_prints_heading(self):
        messages = []
        ui = Ui(quiet=False)
        ui.say = messages.append  # type: ignore[method-assign]

        ui.summary("Empty:", [])

        assert messages == ["\n" + "=" * 60, "Empty:", "=" * 60]


class TestGenerateKeyConfigErrors:
    def test_config_without_key_file(self, no_config, monkeypatch):
        monkeypatch.setattr("vaulttool.config.load_config", lambda *a, **k: {"options": {}})

        result = runner.invoke(app, ["generate-key"])

        assert result.exit_code == 1
        assert "No key_file specified" in result.output

    def test_unreadable_configuration(self, no_config, monkeypatch):
        def boom(*args, **kwargs):
            raise ValueError("broken yaml")

        monkeypatch.setattr("vaulttool.config.load_config", boom)

        result = runner.invoke(app, ["generate-key"])

        assert result.exit_code == 1
        assert "Cannot load configuration" in result.output


class TestGenerateKeyPrompts:
    def _existing_key(self, path):
        key = path / "vault.key"
        key.write_text("0" * 64 + "\n")
        return key

    def test_rekey_warning_is_shown_when_not_forced(self, no_config):
        key = self._existing_key(no_config)

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey"], input="n\n"
        )

        assert result.exit_code == 0
        assert "DESTRUCTIVE operation" in result.output
        assert "Operation cancelled." in result.output
        assert key.read_text().strip() == "0" * 64

    def test_abort_at_prompt_cancels_cleanly(self, no_config, monkeypatch):
        key = self._existing_key(no_config)

        def abort(*args, **kwargs):
            raise typer.Abort()

        monkeypatch.setattr(typer, "confirm", abort)

        result = runner.invoke(app, ["generate-key", "--key-file", str(key)])

        assert result.exit_code == 0
        assert "Operation cancelled." in result.output
        assert key.read_text().strip() == "0" * 64


class TestGenerateKeyRekeyFailures:
    def _key(self, path):
        key = path / "vault.key"
        key.write_text("0" * 64 + "\n")
        return key

    def test_refresh_failure_aborts_rekey(self, no_config, monkeypatch):
        key = self._key(no_config)
        _stub_vaulttool(monkeypatch, refresh_task=lambda **k: _result(failed=1, total=1))

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 1
        assert "Failed to restore some files" in result.output

    def test_refresh_exception_aborts_rekey(self, no_config, monkeypatch):
        key = self._key(no_config)

        def boom(**kwargs):
            raise RuntimeError("refresh exploded")

        _stub_vaulttool(monkeypatch, refresh_task=boom)

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 1
        assert "ERROR during refresh" in result.output

    def test_remove_failure_is_reported(self, no_config, monkeypatch):
        key = self._key(no_config)
        _stub_vaulttool(
            monkeypatch,
            refresh_task=lambda **k: _result(succeeded=1, total=1),
            remove_task=lambda: _result(removed=0, failed=1),
            encrypt_task=lambda **k: _result(created=1, updated=0),
        )

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 0
        assert "Failed: 1 files" in result.output

    def test_remove_exception_aborts_rekey(self, no_config, monkeypatch):
        key = self._key(no_config)

        def boom():
            raise OSError("remove exploded")

        _stub_vaulttool(
            monkeypatch,
            refresh_task=lambda **k: _result(succeeded=1, total=1),
            remove_task=boom,
        )

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 1
        assert "ERROR during remove" in result.output

    def test_encrypt_failure_is_reported(self, no_config, monkeypatch):
        key = self._key(no_config)
        _stub_vaulttool(
            monkeypatch,
            refresh_task=lambda **k: _result(succeeded=1, total=1),
            remove_task=lambda: _result(removed=1, total=1),
            encrypt_task=lambda **k: _result(created=0, updated=0, failed=1),
        )

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 1
        assert "Some files failed to encrypt" in result.output

    def test_encrypt_exception_is_reported(self, no_config, monkeypatch):
        key = self._key(no_config)

        def boom(**kwargs):
            raise RuntimeError("encrypt exploded")

        _stub_vaulttool(
            monkeypatch,
            refresh_task=lambda **k: _result(succeeded=1, total=1),
            remove_task=lambda: _result(removed=1, total=1),
            encrypt_task=boom,
        )

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--rekey", "--force"]
        )

        assert result.exit_code == 1
        assert "ERROR during encryption" in result.output


class TestGenerateKeyKeyFileFailures:
    def _key(self, path):
        key = path / "vault.key"
        key.write_text("0" * 64 + "\n")
        return key

    def test_backup_failure_exits(self, no_config, monkeypatch):
        key = self._key(no_config)

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(cli, "_write_private_file", boom)

        result = runner.invoke(app, ["generate-key", "--key-file", str(key), "--force"])

        assert result.exit_code == 1
        assert "Failed to backup old key" in result.output

    def test_new_key_write_failure_mentions_backup(self, no_config, monkeypatch):
        key = self._key(no_config)
        calls = {"count": 0}
        original = cli._write_private_file

        def flaky(path, content, exclusive=False):
            calls["count"] += 1
            if calls["count"] > 1:  # first call writes the backup
                raise OSError("read-only key")
            return original(path, content, exclusive=exclusive)

        monkeypatch.setattr(cli, "_write_private_file", flaky)

        result = runner.invoke(app, ["generate-key", "--key-file", str(key), "--force"])

        assert result.exit_code == 1
        assert "Failed to write new key" in result.output
        assert "Old key backup is safe at" in result.output


class TestGenerateKeyUnexpectedErrors:
    def _existing_key(self, path):
        key = path / "vault.key"
        key.write_text("0" * 64 + "\n")
        return key

    def test_keyboard_interrupt_exits_cleanly(self, no_config, monkeypatch):
        key = self._existing_key(no_config)

        def interrupt(*args, **kwargs):
            raise KeyboardInterrupt()

        monkeypatch.setattr(cli, "_write_private_file", interrupt)

        result = runner.invoke(
            app, ["generate-key", "--key-file", str(key), "--force"]
        )

        assert result.exit_code == 1
        assert "Operation cancelled by user" in result.output

    def test_unexpected_exception_is_logged(self, no_config, monkeypatch):
        key = self._existing_key(no_config)

        def boom(*args, **kwargs):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(typer, "confirm", boom)

        result = runner.invoke(app, ["generate-key", "--key-file", str(key)])

        assert result.exit_code == 1
        assert "ERROR: unexpected" in result.output


class TestTaskCommandsFailures:
    """remove/encrypt/refresh/check-ignore must exit non-zero on task failures."""

    def test_remove_reports_failure(self, no_config, monkeypatch):
        _stub_vaulttool(monkeypatch, remove_task=lambda: _result(removed=0, failed=1))

        result = runner.invoke(app, ["remove"])

        assert result.exit_code == 1
        assert "Remove Summary" in result.output

    def test_remove_exception(self, no_config, monkeypatch):
        def boom():
            raise OSError("nope")

        _stub_vaulttool(monkeypatch, remove_task=boom)

        result = runner.invoke(app, ["remove"])

        assert result.exit_code == 1
        assert "ERROR: nope" in result.output

    def test_encrypt_reports_failure(self, no_config, monkeypatch):
        _stub_vaulttool(monkeypatch, encrypt_task=lambda **k: _result(failed=1))

        result = runner.invoke(app, ["encrypt"])

        assert result.exit_code == 1
        assert "Encrypt Summary" in result.output

    def test_encrypt_exception(self, no_config, monkeypatch):
        def boom(**kwargs):
            raise OSError("nope")

        _stub_vaulttool(monkeypatch, encrypt_task=boom)

        result = runner.invoke(app, ["encrypt"])

        assert result.exit_code == 1
        assert "ERROR: nope" in result.output

    def test_refresh_reports_failure(self, no_config, monkeypatch):
        _stub_vaulttool(monkeypatch, refresh_task=lambda **k: _result(failed=1))

        result = runner.invoke(app, ["refresh"])

        assert result.exit_code == 1
        assert "Refresh Summary" in result.output

    def test_refresh_exception(self, no_config, monkeypatch):
        def boom(**kwargs):
            raise OSError("nope")

        _stub_vaulttool(monkeypatch, refresh_task=boom)

        result = runner.invoke(app, ["refresh"])

        assert result.exit_code == 1
        assert "ERROR: nope" in result.output

    def test_check_ignore_exception(self, no_config, monkeypatch):
        def boom():
            raise OSError("git missing")

        _stub_vaulttool(monkeypatch, check_ignore_task=boom)

        result = runner.invoke(app, ["check-ignore"])

        assert result.exit_code == 1
        assert "ERROR: git missing" in result.output
