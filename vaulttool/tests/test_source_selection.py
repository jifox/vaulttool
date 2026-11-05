"""Tests for source-file selection (excludes, de-duplication) and ignore checks."""

import subprocess
from pathlib import Path

import pytest

from vaulttool.core import VaultTool

pytestmark = pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git is required for these tests",
)


def _make_vt(tmp_path, monkeypatch, **overrides):
    """Build a VaultTool for an isolated working directory."""
    monkeypatch.chdir(tmp_path)
    key_file = tmp_path / "test.key"
    key_file.write_bytes(b"0123456789abcdef0123456789abcdef")

    settings = {
        "include_directories": '["."]',
        "exclude_directories": "[]",
        "include_patterns": '["*.env"]',
        "exclude_patterns": "[]",
    }
    settings.update(overrides)

    (tmp_path / ".vaulttool.yml").write_text(
        f"""vaulttool:
  include_directories: {settings['include_directories']}
  exclude_directories: {settings['exclude_directories']}
  include_patterns: {settings['include_patterns']}
  exclude_patterns: {settings['exclude_patterns']}
  options:
    suffix: ".vault"
    key_file: "{key_file}"
"""
    )
    return VaultTool()


class TestExclusions:
    """`exclude_directories` must match whole path components only."""

    def test_excluding_dir_does_not_match_similar_names(self, tmp_path, monkeypatch):
        (tmp_path / "tests").mkdir()
        (tmp_path / "contest").mkdir()
        (tmp_path / "tests" / "a.env").write_text("A=1")
        (tmp_path / "contest" / "b.env").write_text("B=2")
        (tmp_path / "root.env").write_text("C=3")

        vt = _make_vt(tmp_path, monkeypatch, exclude_directories='["tests"]')
        names = sorted(path.name for path in vt.iter_source_files())

        assert names == ["b.env", "root.env"]

    def test_excluding_git_dir_keeps_gitignore_file(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "inside.env").write_text("G=1")
        (tmp_path / ".gitignore").write_text("root.env\n")
        (tmp_path / "root.env").write_text("R=1")

        vt = _make_vt(
            tmp_path,
            monkeypatch,
            exclude_directories='[".git"]',
            include_patterns='["*.env", ".gitignore"]',
        )
        names = sorted(path.name for path in vt.iter_source_files())

        assert names == [".gitignore", "root.env"]

    def test_nested_exclude_path_is_honoured(self, tmp_path, monkeypatch):
        (tmp_path / "vendor" / "sub").mkdir(parents=True)
        (tmp_path / "vendor" / "sub" / "x.env").write_text("X=1")
        (tmp_path / "own.env").write_text("O=1")

        vt = _make_vt(tmp_path, monkeypatch, exclude_directories='["vendor/sub"]')

        assert sorted(path.name for path in vt.iter_source_files()) == ["own.env"]


class TestDeduplication:
    """A file matched by several patterns must only be processed once."""

    def test_file_matched_by_two_patterns_is_yielded_once(self, tmp_path, monkeypatch):
        (tmp_path / "both.env.conf").write_text("B=1")

        vt = _make_vt(
            tmp_path,
            monkeypatch,
            include_patterns='["*.env", "*.conf", "*env*"]',
        )
        files = list(vt.iter_source_files())
        matches = [path for path in files if path.name == "both.env.conf"]

        assert len(matches) == 1
        assert len(files) == len(set(files))


class TestCheckIgnore:
    """`check-ignore` must really ask Git instead of mutating .gitignore."""

    def _init_repo(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    def test_reports_files_that_git_would_track(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path)
        (tmp_path / "plain.env").write_text("A=1")
        (tmp_path / "ignored.env").write_text("B=2")
        (tmp_path / ".gitignore").write_text("ignored.env\n")
        vt = _make_vt(tmp_path, monkeypatch)

        result = vt.check_ignore_task()

        assert result["total"] == 2
        assert result["ignored"] == 1
        assert [Path(p).name for p in result["not_ignored"]] == ["plain.env"]

    def test_does_not_modify_gitignore(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path)
        (tmp_path / "plain.env").write_text("A=1")
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("")
        vt = _make_vt(tmp_path, monkeypatch)

        vt.check_ignore_task()

        assert gitignore.read_text() == ""

    def test_all_ignored_when_gitignore_covers_files(self, tmp_path, monkeypatch):
        self._init_repo(tmp_path)
        (tmp_path / "a.env").write_text("A=1")
        (tmp_path / ".gitignore").write_text("*.env\n")
        vt = _make_vt(tmp_path, monkeypatch)

        result = vt.check_ignore_task()

        assert result["not_ignored"] == []
        assert result["ignored"] == result["total"] == 1
