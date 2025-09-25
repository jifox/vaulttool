import os
import tempfile
import shutil
from pathlib import Path
import pytest
from vaulttool.core import remove_vault_files

def test_remove_vault_files():
	with tempfile.TemporaryDirectory() as tmpdir:
		# Setup: create some vault files and some non-vault files
		suffix = ".vault"
		files = ["a.txt", "b.env", "c.json"]
		vault_files = [f + suffix for f in files]
		for vf in vault_files:
			Path(tmpdir, vf).write_text("vaulted")
		# Also create a non-vault file
		Path(tmpdir, "notvaulted.txt").write_text("plain")
		config = {
			"include_directories": [tmpdir],
			"options": {"suffix": suffix},
		}
		removed = remove_vault_files(config)
		# All vault files should be removed
		for vf in vault_files:
			assert not Path(tmpdir, vf).exists()
		# Non-vault file should remain
		assert Path(tmpdir, "notvaulted.txt").exists()
		# The removed list should match the vault files
		assert set(os.path.basename(f) for f in removed) == set(vault_files)
