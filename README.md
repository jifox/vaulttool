# Vault Tool

<img src="docs/img/vaulttool_icon.png" alt="Vault Tool Icon" width="50%" />

![License: Apache-2](https://img.shields.io/badge/License-Apache%202-blue.svg)
![Python: 3.10–3.13](https://img.shields.io/badge/python-3.10--3.13-blue.svg)

A simple tool that allows you to automatically encrypt your secrets and configuration files so that they can be safely stored in your version control system.

## Table of Contents

- [Features](#features)
- [What's New in Version 2.0.0](#whats-new-in-version-200)
  - [Simplified Installation](#simplified-installation)
  - [Enhanced Security & Reliability](#enhanced-security--reliability)
  - [Better Error Messages](#better-error-messages)
  - [Comprehensive Logging](#comprehensive-logging)
  - [Improved Error Handling](#improved-error-handling)
  - [Test Coverage](#test-coverage)
  - [What This Means For You](#what-this-means-for-you)
  - [Upgrade Path](#upgrade-path)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Install Vault Tool (Recommended: Poetry)](#install-vault-tool-recommended-poetry)
  - [Generate Encryption Key](#generate-encryption-key)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Generate example configuration](#generate-example-configuration)
  - [Display version information](#display-version-information)
  - [Encrypt Files](#encrypt-files)
  - [Remove all vault files](#remove-all-vault-files)
  - [Refresh plaintext from vaults](#refresh-plaintext-from-vaults)
  - [Ensure Plaintext Files Are Added to .gitignore](#ensure-plaintext-files-are-added-to-gitignore)
- [Example Workflow](#example-workflow)
  - [Initial Setup](#initial-setup)
  - [Daily Workflow](#daily-workflow)
- [Pre-commit Installation](#pre-commit-installation)
- [Pre-commit Integration](#pre-commit-integration)
- [Related Tools](#related-tools)
- [Contributing](#contributing)
  - [How to Contribute](#how-to-contribute)
  - [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Getting Help](#getting-help)
- [License](#license)

## Features

- **Encrypts sensitive files**: Protects configuration files, API keys, and secrets by encrypting them.
- **Works with Git**: Lets you track changes to encrypted files without exposing secrets in your repository.
- **Detects changes automatically**: Updates encrypted files whenever the original files change.
- **Restores missing files**: Automatically decrypts files if the original is missing and a `.vault` file exists.
- **Refreshes plaintext from vaults**: On demand, overwrite existing plaintext from `.vault` files (with `--force`).
- **Uses AES-256-CBC encryption**: Secures your data with strong, industry-standard encryption via Python's cryptography library.
- **Updates .gitignore for you**: Adds plain text files to `.gitignore` to prevent accidental commits of secrets.
- **Verifies file integrity**: Uses HMACs to make sure encrypted files are always up to date.
- **Editor-friendly format**: Encrypted files are base64 encoded, making them easy to copy and paste.
- **Easy to use**: Integrates smoothly with your workflow and tools.
- **Keeps secrets safe**: Stores sensitive information securely and restricts access to authorized users.
- **Flexible configuration**: Lets you specify which files to encrypt and how to handle them using a config file.

---

## What's New in Version 2.0.0

VaultTool v2.0.0 represents a **major quality improvement** with comprehensive error handling and validation enhancements. This release makes VaultTool more robust, debuggable, and user-friendly.

### Cryptographic Components

1. **HKDF Key Derivation**
   - Master key → HMAC key (32 bytes)
   - Master key → Encryption key (32 bytes)
   - Cryptographically separated

  The HKDF (HMAC-based Extract-and-Expand Key Derivation Function) algorithm is a cryptographic method for
  transforming a shared secret into a cryptographically strong key. It uses HMAC (Hash-based Message Authentication Code) as a
  building block to ensure the derived keys are secure and suitable for encryption and authentication.

2. **HMAC-SHA256 Authentication**
   - Keyed authentication tag
   - Detects tampering
   - 64 hex characters

  The HMAC-SHA256 algorithm is a cryptographic hash function that combines a secret key with the input data to produce
  a fixed-size output (the HMAC tag). This tag is unique to both the input data and the key, making it an effective
  way to verify data integrity and authenticity.

3. **AES-256-CBC Encryption**
   - 256-bit encryption key
   - Random IV per encryption
   - PKCS7 padding

Architecture Diagram:

```text
Master Key File (vault.key)
    ↓
[64 hex chars = 32 bytes of entropy]
    ↓
derive_keys() with HKDF
    ├─→ HKDF(info="hmac-key") → HMAC Key (32 bytes)
    │                              ↓
    │                          Used for file integrity/authentication
    │
    └─→ HKDF(info="encryption-key") → Encryption Key (32 bytes)
                                          ↓
                                   Used for AES-256-CBC encryption
```

## Vault File Format

```text
Line 1: HMAC-SHA256 (64 hex chars)
Line 2: Base64(IV[16] + Ciphertext[variable])
```

Example:

```text
ae5bee7bdc95c4aa85c5e773876fc78c2b8e9f4d3c7a6b5e8d1f0a9c2e4b7d6f
1iaMa0AakO59yy6eZeNuBnmfQDhoqsrAovpp69MyqNFjZAbCxYzPq...
```

> **BREAKING CHANGE (Installation Only):** VaultTool now uses Python's `cryptography` library directly instead of calling external OpenSSL binaries. This **simplifies installation** (no system dependencies required) but the `openssl_path` configuration option is no longer used.

### Simplified Installation

**No More External Dependencies!**

- **Removed OpenSSL requirement**: Now uses Python's `cryptography` library directly
- **Simpler installation**: Just install VaultTool with pip or Poetry - no system dependencies
- **Better portability**: Works consistently across all platforms (Linux, macOS, Windows)
- **Same strong encryption**: Still uses AES-256-CBC with HMAC-SHA256 for authentication

**Result:** Installation is now as simple as `pip install vaulttool` or `poetry install` - no need to install OpenSSL or other system packages!

### Enhanced Security & Reliability

**Critical Security Improvements:**

- **Key Material Validation**: Enforces minimum 32-byte key size with informative error messages
- **File Write Verification**: Validates encrypted file integrity immediately after write operations
- **HMAC Validation**: Enhanced tamper detection with detailed error reporting
- **Empty File Handling**: Graceful handling of empty files with appropriate warnings

**Result:** Your encrypted files are now verified end-to-end, catching corruption or write failures immediately.

### Better Error Messages

**Before v2.0:**

```text
Error: Invalid value
```

**After v2.0:**

```text
Error: Key file size (16 bytes) is below minimum (32 bytes).
Ensure key file contains at least 32 bytes of key material.
```

**Configuration Errors Now Include:**

- Exact field names that are missing or invalid
- Expected formats and values
- Actionable guidance on how to fix the issue

**Path Validation Errors Show:**

- Full exception context chain
- What operation was being attempted
- Why the path validation failed

### Comprehensive Logging

**Debug Visibility:**

```python
[DEBUG] Deriving keys from master key (64 bytes)
[DEBUG] Successfully derived HMAC key and encryption key
[DEBUG] Encrypting file: secret.env -> secret.env.vault
[DEBUG] Encrypted 1234 bytes -> 1264 bytes (with IV and padding)
[INFO] Successfully wrote encrypted file: secret.env.vault
```

**Error Diagnostics:**

```python
[ERROR] Key derivation failed: Invalid key material length
[ERROR] Validation failed: Ciphertext length not multiple of 16-byte block size
[ERROR] HMAC verification failed: File may have been tampered with
```

**Logging Levels:**

- `DEBUG`: Detailed operation flow, perfect for troubleshooting
- `INFO`: Successful operations and summaries
- `WARNING`: Non-critical issues (empty files, fallback operations)
- `ERROR`: Failures with full stack traces and context

### Improved Error Handling

**Exception Chaining:**

All exceptions now preserve full context with `from e` syntax:

```python
try:
    validate_path(file_path)
except OSError as e:
    raise ValueError(f"Invalid file path: {e}") from e
```

**Benefit:** Full debugging information retained, making production issues easier to diagnose.

**Crypto Operation Validation:**

- Validates input format before decryption (length checks, block alignment)
- Validates padding after decryption (detects corruption early)
- Logs all validation failures with specific error details

**CLI Error Handling:**

- Graceful version detection with multiple fallback methods
- Specific exception handling for different error types
- Informative logging at each fallback step

### Test Coverage

**Comprehensive Test Suite:**

- **71 tests** covering all functionality (was 56)
- **15 new tests** specifically for error handling paths
- **100% pass rate** with 2.5s execution time
- **Zero regressions** - all original tests still passing

**Test Categories:**

- Core functionality (encryption, decryption, configuration)
- Security edge cases (tampering, corruption, invalid inputs)
- Error handling (exceptions, validation, logging)
- Integration tests (full workflows, bulk operations)

### What This Means For You

**For Users:**

- **Better error messages** help you fix issues quickly without reading docs
- **Enhanced logging** makes debugging configuration problems straightforward
- **No breaking changes** - drop-in upgrade from v1.x

**For Developers:**

- **Full exception chains** preserve debugging context
- **Comprehensive logging** provides operational visibility
- **Enhanced validation** catches issues early in the pipeline

**For Operations:**

- **Structured logging** integrates with monitoring systems
- **Error context** makes production issues diagnosable
- **Minimal performance impact** (<3% overhead from logging)

### Upgrade Path

**You need to Completely Backward Compatible:**

```bash
# No configuration changes needed
poetry update vaulttool

# or
pip install --upgrade vaulttool

# Your existing .vaulttool.yml continues to work
vaulttool
```

**What You'll Notice:**

- More helpful error messages when things go wrong
- Better logging output (use `--verbose` for debug logs if available)
- Faster issue resolution due to improved diagnostics

---

## Requirements

- Python 3.10 or newer
- Python packages (automatically installed):
  - `cryptography` - For AES-256-CBC encryption and HMAC
  - `typer` - Command-line interface
  - `pyyaml` - Configuration file parsing

**Note:** As of v2.0.0, VaultTool uses Python's `cryptography` library directly instead of calling external OpenSSL binaries. This makes installation simpler and more portable across platforms.

## Installation

### Install Vault Tool (Recommended: Poetry)

#### Development/Local Installation

```bash
git clone https://github.com/jifox/vaulttool.git
cd vaulttool
poetry install
pre-commit install
```

#### Running the CLI

You can run the CLI directly with:

```bash
poetry run vaulttool
```

If you want to install the CLI globally (optional, for advanced users):

```bash
poetry build
pipx install dist/vaulttool-*.whl --force
```

### Generate Encryption Key

To create a secure encryption key for your vault, you can use the provided script or generate one manually:

**Option 1: Using the provided script:**

```bash
./vaulttool-generate-key.sh
```

**Option 2: Manual generation using Python:**

```bash
# Create vaulttool directory in home
mkdir -p "$HOME/.vaulttool"

# Generate a 256-bit (32-byte) encryption key
python3 -c "import secrets; print(secrets.token_hex(32))" > "$HOME/.vaulttool/vault.key"

# Secure the key file (Unix/Linux/macOS)
chmod 600 "$HOME/.vaulttool/vault.key"
```

**Option 3: Manual generation using OpenSSL (if available):**

```bash
mkdir -p "$HOME/.vaulttool"
openssl rand -hex 32 > "$HOME/.vaulttool/vault.key"
chmod 600 "$HOME/.vaulttool/vault.key"
```

**Important:** The key file must contain at least 32 bytes (64 hex characters) of random data. VaultTool v2.0.0+ validates key size and will reject keys that are too short.

## Configuration

Vault Tool uses a YAML configuration file named `.vaulttool.yml` in your project directory to control which files are encrypted and how.

You can generate an example configuration file with:

```bash
vaulttool gen-vaulttool > .vaulttool.yml
```

Example `.vaulttool.yml`:

```yaml
vaulttool:
  include_directories:
    - "src"
    - "configs"
  exclude_directories:
    - ".venv"
    - ".git"
    - "__pycache__"
  include_patterns:
    - "*.env"
    - "*.ini"
    - "*.json"
  exclude_patterns:
    - "*.log"
    - "*example*"
    - "*.vault"
  options:
    suffix: ".vault"           # Suffix for encrypted files
    algorithm: "aes-256-cbc"   # Encryption algorithm (AES-256-CBC)
    key_type: "file"           # Key storage type
    key_file: "vault.key"      # Path to encryption key file
```

**Configuration Options:**

- **`include_directories`**: List of directories to search for files to encrypt. Defaults to current directory if empty.
- **`exclude_directories`**: Directories to skip during encryption.
- **`include_patterns`**: Wildcard patterns for files to encrypt (e.g., `*.env`, `*.json`).
- **`exclude_patterns`**: Patterns for files to exclude. Defaults to `[*.vault]` (options.suffix).
- **`options`**: Encryption settings including:
  - `suffix`: File extension for encrypted files (default: `.vault`)
  - `algorithm`: Encryption algorithm (default: `aes-256-cbc`). Uses AES-256-CBC with HMAC-SHA256 for authentication.
  - `key_file`: Path to encryption key file (must be at least 32 bytes)

**Note:** The `openssl_path` option has been removed in v2.0.0 as VaultTool now uses Python's `cryptography` library directly.

Edit `.vaulttool.yml` to match your project structure and security requirements.

## Usage

### Generate example configuration

```bash
vaulttool gen-vaulttool > .vaulttool.yml
```

### Display version information

```bash
vaulttool version
```

### Encrypt Files

To encrypt your sensitive files, navigate to your project directory and run:

```bash
vaulttool encrypt [OPTIONS]

  OPTIONS: 
    --force              Re-encrypt and overwrite existing .vault Files
    --verbose  -v        Enable verbose debug logging
    --quiet    -q        Show only errors (suppress info/warning)
    --help               Show this message and exit.
```

This will:

- Encrypt specified files based on the configuration in `.vaulttool.yml`
- Automatically detect changes in unencrypted files and update corresponding `.vault` files
- Add plain text files to `.gitignore` to prevent accidental commits of sensitive information

### Remove all vault files

To delete all vault files matching the configured suffix (e.g., `.vault`), run:

```bash
vaulttool remove [OPTIONS]

  OPTIONS:
    --verbose  -v        Enable verbose debug logging
    --quiet    -q        Show only errors (suppress info/warning)
    --help               Show this message and exit.
```

This will search the configured directories and delete all matching vault files.

### Refresh plaintext from vaults

You can refresh (restore) plaintext files from existing `.vault` files.

```bash
python -m vaulttool.cli refresh [OPTIONS]

OPTIONS:
  --force        --no-force      Overwrite plaintext files from existing .vault files [default: force] 
  --verbose  -v                  Enable verbose debug logging
  --quiet    -q                  Show only errors (suppress info/warning)
  --help                         Show this message and exit.
```

This will:

- Restore only missing plaintext files (default behavior)
- Overwrite existing plaintext files from `.vault` files if `--force` is specified
- Update `.gitignore` to ensure plaintext files are ignored

### Ensure Plaintext Files Are Added to .gitignore

Add missing plaintext files to .gitignore so they are not accidentally committed:

```bash
vaulttool check-ignore [OPTIONS]

  OPTIONS:
    --verbose  -v        Enable verbose debug logging
    --quiet    -q        Show only errors (suppress info/warning)
    --help               Show this message and exit.
```

## Example Workflow

### Initial Setup

1. **Generate configuration** with `vaulttool gen-vaulttool > .vaulttool.yml`
2. **Configure** `.vaulttool.yml` to match your files
3. **Create your secret key** using the provided script or manually (see Installation section)
4. **Run** `vaulttool` to encrypt files

### Daily Workflow

1. **Edit** your secret files as needed
2. **Run** `vaulttool` before committing to Git
3. **Commit** only `.vault` files (plain files are automatically ignored)
4. **If a plain file is deleted**, run `vaulttool` to restore it from its `.vault` file
5. **To discard local plaintext changes and refresh from vaults**, run `vaulttool --force`

## Pre-commit Installation

To enable automatic encryption and code checks before every commit, install pre-commit:

```bash
pip install pre-commit
```

Then enable it in your repository:

```bash
pre-commit install
```

This will ensure all configured hooks (including Vault Tool encryption, ignore checks, tests, and linting) run automatically before each commit.

## Pre-commit Integration

For automatic encryption before commits, add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: vaulttool
        name: Encrypt sensitive files
        entry: vaulttool
        language: system
        always_run: true
```

## Related Tools

- **[Python Cryptography](https://cryptography.io/)**: The cryptography library used by VaultTool for AES-256-CBC encryption and HMAC
- **[pipx](https://pypa.github.io/pipx/)**: Install and run Python applications in isolated environments
- **[pre-commit](https://pre-commit.com/)**: Framework for managing Git pre-commit hooks
- **[Git](https://git-scm.com/)**: Version control system
- **[Poetry](https://python-poetry.org/)**: Python dependency management and packaging

## Contributing

We welcome contributions to Vault Tool! Here's how you can help:

### How to Contribute

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
4. **Make** your changes and add tests
5. **Run** tests to ensure everything works
6. **Commit** your changes (`git commit -m 'Add amazing feature'`)
7. **Push** to your branch (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

### Development Setup

```bash
git clone https://github.com/jifox/vaulttool.git
cd vaulttool
pip install -e .[dev]
pre-commit install
```

## Python API Usage

```python
from vaulttool.core import VaultTool

# Initialize (reads .vaulttool.yml)
vt = VaultTool()

# Access derived keys
print(f"HMAC key: {vt.hmac_key.hex()}")
print(f"Encryption key: {vt.encryption_key.hex()}")

# Encrypt all matching files
vt.encrypt_task(force=False)

# Decrypt and restore files
vt.refresh_task(force=True)

# Encrypt a single file
vt.encrypt_file("secrets.env", "encrypted.tmp")

# Decrypt a single file
vt.decrypt_file("encrypted.tmp", "secrets.env")
```

## Utility Functions

```python
from vaulttool.utils import derive_keys, compute_hmac

# Derive keys from master key file
hmac_key, enc_key = derive_keys("/path/to/master.key")

# Compute HMAC of a file
hmac_tag = compute_hmac("myfile.txt", hmac_key)
print(f"HMAC: {hmac_tag}")  # 64 hex chars
```

## Security Best Practices

1. **Master Key**
   - Use 32+ bytes of random data
   - Store securely (encrypted filesystem, HSM, etc.)
   - Back up in secure location
   - Never commit to version control

2. **Key File Permissions**

   ```bash
   chmod 600 ~/.vaulttool/master.key
   ```

3. **Gitignore**
   - VaultTool auto-adds source files to .gitignore
   - Always commit .vault files, not source files
   - Never commit master.key

4. **Key Rotation**
   - Plan regular key rotation
   - Decrypt → change key → re-encrypt

## Troubleshooting

### Common Issues

#### Key file too small

**Solution:** VaultTool v2.0.0+ requires at least 32 bytes (64 hex characters) in the key file.

```bash
# Check key file size
wc -c ~/.vaulttool/vault.key

# Generate a new valid key (64 hex chars = 32 bytes)
python3 -c "import secrets; print(secrets.token_hex(32))" > ~/.vaulttool/vault.key
chmod 600 ~/.vaulttool/vault.key
```

#### Permission denied

**Solution:** Run Vault Tool with appropriate permissions to access files.

```bash
# Check file permissions
ls -la ~/.vaulttool/vault.key
chmod 600 ~/.vaulttool/vault.key
```

#### Key file missing

**Solution:** Generate a key file as described in the installation section and update your `.vaulttool.yml`.

```bash
mkdir -p ~/.vaulttool
python3 -c "import secrets; print(secrets.token_hex(32))" > ~/.vaulttool/vault.key
chmod 600 ~/.vaulttool/vault.key
```

#### Configuration not found

**Solution:** Ensure `.vaulttool.yml` exists in your project root or specify the config path.

```bash
# Generate example configuration
vaulttool gen-vaulttool > .vaulttool.yml
```

#### Cryptography module errors

**Solution:** Ensure the Python `cryptography` package is properly installed.

```bash
# Reinstall dependencies
poetry install
# or
pip install cryptography
```

### Getting Help

- **Built-in Help**: Run `vaulttool --help` for command reference and usage examples
- **Documentation**: Check this README for setup and usage instructions
- **Bug Reports**: [Open an issue](https://github.com/jifox/vaulttool/issues) on GitHub
- **Feature Requests**: [Start a discussion](https://github.com/jifox/vaulttool/discussions) on GitHub

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---
