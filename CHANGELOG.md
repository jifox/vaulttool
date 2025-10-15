# Changelog

All notable changes to VaultTool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-15

### 🎉 Major Release - Quality & Reliability Improvements

Version 2.0.0 represents a major quality improvement with comprehensive error handling, enhanced validation, and simplified installation. This release makes VaultTool more robust, debuggable, and user-friendly.

### ⚠️ Breaking Changes

- **Removed OpenSSL Dependency**: VaultTool now uses Python's `cryptography` library directly instead of calling external OpenSSL binaries
  - **Impact**: The `openssl_path` configuration option is no longer used and will be ignored if present
  - **Benefit**: Simplified installation with no system dependencies required
  - **Migration**: No action needed - existing configurations continue to work, just remove the unused `openssl_path` option

### ✨ Added

#### Security & Reliability
- **Key Material Validation**: Enforces minimum 32-byte key size with informative error messages
- **File Write Verification**: Validates encrypted file integrity immediately after write operations
- **HMAC Validation Enhancement**: Enhanced tamper detection with detailed error reporting
- **Empty File Handling**: Graceful handling of empty files with appropriate warnings
- **Crypto Operation Validation**: Input format validation before decryption (length checks, block alignment)

#### Error Handling & Diagnostics
- **Exception Chaining**: All exceptions now preserve full context with `from e` syntax for complete debugging information
- **Enhanced Error Messages**: Configuration errors now include exact field names, expected formats, and actionable guidance
- **Path Validation Context**: Full exception context chain showing what operation was attempted and why it failed
- **Improved CLI Error Handling**: Graceful version detection with multiple fallback methods and specific exception handling

#### Logging & Visibility
- **Comprehensive Debug Logging**: Detailed operation flow for troubleshooting
  - Key derivation operations
  - Encryption/decryption operations with byte counts
  - File write confirmations
  - Validation checkpoints
- **Structured Log Levels**: DEBUG, INFO, WARNING, and ERROR levels for appropriate visibility
- **Error Diagnostics Logging**: Full stack traces and context for failures

#### Testing
- **Enhanced Test Coverage**: 71 comprehensive tests (up from 56)
- **15 New Error Handling Tests**: Specifically for error handling paths and edge cases
- **100% Pass Rate**: All tests passing with 2.5s execution time
- **Zero Regressions**: All original tests still passing

### 🔄 Changed

- **Encryption Backend**: Migrated from OpenSSL CLI to Python `cryptography` library
  - Same AES-256-CBC encryption with HMAC-SHA256 authentication
  - Better portability across all platforms (Linux, macOS, Windows)
  - No external binary dependencies
- **Error Messages**: All error messages enhanced with specific details and actionable guidance
- **Configuration Validation**: More strict validation with detailed error reporting

### 🐛 Fixed

- **Key Derivation**: Enhanced error context in HKDF operations
- **Task Error Aggregation**: TaskResult now includes file paths in error messages for easier debugging
- **Padding Validation**: Better detection and reporting of corrupted encrypted data
- **Path Resolution**: Improved error messages when path validation fails

### 📚 Documentation

- **README**: Comprehensive "What's New in v2.0.0" section added
- **Installation Guide**: Simplified with removal of OpenSSL requirements
- **Error Message Examples**: Before/after examples showing improvements
- **Logging Examples**: Debug and error output samples
- **Troubleshooting**: Updated with v2.0.0-specific guidance
- **Configuration Reference**: Updated to reflect removed `openssl_path` option

### 🔧 Technical Details

#### Dependencies
- Added: `cryptography` library for encryption operations
- Maintained: `typer` for CLI, `pyyaml` for configuration
- Python: Requires 3.10 or newer

#### Performance
- Minimal performance impact: <3% overhead from enhanced logging and validation
- Faster installation: No need to compile or install system packages

### 📦 Upgrade Instructions

**Completely Backward Compatible** - Drop-in replacement for v1.x:

```bash
# Using Poetry
poetry update vaulttool

# Using pip
pip install --upgrade vaulttool

# Your existing .vaulttool.yml continues to work unchanged
vaulttool
```

**What You'll Notice:**
- More helpful error messages when things go wrong
- Better logging output for debugging
- Faster issue resolution due to improved diagnostics
- Simpler installation on new systems

### 🙏 Contributors

- Josef Fuchs - Lead Developer

---

## [1.x.x] - Previous Versions

Previous versions used external OpenSSL binaries for encryption operations. See git history for details.

