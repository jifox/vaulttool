"""Core VaultTool functionality for secure file encryption and management.

This module contains the main VaultTool class that provides secure encryption
and management of sensitive files using AES-256-CBC. It handles file discovery,
encryption/decryption, and automatic .gitignore management to prevent
accidental commits of sensitive data.

The VaultTool uses a vault file format where each encrypted file contains:
- Line 1: HMAC-SHA256 authentication tag of the original file (for integrity)
- Line 2+: Base64-encoded encrypted content (IV + ciphertext)

The HMAC key and encryption key are derived from the master key file using
HKDF (HMAC-based Key Derivation Function) for cryptographic separation.
Encryption uses AES-256-CBC with randomly generated IVs and PKCS7 padding.

Environment Variables:
    VAULTTOOL_PRECOMMIT: When set, prevents .gitignore modifications during
                        pre-commit hooks or CI runs.
"""

import base64
import binascii
import hmac
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import load_config
from .utils import compute_hmac, compute_hmac_bytes, derive_keys, encode_base64

logger = logging.getLogger(__name__)

# Flag to indicate running under pre-commit/CI to avoid touching .gitignore
VAULTTOOL_PRECOMMIT: bool = bool(os.environ.get("VAULTTOOL_PRECOMMIT"))

# Maximum file size to prevent memory exhaustion (100MB)
MAX_FILE_SIZE: int = 100 * 1024 * 1024

#: Default vault suffix used when the configuration does not define one.
DEFAULT_SUFFIX: str = ".vault"

#: Marker that identifies a v2 (AES-GCM) encrypted payload.
GCM_MAGIC: bytes = b"VT2\x01"

#: AES-GCM nonce size in bytes (96-bit nonce, as recommended for GCM).
GCM_NONCE_SIZE: int = 12

#: AES-GCM authentication tag size in bytes.
GCM_TAG_SIZE: int = 16

#: IV size used by the legacy AES-CBC payload format.
LEGACY_IV_SIZE: int = 16

#: AES block size in bytes.
AES_BLOCK_SIZE: int = 16

#: Smallest payload that can carry a complete v2 (magic + nonce + tag) record.
MIN_ENCRYPTED_SIZE: int = 32

#: Length of a hexadecimal SHA-256 HMAC.
HMAC_HEX_LENGTH: int = 64

#: Strict format of a vault file's authentication digest line.
HMAC_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")


