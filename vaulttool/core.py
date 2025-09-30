import base64
from logging import config
import os
from pathlib import Path
import subprocess
from .config import load_config
from .utils import compute_checksum, encode_base64

# Flag to indicate running under pre-commit/CI to avoid touching .gitignore
VAULTTOOL_PRECOMMIT: bool = bool(os.environ.get("VAULTTOOL_PRECOMMIT"))




class VaultTool:
    def __init__(self):
        config = load_config()
        options = config.get("options", {})
        self.suffix = options.get("suffix", ".vault")
        if self.suffix and "." not in self.suffix:
            raise ValueError("Suffix must contain a dot (e.g., .vault, prod.vault)")
        self.key_file = options.get("key_file")
        self.algorithm = options.get("algorithm", "aes-256-cbc")
        self.openssl_path = options.get("openssl_path", "openssl")
        self.include_directories = config.get("include_directories", ["." ])
        self.exclude_directories = set(config.get("exclude_directories", []))
        self.include_patterns = config.get("include_patterns", [])
        self.exclude_patterns = set(config.get("exclude_patterns", []))

    @staticmethod
    def source_filename(vault_path: str, suffix: str) -> str:
        """Return the source filename for a given vault file and suffix."""
        if vault_path.endswith(suffix):
            return vault_path[: -len(suffix)]
        return vault_path  # Not a vault file; return as is

    @staticmethod
    def vault_filename(source_path: str, suffix: str) -> str:
        """Return the vault filename for a given source file and suffix."""
        return source_path + suffix

    def encrypt_file(self, source_path: str, encrypted_path: str):
        """Encrypt a file using OpenSSL with the configured options."""
        cmd = [self.openssl_path, "enc", f"-{self.algorithm}",
            "-salt", "-pbkdf2",  # Use PBKDF2 for secure key derivation
            "-in", source_path,
            "-out", encrypted_path,
            "-pass", f"file:{self.key_file}"
        ]
        subprocess.run(cmd, check=True)

    def decrypt_file(self, encrypted_path: str, output_path: str):
        """Decrypt a file using OpenSSL with the configured options."""
        cmd = [self.openssl_path, "enc", "-d", f"-{self.algorithm}",
            "-pbkdf2",  # Use PBKDF2 for secure key derivation
            "-in", encrypted_path,
            "-out", output_path,
            "-pass", f"file:{self.key_file}"
        ]
        subprocess.run(cmd, check=True)

    def add_to_gitignore(self, file_path: Path):
        """Add a file to .gitignore if not already present."""
        if VAULTTOOL_PRECOMMIT and (Path(".git").exists()):
            return  # Avoid touching .gitignore in pre-commit/CI runs
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            gitignore_path.touch()
        with open(gitignore_path, "r", encoding="utf-8") as gi:
            gitignore_lines = set(line.strip() for line in gi if line.strip())
        rel_path = os.path.relpath(file_path, Path().absolute())
        if rel_path not in gitignore_lines:
            with open(gitignore_path, "a", encoding="utf-8") as gi:
                gi.write(f"{rel_path}\n")
            print(f"Added {rel_path} to .gitignore")

    def iter_source_files(self):
        """Generator yielding all source files.

        Yields:
            Path: The path to each source file.
        """
        for dir in self.include_directories:
            for pattern in self.include_patterns:
                for source_file in Path(dir).rglob(pattern):
                    if any(source_file.match(ex_pat) for ex_pat in self.exclude_patterns):
                        continue
                    if any(ex_dir in str(source_file) for ex_dir in self.exclude_directories):
                        continue
                    self.add_to_gitignore(source_file)
                    yield source_file

    def iter_vault_files(self):
        """Generator yielding all vault files."""
        for dir in self.include_directories:
            for vault_file in Path(dir).rglob(f"*{self.suffix}"):
                yield vault_file

    def iter_missing_sources(self):
        """Generator yielding source files that are missing but have corresponding vault files."""
        for vault_file in self.iter_vault_files():
            source_file = Path(self.source_filename(str(vault_file), self.suffix))
            if not source_file.exists():
                yield source_file

    def check_ignore_task(self):
        """Add check for unignored plaintext files that should be ignored."""
        # Just loop with iter_source_files
        for source_file in self.iter_source_files():
            pass

    def refresh_task(self, force: bool = True):
        """Decrypt and restore missing source files from their vault files.

        For each .vault file found in the configured directories, if the corresponding source file does not exist,
        decrypt the .vault file and restore the source file using OpenSSL and the configured key.

        Args:
            force (bool): If True, decrypt and restore the source file even if it already exists
        """
        for vault_file in self.iter_vault_files():
            source_file = Path(self.source_filename(str(vault_file), self.suffix))
            if source_file.exists() and not force:
                continue
            # Read the base64 content from vault file and decode it
            with open(vault_file, "r", encoding="utf-8") as vf:
                lines = vf.readlines()
                if len(lines) < 2:
                    continue
                encrypted_b64 = lines[1].strip()
            import base64
            encrypted_data = base64.b64decode(encrypted_b64)
            # Write to temp file and decrypt
            temp_path = str(vault_file) + ".tmp"
            with open(temp_path, "wb") as tf:
                tf.write(encrypted_data)
            self.decrypt_file(temp_path, str(source_file))
            os.remove(temp_path)
            print(f"Decrypted {vault_file} to restore missing source file {source_file}")

    def encrypt_task(self, force: bool = False):
        """Encrypt all source files to their corresponding vault files.
        
        Args:
            force (bool): If True, re-encrypt even if the checksum hasn't changed
        """
        for source_file in self.iter_source_files():
            vault_file = Path(self.vault_filename(str(source_file), self.suffix))
            checksum = compute_checksum(source_file)
            vault_checksum = None
            if vault_file.exists():
                with open(vault_file, "r", encoding="utf-8") as vf:
                    first_line = vf.readline().strip()
                    vault_checksum = first_line if first_line else None
            if not vault_file.exists() or checksum != vault_checksum or force:
                # Encrypt file to temp, then encode and write .vault file
                self.encrypt_file(str(source_file), str(vault_file) + ".tmp")
                with open(str(vault_file) + ".tmp", "rb") as ef:
                    encoded = encode_base64(ef.read()).decode()
                os.remove(str(vault_file) + ".tmp")
                with open(vault_file, "w", encoding="utf-8") as vf:
                    vf.write(checksum + "\n" + encoded + "\n")
                action = "Updated" if vault_file.exists() else "Created"
                print(f"{action} vault file: {vault_file} for source: {source_file}")


    def remove_task(self):
        """Delete all vault files matching the configured suffix in the include directories."""
        for vault_file in self.iter_vault_files():
            try:
                vault_file.unlink()
                print(f"Removed vault file: {vault_file}")
            except Exception as e:
                print(f"Failed to remove {vault_file}: {e}")
