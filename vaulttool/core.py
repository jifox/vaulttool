"""Core VaultTool functionality for secure file encryption and management.

This module contains the main VaultTool class that provides secure encryption
and management of sensitive files using OpenSSL. It handles file discovery,
encryption/decryption, and automatic .gitignore management to prevent
accidental commits of sensitive data.

The VaultTool uses a vault file format where each encrypted file contains:
- Line 1: SHA-256 checksum of the original file (for change detection)
- Line 2+: Base64-encoded encrypted content

Environment Variables:
    VAULTTOOL_PRECOMMIT: When set, prevents .gitignore modifications during
                        pre-commit hooks or CI runs.
"""

import base64
import os
from pathlib import Path
import subprocess
from .config import load_config
from .utils import compute_checksum, encode_base64

# Flag to indicate running under pre-commit/CI to avoid touching .gitignore
VAULTTOOL_PRECOMMIT: bool = bool(os.environ.get("VAULTTOOL_PRECOMMIT"))




class VaultTool:
    """A tool for encrypting and managing sensitive files using OpenSSL.
    
    VaultTool provides secure encryption of sensitive files (like configuration files
    containing secrets) and manages their encrypted counterparts. It uses OpenSSL for
    encryption and automatically handles .gitignore updates to prevent accidental
    commits of plaintext sensitive data.
    
    The tool operates on source files matching configured patterns and creates
    encrypted "vault" files with a configurable suffix. Each vault file contains
    a checksum and base64-encoded encrypted content.
    
    Attributes:
        suffix: File suffix for vault files (e.g., '.vault').
        key_file: Path to the encryption key file.
        algorithm: OpenSSL encryption algorithm (default: 'aes-256-cbc').
        openssl_path: Path to the openssl executable.
        include_directories: Directories to search for source files.
        exclude_directories: Directories to exclude from search.
        include_patterns: File patterns to include (e.g., '*.env').
        exclude_patterns: File patterns to exclude.
    """
    
    def __init__(self):
        """Initialize VaultTool with configuration from .vaulttool.yml.
        
        Loads configuration from the first found file in this order:
        1. .vaulttool.yml in current directory
        2. ~/.vaulttool/.vaulttool.yml
        3. /etc/vaulttool/config.yml
        
        Raises:
            FileNotFoundError: If no configuration file is found.
            ValueError: If configuration is invalid or missing required keys.
        """
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
        """Convert a vault file path to its corresponding source file path.
        
        Args:
            vault_path: Path to the vault file.
            suffix: The vault file suffix to remove.
            
        Returns:
            The source file path with the suffix removed. If the path doesn't
            end with the suffix, returns the original path unchanged.
            
        Example:
            >>> VaultTool.source_filename("config.env.vault", ".vault")
            "config.env"
        """
        if vault_path.endswith(suffix):
            return vault_path[: -len(suffix)]
        return vault_path  # Not a vault file; return as is

    @staticmethod
    def vault_filename(source_path: str, suffix: str) -> str:
        """Convert a source file path to its corresponding vault file path.
        
        Args:
            source_path: Path to the source file.
            suffix: The vault file suffix to append.
            
        Returns:
            The vault file path with the suffix appended.
            
        Example:
            >>> VaultTool.vault_filename("config.env", ".vault")
            "config.env.vault"
        """
        return source_path + suffix

    def encrypt_file(self, source_path: str, encrypted_path: str):
        """Encrypt a single file using OpenSSL with configured options.
        
        Uses OpenSSL command-line tool to encrypt a file with AES encryption,
        salt, and PBKDF2 key derivation for security.
        
        Args:
            source_path: Path to the plaintext file to encrypt.
            encrypted_path: Path where the encrypted file will be written.
            
        Raises:
            subprocess.CalledProcessError: If OpenSSL encryption fails.
            FileNotFoundError: If source file or key file doesn't exist.
        """
        cmd = [self.openssl_path, "enc", f"-{self.algorithm}",
            "-salt", "-pbkdf2",  # Use PBKDF2 for secure key derivation
            "-in", source_path,
            "-out", encrypted_path,
            "-pass", f"file:{self.key_file}"
        ]
        subprocess.run(cmd, check=True)

    def decrypt_file(self, encrypted_path: str, output_path: str):
        """Decrypt a single file using OpenSSL with configured options.
        
        Uses OpenSSL command-line tool to decrypt a file that was encrypted
        with the corresponding encrypt_file method.
        
        Args:
            encrypted_path: Path to the encrypted file to decrypt.
            output_path: Path where the decrypted file will be written.
            
        Raises:
            subprocess.CalledProcessError: If OpenSSL decryption fails.
            FileNotFoundError: If encrypted file or key file doesn't exist.
        """
        cmd = [self.openssl_path, "enc", "-d", f"-{self.algorithm}",
            "-pbkdf2",  # Use PBKDF2 for secure key derivation
            "-in", encrypted_path,
            "-out", output_path,
            "-pass", f"file:{self.key_file}"
        ]
        subprocess.run(cmd, check=True)

    def add_to_gitignore(self, file_path: Path):
        """Add a file to .gitignore if not already present.
        
        Ensures that sensitive source files are automatically added to .gitignore
        to prevent accidental commits. Creates .gitignore if it doesn't exist.
        
        Args:
            file_path: Path to the file to add to .gitignore.
            
        Note:
            Skips operation when VAULTTOOL_PRECOMMIT environment variable is set
            to avoid modifying .gitignore during pre-commit hooks or CI runs.
        """
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
        """Generator for all source files matching the configured patterns.
        
        Recursively searches the include directories for files matching the
        include patterns, while excluding files matching exclude patterns
        or located in exclude directories. Automatically adds found files
        to .gitignore.

        Yields:
            Path: The path to each matching source file.
            
        Note:
            Files are automatically added to .gitignore as they are discovered
            to prevent accidental commits of sensitive data.
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
        """Generator for all vault files matching the configured suffix.
        
        Recursively searches the include directories for files ending with
        the configured vault suffix.

        Yields:
            Path: The path to each vault file found.
        """
        for dir in self.include_directories:
            for vault_file in Path(dir).rglob(f"*{self.suffix}"):
                yield vault_file

    def iter_missing_sources(self):
        """Generator for source files that are missing but have corresponding vault files.
        
        Identifies vault files that exist but whose corresponding source files
        are missing. These are candidates for restoration/decryption.

        Yields:
            Path: The path where each missing source file should be located.
        """
        for vault_file in self.iter_vault_files():
            source_file = Path(self.source_filename(str(vault_file), self.suffix))
            if not source_file.exists():
                yield source_file

    def check_ignore_task(self):
        """Validate that all source files are properly ignored by Git.
        
        Iterates through all source files to ensure they are added to .gitignore.
        This is primarily used as a validation step to ensure no sensitive files
        are accidentally committed to version control.
        
        Note:
            This method currently only triggers the .gitignore addition side effect
            of iter_source_files(). Future versions may add actual validation logic.
        """
        # Just loop with iter_source_files
        for source_file in self.iter_source_files():
            pass

    def refresh_task(self, force: bool = True):
        """Decrypt and restore source files from their vault files.

        For each vault file found in the configured directories, decrypts and
        restores the corresponding source file. By default, overwrites existing
        source files.

        Args:
            force: If True, decrypt and restore source files even if they already
                   exist. If False, only restore missing source files.
                   
        Note:
            Each vault file contains a checksum on the first line and base64-encoded
            encrypted content on subsequent lines. The encrypted content is temporarily
            written to a file for OpenSSL decryption, then cleaned up.
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
        
        Processes all source files matching the configured patterns and creates
        encrypted vault files. Uses file checksums to detect changes and avoid
        unnecessary re-encryption unless forced.
        
        Args:
            force: If True, re-encrypt all files even if their checksums haven't
                   changed. If False, only encrypt new files or files that have
                   been modified since last encryption.
                   
        Note:
            Each vault file contains:
            - Line 1: SHA-256 checksum of the source file
            - Line 2+: Base64-encoded encrypted content
            
            This format allows for efficient change detection and secure storage.
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
        """Delete all vault files matching the configured suffix.
        
        Permanently removes all vault files found in the configured include
        directories. This operation cannot be undone.
        
        Note:
            Prints status messages for each file removal attempt, including
            any errors encountered during the deletion process.
            
        Warning:
            This operation permanently deletes encrypted vault files. Ensure
            you have the original source files before running this command.
        """
        for vault_file in self.iter_vault_files():
            try:
                vault_file.unlink()
                print(f"Removed vault file: {vault_file}")
            except Exception as e:
                print(f"Failed to remove {vault_file}: {e}")