class VaultTool:
    """A tool for encrypting and managing sensitive files using AES-256-CBC.

    VaultTool provides secure encryption of sensitive files (like configuration files
    containing secrets) and manages their encrypted counterparts. It uses pure Python
    cryptography with AES-256-CBC encryption and automatically handles .gitignore
    updates to prevent accidental commits of plaintext sensitive data.

    The tool operates on source files matching configured patterns and creates
    encrypted "vault" files with a configurable suffix. Each vault file contains
    an HMAC authentication tag and base64-encoded encrypted content (IV + ciphertext).

    Keys are derived from a master key file using HKDF (HMAC-based Key Derivation
    Function) to provide cryptographic separation between authentication (HMAC) and
    encryption operations. Each encryption operation uses a randomly generated IV
    for semantic security.

    Attributes:
        suffix: File suffix for vault files (e.g., '.vault').
        key_file: Path to the master encryption key file.
        algorithm: Encryption algorithm (for backward compatibility, not used).
        openssl_path: Path to openssl (for backward compatibility, not used).
        include_directories: Directories to search for source files.
        exclude_directories: Directories to exclude from search.
        include_patterns: File patterns to include (e.g., '*.env').
        exclude_patterns: File patterns to exclude.
        hmac_key: Derived HMAC key for authentication (32 bytes).
        encryption_key: Derived encryption key for AES-256 (32 bytes).
    """

    def __init__(self):
        """Initialize VaultTool with configuration from .vaulttool.yml.

        Loads configuration from the first found file in this order:
        1. .vaulttool.yml in current directory
        2. ~/.vaulttool/.vaulttool.yml
        3. /etc/vaulttool/config.yml

        Derives HMAC and encryption keys from the master key file using HKDF
        for cryptographic separation between authentication and encryption.

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
        self.use_suffix_fallback = options.get("use_suffix_fallback", True)  # Default: enabled for flexible vault discovery
        self.include_directories = config.get("include_directories", ["." ])
        self.exclude_directories = set(config.get("exclude_directories", []))
        self.include_patterns = config.get("include_patterns", [])
        self.exclude_patterns = set(config.get("exclude_patterns", []))

        # Set up logger for this instance
        self.logger = logger

        # Derive HMAC and encryption keys from master key using HKDF
        self.hmac_key, self.encryption_key = derive_keys(self.key_file)

    def _validate_file_path(self, file_path: str, require_exists: bool = True) -> Path:
        """Validate and resolve a file path for security.

        Prevents path traversal attacks, symlink following, and access to files
        outside the current working directory.

        Args:
            file_path: Path to validate.
            require_exists: If True, file must exist.

        Returns:
            Resolved Path object.

        Raises:
            ValueError: If path is invalid, unsafe, or outside working directory.
            FileNotFoundError: If file doesn't exist (when require_exists=True).
        """
        file_path_obj = Path(file_path)

        # Check for symlinks BEFORE resolving (to catch symlink itself)
        if file_path_obj.exists() and file_path_obj.is_symlink():
            raise ValueError(f"Symlinks not allowed for security: {file_path}")

        # Now resolve the path
        try:
            if require_exists:
                resolved = file_path_obj.resolve(strict=True)
            else:
                resolved = file_path_obj.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            self.logger.debug(f"Path resolution failed for '{file_path}': {e}", exc_info=True)
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e

        # Check file is within current working directory
        cwd = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd)
        except ValueError:
            raise ValueError(f"File path outside working directory: {file_path}")

        # Check it's a regular file (not directory, device, socket, etc.)
        if resolved.exists():
            if not resolved.is_file():
                raise ValueError(f"Path is not a regular file: {file_path}")

        return resolved

    def _is_valid_hmac(self, hmac_str: str) -> bool:
        """Validate HMAC string format (64 hex characters for SHA-256).

        Args:
            hmac_str: HMAC string to validate.

        Returns:
            True if valid HMAC format, False otherwise.
        """
        if not hmac_str or len(hmac_str) != HMAC_HEX_LENGTH:
            return False
        return HMAC_HEX_PATTERN.fullmatch(hmac_str.lower()) is not None

    @staticmethod
    def _path_aad(path: Union[str, Path]) -> bytes:
        """Build additional authenticated data that binds a payload to a path.

        The path is normalised relative to the current working directory so that
        vault files stay portable between machines (no absolute paths are baked
        into the ciphertext) while still being bound to their logical location.

        Args:
            path: Logical path of the plaintext file.

        Returns:
            The UTF-8 encoded POSIX-style relative path.
        """
        candidate = Path(path)
        try:
            relative = candidate.resolve().relative_to(Path.cwd().resolve())
        except (OSError, ValueError):
            relative = candidate
        return relative.as_posix().encode("utf-8")

    @staticmethod
    def _write_bytes_atomically(path: Path, data: bytes) -> None:
        """Write ``data`` to ``path`` using a temporary file and an atomic rename.

        Prevents a crash or a full disk from leaving a half-written file behind,
        and keeps the permissions of an existing file (or 0600 for new ones).

        Args:
            path: Destination path.
            data: Bytes to write.
        """
        path = Path(path)
        mode = None
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            mode = None

        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if mode is not None:
                os.chmod(tmp_name, mode)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    @staticmethod
    def source_filename(vault_path: str, suffix: str) -> str:
        """Convert a vault file path to its corresponding source file path.

        Removes the vault suffix from the file path to determine the original source file.

        Args:
            vault_path: Path to the vault file.
            suffix: The vault file suffix to remove.

        Returns:
            The source file path with the suffix removed.
            If the path doesn't end with the suffix, returns the original path unchanged.

        Example:
            >>> VaultTool.source_filename("config.env.vault", ".vault")
            "config.env"
            >>> VaultTool.source_filename("config.env.secret.vault", ".secret.vault")
            "config.env"
        """
        if not vault_path.endswith(suffix):
            return vault_path  # Not a vault file; return as is

        # Remove the suffix
        return vault_path[:-len(suffix)]

    def vault_filename(self, source_path: str, suffix: str | None = None) -> str:
        """Convert a source file path to its corresponding vault file path.

        Creates a vault filename by appending the configured suffix to the source path.

        Args:
            source_path: Path to the source file.
            suffix: The vault file suffix to append. If None, uses self.suffix.

        Returns:
            The vault file path with suffix appended.

        Example:
            >>> vt.vault_filename("config.env")  # suffix=".vault"
            "config.env.vault"
            >>> vt.vault_filename("config.env")  # suffix=".secret.vault"
            "config.env.secret.vault"
        """
        if suffix is None:
            suffix = self.suffix

        # Simple suffix appending
        return f"{source_path}{suffix}"

    def infer_vault_suffix(self, vault_path: str) -> str | None:
        """Infer the actual vault suffix from a vault file path.

        When fallback is enabled, vault files might have different suffixes than the current
        configured suffix. This method attempts to determine the actual suffix by checking
        if the file ends with ".vault" but not with the current suffix.

        Strategy: Since all suffixes must end with ".vault", when a file doesn't match the
        current suffix but ends with ".vault", we infer the suffix while accounting for
        common file extensions (.env, .ini, .yaml, etc.).

        Args:
            vault_path: Path to the vault file to analyze.

        Returns:
            The inferred suffix (e.g., ".prod.vault", "_n3test.vault") or None if unable to infer.

        Example:
            >>> vt.infer_vault_suffix("development/creds.env.prod.vault")
            ".prod.vault"
        """
        if not isinstance(vault_path, str):
            vault_path = str(vault_path)

        # If the file already matches the current suffix, return it
        if vault_path.endswith(self.suffix):
            return self.suffix

        # If fallback is enabled and file ends with .vault, we need to infer the suffix
        if self.use_suffix_fallback and vault_path.endswith(".vault"):
            # Remove ".vault" to get the base filename
            base = vault_path[:-6]  # Remove ".vault"
            
            # Common file extensions that are NOT part of the vault suffix
            # These are file extensions that come BEFORE the vault suffix
            COMMON_EXTENSIONS = {
                '.env', '.ini', '.yaml', '.yml', '.json', '.conf', '.cfg',
                '.config', '.secret', '.txt', '.log', '.properties', '.cnf'
            }
            
            # Check if the base ends with a common file extension
            for ext in COMMON_EXTENSIONS:
                if base.endswith(ext):
                    # The file extension is part of the filename, not the vault suffix
                    # So the vault suffix is just ".vault"
                    logger.debug(f"Detected common file extension {ext!r} in {vault_path!r}, using .vault as suffix")
                    return ".vault"
            
            # No common extension found, so try to find a custom suffix
            # Look for the last dot or underscore that could mark the start of a custom suffix
            last_dot_idx = base.rfind(".")
            last_underscore_idx = base.rfind("_")
            
            # Take the last occurrence of either dot or underscore
            split_idx = max(last_dot_idx, last_underscore_idx)
            
            if split_idx >= 0:
                # Found a dot or underscore, so custom suffix is from that position to ".vault"
                inferred_suffix = base[split_idx:] + ".vault"
                logger.debug(f"Inferred vault suffix {inferred_suffix!r} for file {vault_path!r}")
                return inferred_suffix
            else:
                # No dot or underscore found in base, so suffix is just ".vault"
                return ".vault"

        return None

    def encrypt_file(self, source_path: str, encrypted_path: str, aad: Optional[bytes] = None):
        """Encrypt a single file using AES-256-GCM with the derived encryption key.

        Every encryption uses a fresh random 96-bit nonce. The payload is
        authenticated (AEAD), so tampering is detected *before* any plaintext
        is produced. An optional ``aad`` (additional authenticated data) binds
        the ciphertext to its logical location, which prevents a vault file
        from being silently swapped with another one.

        Args:
            source_path: Path to the plaintext file to encrypt.
            encrypted_path: Path where the encrypted file will be written.
            aad: Optional additional authenticated data (e.g. the source path).

        Raises:
            IOError: If source file cannot be read or encrypted file cannot be written.
            ValueError: If file paths are invalid, outside working directory, or too large.

        Note:
            Output format: magic (4) + nonce (12) + ciphertext + tag (16).
        """
        logger.debug("Encrypting file: %s -> %s", source_path, encrypted_path)

        # Validate source path for security (must exist and be within workspace)
        source = self._validate_file_path(source_path, require_exists=True)

        # For encrypted_path, just ensure parent directory exists
        # (we don't validate it against workspace since it's output)
        encrypted = Path(encrypted_path).resolve()
        if not encrypted.parent.exists():
            raise ValueError(f"Parent directory does not exist: {encrypted.parent}")

        # Check file size to prevent memory exhaustion
        file_size = source.stat().st_size
        logger.debug("Source file size: %s bytes", file_size)
        if file_size > MAX_FILE_SIZE:
            logger.error("File too large: %s bytes (maximum %s bytes)", file_size, MAX_FILE_SIZE)
            raise ValueError(
                f"File too large: {file_size} bytes "
                f"(maximum {MAX_FILE_SIZE} bytes / {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            )

        with open(source, "rb") as f:
            plaintext = f.read()

        payload = self._encrypt_payload(plaintext, aad)

        # Validate encrypted output
        encrypted_size = len(payload)
        if encrypted_size < MIN_ENCRYPTED_SIZE:  # < 32: magic + nonce + tag truncated
            logger.error("Encrypted output suspiciously small: %s bytes", encrypted_size)
            raise ValueError(
                f"Encrypted output suspiciously small: {encrypted_size} bytes "
                f"(minimum {MIN_ENCRYPTED_SIZE})"
            )

        logger.debug("Encrypted %s bytes -> %s bytes", file_size, encrypted_size)

        with open(encrypted_path, "wb") as f:
            f.write(payload)

        logger.debug("Successfully wrote encrypted file: %s", encrypted_path)

    def _encrypt_payload(self, plaintext: bytes, aad: Optional[bytes] = None) -> bytes:
        """Encrypt in-memory plaintext into a self-describing v2 payload.

        Args:
            plaintext: Bytes to encrypt.
            aad: Optional additional authenticated data.

        Returns:
            ``magic + nonce + ciphertext + tag``.
        """
        nonce = os.urandom(GCM_NONCE_SIZE)
        ciphertext_and_tag = AESGCM(self.encryption_key).encrypt(nonce, plaintext, aad)
        return GCM_MAGIC + nonce + ciphertext_and_tag

    def _decrypt_payload(self, payload: bytes, aad: Optional[bytes] = None) -> bytes:
        """Decrypt a v2 payload or a legacy AES-CBC payload.

        The v2 format is authenticated before any plaintext is returned, so a
        tampered vault file never produces usable output. Legacy (v1) payloads
        are decrypted with AES-CBC; callers are responsible for verifying the
        HMAC line, which :meth:`refresh_task` does before writing to disk.

        Args:
            payload: Raw payload bytes read from a vault/temporary file.
            aad: Additional authenticated data used when the file was encrypted.

        Returns:
            The decrypted plaintext.

        Raises:
            ValueError: If the payload is malformed, truncated, or fails authentication.
        """
        if payload.startswith(GCM_MAGIC):
            return self._decrypt_v2_payload(payload, aad)
        return self._decrypt_legacy_payload(payload)

    def _decrypt_v2_payload(self, payload: bytes, aad: Optional[bytes] = None) -> bytes:
        """Decrypt an AES-256-GCM payload, raising ``ValueError`` on failure."""
        if len(payload) < len(GCM_MAGIC) + GCM_NONCE_SIZE + GCM_TAG_SIZE:
            raise ValueError(
                f"Encrypted file is too short for the v2 format: {len(payload)} bytes"
            )

        nonce_start = len(GCM_MAGIC)
        nonce = payload[nonce_start:nonce_start + GCM_NONCE_SIZE]
        ciphertext_and_tag = payload[nonce_start + GCM_NONCE_SIZE:]

        try:
            return AESGCM(self.encryption_key).decrypt(nonce, ciphertext_and_tag, aad)
        except InvalidTag as e:
            logger.error("Authentication failed for encrypted payload (invalid GCM tag)")
            raise ValueError(
                "Authentication failed: the vault file was modified or was created "
                "for a different file path"
            ) from e

    def _decrypt_legacy_payload(self, payload: bytes) -> bytes:
        """Decrypt a legacy AES-256-CBC payload (IV + ciphertext)."""
        if len(payload) < LEGACY_IV_SIZE:
            logger.error("Encrypted file too short: %s bytes (missing IV)", len(payload))
            raise ValueError(f"Encrypted file is too short (missing IV): {len(payload)} bytes")

        if len(payload) == LEGACY_IV_SIZE:
            logger.error("Encrypted file contains no ciphertext (only IV)")
            raise ValueError("Encrypted file contains no ciphertext (only IV)")

        ciphertext_len = len(payload) - LEGACY_IV_SIZE
        if ciphertext_len % AES_BLOCK_SIZE != 0:
            logger.error("Invalid ciphertext length: %s bytes (not multiple of 16)", ciphertext_len)
            raise ValueError(
                f"Invalid ciphertext length: {ciphertext_len} bytes "
                f"(not multiple of {AES_BLOCK_SIZE}-byte block size)"
            )

        iv = payload[:LEGACY_IV_SIZE]
        ciphertext = payload[LEGACY_IV_SIZE:]

        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = sym_padding.PKCS7(128).unpadder()
        return unpadder.update(padded_plaintext) + unpadder.finalize()

    def decrypt_file(self, encrypted_path: str, output_path: str, aad: Optional[bytes] = None):
        """Decrypt a single file, authenticating it before anything is written.

        The payload is decrypted in memory first. For v2 (AES-GCM) payloads the
        authentication tag is verified by :mod:`cryptography` before the
        plaintext is returned, so a tampered file can never produce output on
        disk. Legacy AES-CBC payloads are decrypted in memory as well; callers
        must verify the vault HMAC line before trusting the result.

        Args:
            encrypted_path: Path to the encrypted file to decrypt.
            output_path: Path where the decrypted file will be written.
            aad: Additional authenticated data used when the file was encrypted.

        Raises:
            IOError: If the encrypted file cannot be read or the output cannot be written.
            ValueError: If the encrypted file is malformed or authentication fails.
        """
        logger.debug("Decrypting file: %s -> %s", encrypted_path, output_path)

        # Validate encrypted input path for security
        encrypted = self._validate_file_path(encrypted_path, require_exists=True)

        # For output_path, just ensure parent directory exists
        # (we don't validate it against workspace since it's output)
        output = Path(output_path).resolve()
        if not output.parent.exists():
            raise ValueError(f"Parent directory does not exist: {output.parent}")

        # Bound memory usage symmetrically with encrypt_file()
        encrypted_size = encrypted.stat().st_size
        if encrypted_size > MAX_FILE_SIZE:
            logger.error("Encrypted file too large: %s bytes (maximum %s bytes)", encrypted_size, MAX_FILE_SIZE)
            raise ValueError(
                f"Encrypted file too large: {encrypted_size} bytes (maximum {MAX_FILE_SIZE} bytes)"
            )

        with open(encrypted, "rb") as f:
            payload = f.read()

        # Authenticate + decrypt in memory; nothing is written on failure
        plaintext = self._decrypt_payload(payload, aad)

        logger.debug("Decrypted %s bytes -> %s bytes plaintext", len(payload), len(plaintext))

        if not plaintext:
            logger.warning("Decryption produced empty output (0 bytes)")

        with open(output_path, "wb") as f:
            f.write(plaintext)

        logger.debug("Successfully wrote decrypted file: %s", output_path)

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
            logger.info(f"Added {rel_path} to .gitignore")

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
        the configured vault suffix. When use_suffix_fallback is enabled and
        a custom suffix is used (not '.vault'), also searches for '.vault'
        files as fallbacks.

        Yields:
            Path: The path to each vault file found. When use_suffix_fallback=True
                  and custom suffix is set, yields custom suffix files preferentially,
                  with '.vault' files as fallback only if custom suffix doesn't exist
                  for that source file.
        """
        if self.use_suffix_fallback and self.suffix != ".vault":
            # Suffix fallback enabled with custom suffix
            # Group by source file and prefer custom suffix over .vault fallback
            vault_files_by_source = {}

            # Collect all vault files (both custom suffix and .vault)
            for dir in self.include_directories:
                # Find files with custom suffix
                for vault_file in Path(dir).rglob(f"*{self.suffix}"):
                    source = self.source_filename(str(vault_file), self.suffix)
                    vault_files_by_source[source] = vault_file

                # Find files with .vault suffix as fallback
                # IMPORTANT: Only search for .vault if it's different from custom suffix
                # to avoid finding custom suffix files twice (e.g., .secret.vault ends with .vault)
                for vault_file in Path(dir).rglob("*.vault"):
                    # Skip if this file matches the custom suffix pattern
                    if str(vault_file).endswith(self.suffix):
                        continue

                    # Infer the actual suffix instead of assuming ".vault"
                    inferred_suffix = self.infer_vault_suffix(str(vault_file))
                    if inferred_suffix is None:
                        # Fallback to ".vault" if unable to infer
                        inferred_suffix = ".vault"
                    
                    source = self.source_filename(str(vault_file), inferred_suffix)
                    # Only use fallback if custom suffix doesn't exist
                    if source not in vault_files_by_source:
                        vault_files_by_source[source] = vault_file

            # Yield preferred vault files
            for vault_file in vault_files_by_source.values():
                yield vault_file
        else:
            # Traditional behavior: yield all vault files with configured suffix
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

    def refresh_task(self, force: bool = True) -> Dict[str, Any]:
        """Decrypt and restore source files from their vault files.

        For each vault file found in the configured directories, decrypts and
        restores the corresponding source file. By default, overwrites existing
        source files. Verifies HMAC integrity after decryption.

        Args:
            force: If True, decrypt and restore source files even if they already
                   exist. If False, only restore missing source files.

        Returns:
            Dict with keys: 'total', 'succeeded', 'failed', 'skipped', 'errors'
            where 'errors' is a list of (vault_file, error_message) tuples.

        Note:
            Each vault file contains an HMAC tag on the first line and base64-encoded
            encrypted content on subsequent lines. After decryption, the HMAC is
            verified to ensure the decrypted content has not been tampered with.
        """
        logger.info(f"Starting refresh task (force={force})")

        # Initialize counters for aggregation
        total = 0
        succeeded = 0
        failed = 0
        skipped = 0
        errors = []

        vault_files = list(self.iter_vault_files())
        logger.info(f"Found {len(vault_files)} vault files to process")

        for vault_file in vault_files:
            total += 1
            # Determine which suffix this vault file uses
            # When fallback is enabled, files might have different suffixes
            if str(vault_file).endswith(self.suffix):
                vault_suffix = self.suffix
            elif self.use_suffix_fallback and str(vault_file).endswith(".vault"):
                # Use inferred suffix instead of assuming ".vault"
                vault_suffix = self.infer_vault_suffix(str(vault_file))
                if vault_suffix is None:
                    logger.warning(f"Failed to infer vault suffix for {vault_file}")
                    skipped += 1
                    continue
                logger.debug(f"Using inferred suffix {vault_suffix!r} for {vault_file}")
            else:
                # Unknown suffix, skip
                logger.warning(f"Vault file {vault_file} doesn't match any known suffix pattern")
                skipped += 1
                continue

            source_file = Path(self.source_filename(str(vault_file), vault_suffix))

            if source_file.exists() and not force:
                logger.debug(f"Skipping existing source file: {source_file}")
                skipped += 1
                continue

            # Read vault file with validation
            try:
                logger.debug(f"Reading vault file: {vault_file}")
                with open(vault_file, "r", encoding="utf-8") as vf:
                    lines = vf.readlines()
                    if len(lines) < 2:
                        raise ValueError("Vault file has insufficient lines (expected at least 2)")
                    stored_hmac = lines[0].strip().lower()
                    encrypted_b64 = lines[1].strip()
            except (IOError, OSError) as e:
                logger.error(f"Failed to read vault file {vault_file}: {e}")
                errors.append((str(vault_file), f"Read error: {e}"))
                failed += 1
                continue
            except ValueError as e:
                logger.warning(f"Malformed vault file {vault_file}: {e}")
                errors.append((str(vault_file), f"Malformed: {e}"))
                failed += 1
                continue

            # Validate HMAC format
            if not self._is_valid_hmac(stored_hmac):
                logger.error(f"Invalid HMAC format in {vault_file} (expected 64 hex chars)")
                errors.append((str(vault_file), "Invalid HMAC format"))
                failed += 1
                continue

            # Validate and decode base64
            if not encrypted_b64:
                logger.error(f"Empty encrypted content in {vault_file}")
                errors.append((str(vault_file), "Empty encrypted content"))
                failed += 1
                continue

            try:
                encrypted_data = base64.b64decode(encrypted_b64, validate=True)
            except (binascii.Error, ValueError) as e:
                logger.error(f"Invalid base64 encoding in {vault_file}: {e}")
                errors.append((str(vault_file), f"Base64 decode error: {e}"))
                failed += 1
                continue

            # Authenticate and decrypt in memory before touching the disk:
            # unauthenticated plaintext must never be written.
            try:
                logger.debug("Decrypting %s -> %s", vault_file, source_file)
                plaintext = self._decrypt_payload(encrypted_data, self._path_aad(source_file))

                computed_hmac = compute_hmac_bytes(plaintext, self.hmac_key)
                if not hmac.compare_digest(computed_hmac, stored_hmac):
                    logger.error("HMAC verification failed for %s", vault_file)
                    logger.debug("  Stored HMAC:   %s", stored_hmac)
                    logger.debug("  Computed HMAC: %s", computed_hmac)
                    logger.warning("File may have been tampered with - nothing was written")
                    errors.append((str(vault_file), "HMAC verification failed"))
                    failed += 1
                    continue

                self._write_bytes_atomically(source_file, plaintext)
                logger.info("Successfully restored %s from %s (authenticated ✓)", source_file, vault_file)
                succeeded += 1

            except (IOError, OSError, ValueError) as e:
                logger.error(
                    "Failed to decrypt %s: %s", vault_file, e, exc_info=logger.isEnabledFor(logging.DEBUG)
                )
                errors.append((str(vault_file), f"Decryption failed: {e}"))
                failed += 1

        # Log summary
        logger.info(f"Refresh completed: {succeeded}/{total} succeeded, {failed} failed, {skipped} skipped")
        if errors:
            logger.warning(f"Failed to process {len(errors)} vault files")
            for vault_file, error in errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {vault_file}: {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")

        return {
            'total': total,
            'succeeded': succeeded,
            'failed': failed,
            'skipped': skipped,
            'errors': errors
        }

    def encrypt_task(self, force: bool = False) -> Dict[str, Any]:
        """Encrypt all source files to their corresponding vault files.

        Processes all source files matching the configured patterns and creates
        encrypted vault files. Uses HMAC for authentication to detect changes
        and avoid unnecessary re-encryption unless forced.

        Args:
            force: If True, re-encrypt all files even if their HMACs haven't
                   changed. If False, only encrypt new files or files that have
                   been modified since last encryption.

        Returns:
            Dict with keys: 'total', 'created', 'updated', 'skipped', 'failed', 'errors'
            where 'errors' is a list of (source_file, error_message) tuples.

        Note:
            Each vault file contains:
            - Line 1: HMAC-SHA256 authentication tag of the source file
            - Line 2+: Base64-encoded encrypted content

            This format provides both integrity verification and secure storage.
        """
        logger.info(f"Starting encrypt task (force={force})")

        # Initialize counters for aggregation
        total = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        errors = []

        source_files = list(self.iter_source_files())
        logger.info(f"Found {len(source_files)} source files to process")

        for source_file in source_files:
            total += 1
            # Determine vault filename using configured suffix
            vault_file = Path(self.vault_filename(str(source_file)))

            try:
                # Compute HMAC of current source file
                logger.debug(f"Computing HMAC for {source_file}")
                hmac_tag = compute_hmac(source_file, self.hmac_key)

                # Check if vault file exists and get its HMAC
                vault_hmac = None
                vault_exists = vault_file.exists()

                if vault_exists:
                    try:
                        with open(vault_file, "r", encoding="utf-8") as vf:
                            first_line = vf.readline().strip()
                            vault_hmac = first_line if first_line else None
                    except (IOError, OSError) as e:
                        logger.warning(f"Failed to read existing vault file {vault_file}: {e}")
                        vault_hmac = None

                # Decide if encryption is needed
                if vault_exists and hmac_tag == vault_hmac and not force:
                    logger.debug(f"Skipping unchanged file: {source_file}")
                    skipped += 1
                    continue

                # Encrypt file to temp, then encode and write .vault file
                logger.debug("Encrypting %s -> %s", source_file, vault_file)
                temp_encrypted = str(vault_file) + ".tmp"

                try:
                    # Bind the ciphertext to its logical path (AAD) so a vault
                    # file cannot be silently swapped with another one.
                    self.encrypt_file(str(source_file), temp_encrypted, aad=self._path_aad(source_file))

                    with open(temp_encrypted, "rb") as ef:
                        encoded = encode_base64(ef.read()).decode()

                    # Bytes, not text: keeps the byte count identical on every platform
                    expected_content = (hmac_tag + "\n" + encoded + "\n").encode("utf-8")
                    expected_size = len(expected_content)

                    logger.debug("Writing vault file: %s (%s bytes)", vault_file, expected_size)
                    self._write_bytes_atomically(vault_file, expected_content)

                    # Verify the file was written correctly
                    if not vault_file.exists():
                        raise IOError(f"Vault file not created after write: {vault_file}")

                    # Verify file size matches expected
                    written_size = vault_file.stat().st_size
                    if written_size != expected_size:
                        logger.error(
                            "Incomplete write to %s: %s bytes (expected %s)",
                            vault_file, written_size, expected_size,
                        )
                        raise IOError(
                            f"Incomplete write: {written_size} bytes written, expected {expected_size} bytes"
                        )

                    # Verify file is readable and contains valid data
                    try:
                        with open(vault_file, "rb") as vf_verify:
                            verify_lines = vf_verify.read().split(b"\n")
                        if len(verify_lines) < 2 or not verify_lines[1].strip():
                            raise IOError("Vault file verification failed: insufficient lines")
                        if verify_lines[0].decode("ascii").strip() != hmac_tag:
                            raise IOError("Vault file verification failed: HMAC mismatch")
                    except (IOError, OSError, UnicodeDecodeError) as verify_err:
                        logger.error("Vault file verification failed for %s: %s", vault_file, verify_err)
                        raise IOError(f"Vault file verification failed: {verify_err}")

                    action = "Updated" if vault_exists else "Created"
                    logger.info(f"{action} vault file: {vault_file} for source: {source_file} ({written_size} bytes)")
                    logger.debug("Vault file verified: HMAC correct, size correct")

                    if vault_exists:
                        updated += 1
                    else:
                        created += 1

                finally:
                    # Clean up temp file
                    if Path(temp_encrypted).exists():
                        try:
                            os.remove(temp_encrypted)
                            logger.debug(f"Removed temp file: {temp_encrypted}")
                        except OSError as cleanup_err:
                            logger.warning(f"Failed to remove temp file {temp_encrypted}: {cleanup_err}")

            except (IOError, OSError, ValueError) as e:
                logger.error(f"Failed to encrypt {source_file}: {e}", exc_info=logger.isEnabledFor(logging.DEBUG))
                errors.append((str(source_file), f"Encryption failed: {e}"))
                failed += 1
                continue

        # Log summary
        logger.info(f"Encrypt completed: {created} created, {updated} updated, {skipped} skipped, {failed} failed (total: {total})")
        if errors:
            logger.warning(f"Failed to encrypt {len(errors)} source files")
            for source_file, error in errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {source_file}: {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")

        return {
            'total': total,
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'failed': failed,
            'errors': errors
        }


    def remove_task(self) -> Dict[str, Any]:
        """Delete all vault files matching the configured suffix.

        Permanently removes all vault files found in the configured include
        directories. When suffix fallback is enabled, this removes BOTH custom
        suffix vault files AND .vault fallback files to ensure complete cleanup.
        This operation cannot be undone.

        Returns:
            Dict with keys: 'total', 'removed', 'failed', 'errors'
            where 'errors' is a list of (vault_file, error_message) tuples.

        Note:
            Prints status messages for each file removal attempt, including
            any errors encountered during the deletion process.

        Warning:
            This operation permanently deletes encrypted vault files. Ensure
            you have the original source files before running this command.
        """
        logger.info("Starting remove task")

        # Initialize counters for aggregation
        total = 0
        removed = 0
        failed = 0
        errors = []

        # Collect all vault files to remove (including both custom suffix and fallback .vault files)
        vault_files_to_remove = set()

        if self.use_suffix_fallback and self.suffix != ".vault":
            # When suffix fallback is enabled, remove BOTH custom suffix and .vault files
            logger.info(f"Collecting vault files with custom suffix '{self.suffix}' and fallback '.vault' files")
            for dir in self.include_directories:
                # Find files with custom suffix
                for vault_file in Path(dir).rglob(f"*{self.suffix}"):
                    vault_files_to_remove.add(vault_file)

                # Find files with .vault suffix (fallback files)
                for vault_file in Path(dir).rglob("*.vault"):
                    # Skip if this file matches the custom suffix pattern (avoid duplicates)
                    if not str(vault_file).endswith(self.suffix):
                        vault_files_to_remove.add(vault_file)
        else:
            # Traditional behavior: collect all vault files with configured suffix
            logger.info(f"Collecting vault files with suffix '{self.suffix}'")
            for dir in self.include_directories:
                for vault_file in Path(dir).rglob(f"*{self.suffix}"):
                    vault_files_to_remove.add(vault_file)

        logger.info(f"Found {len(vault_files_to_remove)} vault files to remove")

        for vault_file in vault_files_to_remove:
            total += 1
            try:
                vault_file.unlink()
                logger.info(f"Removed vault file: {vault_file}")
                removed += 1
            except (IOError, OSError, PermissionError) as e:
                logger.error(f"Failed to remove {vault_file}: {e}")
                errors.append((str(vault_file), f"Remove failed: {e}"))
                failed += 1

        # Log summary
        logger.info(f"Remove completed: {removed}/{total} removed, {failed} failed")
        if errors:
            logger.warning(f"Failed to remove {len(errors)} vault files")
            for vault_file, error in errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {vault_file}: {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")

        return {
            'total': total,
            'removed': removed,
            'failed': failed,
            'errors': errors
        }
