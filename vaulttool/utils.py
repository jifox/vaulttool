"""Utility functions for VaultTool operations.

This module provides common utility functions for file operations,
checksums, and encoding used throughout the VaultTool package.
"""

import hashlib
import hmac
import base64
import logging
from typing import Union, Tuple
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)


def derive_keys(key_file: str, salt: bytes = b"vaulttool-v1") -> Tuple[bytes, bytes]:
    """Derive HMAC and encryption keys from a master key file using HKDF.

    Uses HKDF (HMAC-based Key Derivation Function) to derive two separate keys
    from the master key: one for HMAC authentication and one for encryption.
    This provides cryptographic separation between authentication and encryption.

    Args:
        key_file: Path to the master key file.
        salt: Salt for key derivation. Default is a fixed application-specific salt.

    Returns:
        Tuple of (hmac_key, encryption_key), each 32 bytes.

    Raises:
        FileNotFoundError: If the key file doesn't exist.
        ValueError: If key file is invalid (empty, too small, not a file, etc.).
        PermissionError: If the key file cannot be read.

    Example:
        >>> hmac_key, enc_key = derive_keys("/path/to/keyfile")
    """
    key_path = Path(key_file).resolve()

    logger.debug(f"Deriving keys from key file: {key_file}")

    # Validate file exists and is a regular file
    if not key_path.exists():
        logger.error(f"Key file not found: {key_file}")
        raise FileNotFoundError(f"Key file not found: {key_file}")
    if not key_path.is_file():
        logger.error(f"Key path is not a regular file: {key_file}")
        raise ValueError(f"Key path is not a regular file: {key_file}")

    # Check file size (prevent reading huge files, require minimum entropy)
    file_size = key_path.stat().st_size
    logger.debug(f"Key file size: {file_size} bytes")
    if file_size == 0:
        logger.error(f"Key file is empty: {key_file}")
        raise ValueError(f"Key file is empty: {key_file}")
    if file_size < 16:  # Minimum 128 bits for security
        logger.error(f"Key file too small: {file_size} bytes (minimum 16 bytes required)")
        raise ValueError(f"Key file too small: {file_size} bytes (minimum 16 bytes required)")
    if file_size > 1024 * 1024:  # Max 1MB to prevent memory issues
        logger.error(f"Key file too large: {file_size} bytes (maximum 1MB)")
        raise ValueError(f"Key file too large: {file_size} bytes (maximum 1MB)")

    # Read and validate key material
    with open(key_path, "rb") as f:
        master_key = f.read().strip()

    # Validate key is not empty after stripping whitespace
    if len(master_key) == 0:
        logger.error(f"Key file contains only whitespace: {key_file}")
        raise ValueError(f"Key file contains only whitespace: {key_file}")
    if len(master_key) < 16:
        logger.error(f"Key material too short after stripping: {len(master_key)} bytes")
        raise ValueError(f"Key material too short after stripping: {len(master_key)} bytes (minimum 16 bytes)")

    logger.debug(f"Key material: {len(master_key)} bytes")

    # Derive HMAC key (32 bytes for SHA-256)
    hkdf_hmac = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"hmac-key",
    )

    # Derive encryption key (32 bytes for AES-256)
    hkdf_enc = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"encryption-key",
    )

    try:
        hmac_key = hkdf_hmac.derive(master_key)
        encryption_key = hkdf_enc.derive(master_key)
        logger.debug(f"Successfully derived HMAC key (32 bytes) and encryption key (32 bytes) from {key_file}")
        return hmac_key, encryption_key
    except Exception as e:
        logger.error(f"Key derivation failed for {key_file}: {e}", exc_info=True)
        raise


def compute_hmac(path: Union[str, Path], hmac_key: bytes) -> str:
    """Compute HMAC-SHA256 of a file for authentication.

    Reads the file in chunks to efficiently handle large files while
    computing an HMAC for integrity verification and authentication.

    Args:
        path: Path to the file to authenticate. Can be a string or Path object.
        hmac_key: The HMAC key derived from the master key.

    Returns:
        Hexadecimal string representation of the HMAC-SHA256.

    Raises:
        IOError: If the file cannot be read.

    Example:
        >>> compute_hmac("myfile.txt", hmac_key)
        "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    """
    logger.debug(f"Computing HMAC for file: {path}")
    h = hmac.new(hmac_key, digestmod=hashlib.sha256)
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    result = h.hexdigest()
    logger.debug(f"HMAC computed: {result[:16]}...")
    return result


def compute_checksum(path: Union[str, Path]) -> str:
    """Compute SHA-256 checksum of a file.

    DEPRECATED: Use compute_hmac() for authenticated integrity checking.
    This function is kept for backwards compatibility only.

    Reads the file in chunks to efficiently handle large files while
    computing a cryptographic hash for change detection.

    Args:
        path: Path to the file to checksum. Can be a string or Path object.

    Returns:
        Hexadecimal string representation of the SHA-256 hash.

    Raises:
        IOError: If the file cannot be read.

    Example:
        >>> compute_checksum("myfile.txt")
        "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def encode_base64(data: bytes) -> bytes:
    """Encode binary data as base64.

    Converts binary data to base64 encoding for safe text storage
    in vault files.

    Args:
        data: Raw bytes to encode.

    Returns:
        Base64-encoded bytes.

    Example:
        >>> encode_base64(b"hello world")
        b'aGVsbG8gd29ybGQ='
    """
    return base64.b64encode(data)


def get_git_branch() -> str:
    """Get the current git branch name.

    Attempts to determine the current git branch name by checking:
    1. The .git/HEAD file to extract the branch reference
    2. Falls back to 'main' if not in a git repository or on detached HEAD

    Returns:
        The current git branch name, or 'main' if not in a git repo or detached HEAD.
        Branch names are sanitized to be filesystem-safe (alphanumeric, dash, underscore only).

    Example:
        >>> get_git_branch()
        'feature-add-encryption'
        >>> get_git_branch()  # Not in git repo
        'main'
    """
    import re
    import subprocess

    try:
        # Try using git command first (most reliable)
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )

        if result.returncode == 0:
            branch = result.stdout.strip()
            # Sanitize branch name for filesystem use
            # Keep alphanumeric, dash, underscore; replace others with dash
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', branch)
            # Remove leading/trailing dashes
            sanitized = sanitized.strip('-')
            # Collapse multiple dashes
            sanitized = re.sub(r'-+', '-', sanitized)

            if sanitized and sanitized != 'HEAD':
                logger.debug(f"Detected git branch: {sanitized}")
                return sanitized

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"Could not determine git branch via command: {e}")

    # Fallback: try reading .git/HEAD directly
    try:
        git_head = Path('.git/HEAD')
        if git_head.exists():
            content = git_head.read_text().strip()
            if content.startswith('ref: refs/heads/'):
                branch = content.replace('ref: refs/heads/', '')
                # Sanitize branch name
                sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', branch)
                sanitized = sanitized.strip('-')
                sanitized = re.sub(r'-+', '-', sanitized)

                if sanitized:
                    logger.debug(f"Detected git branch from .git/HEAD: {sanitized}")
                    return sanitized
    except Exception as e:
        logger.debug(f"Could not read .git/HEAD: {e}")

    # Default fallback
    logger.debug("No git branch detected, using 'main' as default")
    return 'main'
