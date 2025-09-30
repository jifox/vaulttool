"""Utility functions for VaultTool operations.

This module provides common utility functions for file operations,
checksums, and encoding used throughout the VaultTool package.
"""

import hashlib
import base64
from typing import Union
from pathlib import Path


def compute_checksum(path: Union[str, Path]) -> str:
    """Compute SHA-256 checksum of a file.
    
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
